"""Backend glue: as-of /api/current, /api/clock, /api/moments, AI-result merge, failure handling.
Tests marked `network` query real NWS / IEM / Census services and skip themselves if those are unreachable."""
import json
import threading
import time
from datetime import datetime, timezone

import pytest

import evidence_api
from backend import connect, engine_adapter as ea
from closure import hazards

MICHAEL = "2018-10-10T09:00:00Z"
LA_FIRE = "2025-01-07T18:00:00Z"


# ---------------------------------------------------------------- no network needed
def test_clock_endpoint_modes_and_errors(client):
    ok = client.get("/api/clock", params={"asof": MICHAEL}).json()
    assert ok["mode"] == "archive" and ok["source"] == "request"
    for bad in ("garbage", "2999-01-01T00:00:00Z", "1999-09-15T00:00:00Z"):
        r = client.get("/api/clock", params={"asof": bad})
        assert r.status_code == 400 and r.json()["detail"]
        assert client.get("/api/current", params={"asof": bad}).status_code == 400


def test_moments_returns_a_list(client):
    r = client.get("/api/moments")
    assert r.status_code == 200 and isinstance(r.json()["moments"], list)


def test_app_runs_without_object_storage_settings(client):
    assert evidence_api.evidence is None, "tests run with the OBJ_* settings removed"
    assert client.get("/health").json() == {"ok": True}
    r = client.get("/evidence", params={"facility_id": "x"})
    assert r.status_code == 503 and "not configured" in r.json()["detail"]


def test_asof_requests_are_single_flight(monkeypatch):
    calls, gate = [], threading.Event()

    def slow_snapshot(requested):
        calls.append(requested); gate.wait(2); return {"mode": "archive", "facilities": []}
    monkeypatch.setattr(evidence_api, "build_snapshot", slow_snapshot)
    evidence_api._asof_cache.clear()
    as_dt = datetime(2018, 10, 10, 9, 0, tzinfo=timezone.utc)
    out = []
    ts = [threading.Thread(target=lambda: out.append(evidence_api._asof_snapshot(as_dt, MICHAEL))) for _ in range(4)]
    [t.start() for t in ts]; time.sleep(0.3); gate.set(); [t.join() for t in ts]
    evidence_api._asof_cache.clear()   # do not leave the stub snapshot behind for other tests
    assert len(calls) == 1 and len(out) == 4, "four concurrent reloads must share one computation"


def _office(**kw):
    return {"id": "test-bonifay", "name": "Bonifay Service Center", "address": "103 N Oklahoma Street, Bonifay, FL 32425",
            "lat": 30.79, "lon": -85.68, "agency": "USDA NRCS", "state": "FL", **kw}


def _picture(alerts=(), errors=(), mode="archive", as_of="2018-10-10T09:00:00+00:00"):
    ring = [[-86.5, 30.0], [-84.5, 30.0], [-84.5, 31.5], [-86.5, 31.5], [-86.5, 30.0]]
    al = []
    for ev in alerts:
        a = {"id": f"TEST-{ev}", "event": ev, "headline": f"TEST FIXTURE {ev}", "description": "", "instruction": None, "severity": None, "urgency": None,
             "certainty": None, "status": "Actual", "message_type": "Alert", "areaDesc": "test", "sent": "2018-10-08T21:00:00+00:00",
             "effective": "2018-10-08T21:00:00+00:00", "onset": "2018-10-08T21:00:00+00:00", "expires": None, "ends": None, "sender": "NWS TAE",
             "geometry": {"type": "Polygon", "coordinates": [ring]}, "geometry_kind": "county_zone", "source": "TEST", "source_url": None,
             "retrieved_at": as_of, "nws_says_covers_facility_point": True}
        al.append(hazards._finish(a))
    return {"mode": mode, "scenario": None, "as_of": as_of, "retrieved_at": as_of, "alerts": al, "weather": None, "sources": [], "errors": list(errors),
            "disclaimer": None, "data_source": {"name": "TEST", "cached": False, "cache_retrieved_at": None, "retrieved_at": as_of, "notes": []}}


def test_synthetic_picture_gives_closure_and_a_complete_facility_record():
    """SYNTHETIC TEST FIXTURE (a made-up Hurricane Warning polygon), only to exercise the payload shape."""
    f = connect.build_facility(_office(), _picture(["Hurricane Warning"]), datetime(2018, 10, 10, 9, tzinfo=timezone.utc))
    assert f["status"] == "closed" and f["engine"]["deterministic"]["binding_rule"] == "R1"
    assert f["alert"]["type"] == "hurricane" and f["alertPolygon"] and f["sector"] == "service_center" and f["timezone"] == "America/Chicago"
    assert {"engine_facility", "deterministic", "metrics", "by_community", "impact_note", "alerts", "roads", "employees", "evaluation_id", "record"} <= set(f["engine"])


