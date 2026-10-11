"""As-of data layer: clock, cache/offline, mode routing, and (network-marked) real queries."""
import os
from datetime import datetime, timedelta, timezone

import pytest

from closure import clock, hazards, impact, engine, roads, synthetic
from parser import http_cache, nws_client, iem_client

UTC = timezone.utc
NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------- clock
def test_clock_defaults_to_system_time(monkeypatch):
    monkeypatch.delenv("CLEARSIGHT_NOW", raising=False)
    as_of, info = clock.resolve_as_of(None, now=NOW)
    assert as_of == NOW and info["source"] == "system" and info["mode"] == "live"


def test_clock_env_overrides_system_and_request_overrides_env(monkeypatch):
    monkeypatch.setenv("CLEARSIGHT_NOW", "2018-10-10T09:00:00Z")
    as_of, info = clock.resolve_as_of(None, now=NOW)
    assert as_of == datetime(2018, 10, 10, 9, tzinfo=UTC) and info["source"] == "env" and info["mode"] == "archive"
    as_of, info = clock.resolve_as_of("2026-10-10T12:00:00-05:00", now=NOW)
    assert info["source"] == "request" and as_of == datetime(2026, 10, 10, 17, tzinfo=UTC) and info["mode"] == "recent"


@pytest.mark.parametrize("bad", ["not a date", "2999-01-01T00:00:00Z", "1999-09-15T00:00:00Z"])
def test_clock_rejects_unparseable_future_and_pre_archive(bad, monkeypatch):
    monkeypatch.delenv("CLEARSIGHT_NOW", raising=False)
    with pytest.raises(clock.ClockError):
        clock.resolve_as_of(bad, now=NOW)


def test_invalid_env_value_is_reported_clearly(monkeypatch):
    monkeypatch.setenv("CLEARSIGHT_NOW", "tomorrow-ish")
    with pytest.raises(clock.ClockError, match="CLEARSIGHT_NOW"):
        clock.resolve_as_of(None, now=NOW)


def test_mode_routing_boundaries():
    assert nws_client.classify_mode(None, NOW) == "live"
    assert nws_client.classify_mode(NOW - timedelta(minutes=5), NOW) == "live"
    assert nws_client.classify_mode(NOW - timedelta(hours=2), NOW) == "recent"
    assert nws_client.classify_mode(NOW - timedelta(days=5, hours=23), NOW) == "recent"
    assert nws_client.classify_mode(NOW - timedelta(days=7), NOW) == "archive"
    assert nws_client.classify_mode(datetime(2018, 10, 10, tzinfo=UTC), NOW) == "archive"
    with pytest.raises(ValueError):
        nws_client.classify_mode(NOW + timedelta(days=1), NOW)


# ---------------------------------------------------------------- cache + offline (fake HTTP, no network)
class FakeResp:
    status_code = 200

    def __init__(self, data):
        self._d = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._d


def test_cache_hit_is_labelled_and_offline_mode_serves_only_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("CLEARSIGHT_CACHE_DIR", str(tmp_path))
    calls = []
    monkeypatch.setattr(http_cache.requests, "get", lambda url, **k: (calls.append(url), FakeResp({"x": 1}))[1])
    data, m1 = http_cache.cached_get_json("https://example.test/a", {"q": 1})
    assert data == {"x": 1} and m1["cached"] is False and len(calls) == 1
    data, m2 = http_cache.cached_get_json("https://example.test/a", {"q": 1})
    assert m2["cached"] is True and m2["retrieved_at"] == m1["retrieved_at"] and len(calls) == 1
    monkeypatch.setenv("CLEARSIGHT_OFFLINE", "1")
    assert http_cache.cached_get_json("https://example.test/a", {"q": 1})[1]["cached"] is True
    with pytest.raises(http_cache.OfflineCacheMiss, match="example.test/b"):
        http_cache.cached_get_json("https://example.test/b")
    assert len(calls) == 1, "offline mode must never touch the network"


def test_short_ttl_entries_refetch_when_stale(monkeypatch, tmp_path):
    monkeypatch.setenv("CLEARSIGHT_CACHE_DIR", str(tmp_path))
    n = []
    monkeypatch.setattr(http_cache.requests, "get", lambda url, **k: (n.append(1), FakeResp({"n": len(n)}))[1])
    http_cache.cached_get_json("https://example.test/t", None, ttl_seconds=0)
    d, m = http_cache.cached_get_json("https://example.test/t", None, ttl_seconds=0)
    assert d == {"n": 2} and m["cached"] is False


def test_picture_at_routes_archive_to_iem_and_reports_failures(monkeypatch):
    fac = {"id": "t", "latitude": 30.16, "longitude": -85.66, "state": "FL"}
    called = {}

    def boom(*a, **k):
        called["iem"] = True
        raise http_cache.OfflineCacheMiss("no cached copy")

    monkeypatch.setattr(iem_client, "fetch_alerts_at", boom)
    monkeypatch.setattr(iem_client, "fetch_observation_at", lambda *a, **k: {"observation": None, "station": None, "cached": False, "retrieved_at": "x", "sources": [], "notes": []})
    pic = hazards.picture_at(fac, datetime(2018, 10, 10, 9, tzinfo=UTC))
    assert called["iem"] and pic["mode"] == "archive" and pic["alerts"] == [] and any("no cached copy" in e for e in pic["errors"])
    assert pic["disclaimer"] and "not a live alert" in pic["disclaimer"]


# ---------------------------------------------------------------- real queries (skipped when services are unreachable)
def _eval(fac, as_of, employees):
    pic = hazards.picture_at(fac, as_of)
    win = engine.operating_window(fac, as_of)
    imp = impact.analyze_employees(fac, employees, pic["alerts"], win["window_start"], win["window_end"])
    return pic, imp, engine.evaluate(fac, pic, imp, roads.road_conditions(fac, pic["mode"]), as_of)


@pytest.mark.network
def test_michael_4am_panama_city_queries_iem_and_recommends_closure(iem_up):
    fac = synthetic.get_facility("fl-panamacity-sc")
    as_of = datetime(2018, 10, 10, 9, 0, tzinfo=UTC)
    pic, imp, det = _eval(fac, as_of, synthetic.employees_for(fac["id"]))
    assert pic["mode"] == "archive" and not pic["errors"]
    covering = {a["event"] for a in imp["facility_alerts"]}
    assert {"Hurricane Warning", "Storm Surge Warning"} <= covering
    hw = next(a for a in imp["facility_alerts"] if a["event"] == "Hurricane Warning")   # Mobile's warning is also in the picture; this is the one covering the facility
    assert hw["geometry"] and hw["geometry_kind"] == "county_zone" and hw["id"].startswith("VTEC:TAE.HU.W")
    assert det["posture"] == "closure" and det["binding_rule"] == "R1"
    again = hazards.picture_at(fac, as_of)
    assert again["data_source"]["cached"] is True, "second identical query must be served from the labelled cache"
    assert pic["weather"] and pic["weather"]["observation"]["timestamp"].startswith("2018-10-10T09:00")


@pytest.mark.network
def test_los_angeles_fire_weather_2025_queries_iem(iem_up):
    fac = {"id": "t-la", "name": "Test LA office (synthetic location)", "sector": "field_office", "latitude": 34.05, "longitude": -118.55,
           "timezone": "America/Los_Angeles", "opening_time": "08:00", "closing_time": "16:30", "state": "CA"}
    pic, imp, det = _eval(fac, datetime(2025, 1, 7, 18, 0, tzinfo=UTC), [])
    assert "Red Flag Warning" in {a["event"] for a in imp["facility_alerts"]}
    assert any(x["id"] == "R8" and x["fired"] for x in det["rules"]) and det["posture"] == "normal"
    assert any(x.startswith("FIRE WEATHER") for x in det["immediate_actions"])


@pytest.mark.network
def test_recent_mode_uses_nws_alert_history(nws_up):
    fac = synthetic.get_facility("fl-panamacity-sc")
    as_of = (datetime.now(UTC) - timedelta(days=3)).replace(minute=0, second=0, microsecond=0)
    pic = hazards.picture_at(fac, as_of)
    assert pic["mode"] == "recent" and not pic["errors"] and pic["data_source"]["name"].startswith("NWS API")
    assert all(hazards.in_effect(a, as_of)[0] != "expired" for a in pic["alerts"])


@pytest.mark.network
def test_live_mode_has_forecast_and_observation(nws_up):
    fac = synthetic.get_facility("ne-lincoln-sc")
    pic = hazards.picture_at(fac)
    assert pic["mode"] == "live" and not pic["errors"] and pic["weather"]["forecast"] and pic["weather"]["observation"]