def test_failed_alert_retrieval_is_unknown_never_normal():
    f = connect.build_facility(_office(), _picture(errors=["Archive alert query failed: boom"]), datetime(2018, 10, 10, 9, tzinfo=timezone.utc))
    assert f["status"] == "unknown" and f["total"] is None and f["engine"]["data_failed"] and f["alert"] is None
    assert "failed" in f["bullets"][0].lower() and not any(b.startswith("Recommendation") for b in f["bullets"])


def test_timezones_and_sectors_by_agency_and_state():
    assert ea.timezone_for("FL", -85.7) == "America/Chicago" and ea.timezone_for("FL", -82.4) == "America/New_York"
    assert ea.timezone_for("CA", -118.0) == "America/Los_Angeles"
    assert [ea.sector_for(a) for a in ("USDA NRCS", "USDA FSA", "USDA ARS", "USDA FS")] == ["service_center", "service_center", "research_lab", "field_office"]


def test_stored_ai_result_is_merged_for_exactly_that_office_and_moment(tmp_path, monkeypatch):
    monkeypatch.setattr(ea, "AI_DIR", tmp_path)
    as_dt = datetime(2018, 10, 10, 9, tzinfo=timezone.utc)
    ea.save_ai("test-bonifay", as_dt, {"evaluation_id": "ev_test", "record": {"sha256": "abc"}, "second_opinion": {"status": "ok"},
                                       "manager_decision": {"human_approved": True}, "notifications": {"status": "ok"}})
    f = connect.build_facility(_office(), _picture(["Hurricane Warning"]), as_dt)
    assert f["engine"]["second_opinion"] == {"status": "ok"} and f["engine"]["evaluation_id"] == "ev_test"
    other = connect.build_facility(_office(), _picture(["Hurricane Warning"], as_of="2018-10-10T10:00:00+00:00"), datetime(2018, 10, 10, 10, tzinfo=timezone.utc))
    assert "second_opinion" not in other["engine"]


def test_repeat_dashboard_loads_do_not_add_audit_records():
    as_dt = datetime(2018, 10, 10, 9, tzinfo=timezone.utc)
    a = connect.build_facility(_office(id="dedupe-1"), _picture(["Hurricane Warning"]), as_dt)["engine"]["evaluation_id"]
    b = connect.build_facility(_office(id="dedupe-1"), _picture(["Hurricane Warning"]), as_dt)["engine"]["evaluation_id"]
    assert a == b


def test_decide_cli_requires_an_explicit_moment():
    import subprocess, sys
    r = subprocess.run([sys.executable, "-m", "backend.decide", "--all"], cwd=connect.ROOT, capture_output=True, text=True)
    assert r.returncode != 0 and "--asof" in (r.stderr + r.stdout)


# ---------------------------------------------------------------- real services
@pytest.mark.network
def test_michael_snapshot_from_the_iem_archive(client, services_up):
    d = client.get("/api/current", params={"asof": MICHAEL}).json()
    assert d["mode"] == "archive" and len(d["facilities"]) >= 45 and not d["errors"] and d["disclaimer"]
    assert {"mode", "as_of", "generated_at", "clock", "data_source", "disclaimer", "errors", "postures", "chain_verified", "alert", "employees", "facilities"} <= set(d)
    by = {f["name"]: f for f in d["facilities"]}
    assert by["Bonifay Service Center"]["status"] == "closed" and by["Bonifay Service Center"]["alert"]["type"] == "hurricane"
    ca = [f for f in d["facilities"] if f["state"] == "CA"]
    assert len(ca) >= 25 and all(f["status"] == "normal" for f in ca), "California offices were calm on that morning"


@pytest.mark.network
def test_la_fire_weather_moment_has_red_flag_warnings_and_r8_actions(client, services_up):
    d = client.get("/api/current", params={"asof": LA_FIRE}).json()
    red = [f for f in d["facilities"] if f["alert"] and f["alert"]["title"] == "Red Flag Warning"]
    assert red, "Southern California offices should be under a Red Flag Warning at that moment"
    assert any("FIRE WEATHER" in a for f in red for a in f["engine"]["deterministic"]["immediate_actions"])


@pytest.mark.network
def test_live_snapshot_is_live(client, services_up):
    d = client.get("/api/current").json()
    assert d["mode"] == "live" and d["clock"]["source"] == "system" and len(d["facilities"]) >= 45


@pytest.mark.network
def test_cached_snapshot_is_much_faster_than_cold(client, services_up):
    t = time.time(); client.get("/api/current", params={"asof": "2020-08-27T06:00:00Z"}); cold = time.time() - t
    evidence_api._asof_cache.clear()
    t = time.time(); r = client.get("/api/current", params={"asof": "2020-08-27T06:00:00Z"}); warm = time.time() - t
    assert r.status_code == 200 and warm < cold
