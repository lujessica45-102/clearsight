"""Functions for retrieving weather data from the National Weather Service API."""

import os
from datetime import datetime, timedelta, timezone

import requests

try:                                   # imported as parser.nws_client (app) ...
    from . import http_cache, iem_client
except ImportError:                    # ... or as a top-level module (parser/ on sys.path, e.g. the unit tests)
    import http_cache
    import iem_client

NWS_BASE_URL = "https://api.weather.gov"
DEFAULT_TIMEOUT = 25

# As-of routing. "live": now. "recent": the NWS API still serves alert history for roughly the last week.
# "archive": older than that, served from the IEM archive of NWS products (see iem_client.py).
LIVE_TOLERANCE = timedelta(minutes=10)
RECENT_DAYS = 6
RECENT_LOOKBACK = timedelta(days=3)     # /alerts matches on ISSUE time, so we look back to catch still-active alerts
NWS_RETENTION = timedelta(days=6, hours=12)


def classify_mode(as_of, now=None):
    """'live' | 'recent' | 'archive' for an as-of datetime (None means now)."""
    now = now or datetime.now(timezone.utc)
    if as_of is None:
        return "live"
    as_of = as_of.astimezone(timezone.utc)
    if as_of > now + LIVE_TOLERANCE:
        raise ValueError(f"as_of {as_of.isoformat()} is in the future; no alert data exists for it")
    age = now - as_of
    if age <= LIVE_TOLERANCE:
        return "live"
    return "recent" if age <= timedelta(days=RECENT_DAYS) else "archive"


def fetch_json(url, params=None, timeout=DEFAULT_TIMEOUT):
    """Fetch JSON from an NWS endpoint."""
    headers = {
        "User-Agent": os.getenv(
            "NWS_USER_AGENT",
            "USDAClosureCall/1.0 (replace-with-contact-email)",
        ),
        "Accept": "application/geo+json",
    }
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _flat_alert(feature):
    properties = feature.get("properties", {})
    return {
        "id": feature.get("id"),
        "event": properties.get("event"),
        "headline": properties.get("headline"),
        "description": properties.get("description"),
        "instruction": properties.get("instruction"),
        "severity": properties.get("severity"),
        "urgency": properties.get("urgency"),
        "certainty": properties.get("certainty"),
        "status": properties.get("status"),
        "message_type": properties.get("messageType"),
        "affected_areas": properties.get("areaDesc"),
        "effective": properties.get("effective"),
        "onset": properties.get("onset"),
        "expires": properties.get("expires"),
        "sent": properties.get("sent"),
        "sender": properties.get("senderName"),
    }


def _live_fetch_alerts(latitude, longitude):
    """Return active NWS alerts affecting the supplied coordinates."""
    data = fetch_json(
        f"{NWS_BASE_URL}/alerts/active",
        params={"point": f"{latitude},{longitude}"},
    )

    return [_flat_alert(feature) for feature in data.get("features", [])]


def _measurement_value(measurement):
    """Extract a measurement's value while preserving null readings."""
    if not isinstance(measurement, dict):
        return None
    return measurement.get("value")


def _parse_observation(properties):
    """Normalize a latest-observation response into useful fields."""
    return {
        "timestamp": properties.get("timestamp"),
        "temperature": _measurement_value(properties.get("temperature")),
        "temperature_unit": (
            properties.get("temperature", {}).get("unitCode")
            if isinstance(properties.get("temperature"), dict) else None
        ),
        "wind_speed": _measurement_value(properties.get("windSpeed")),
        "wind_gust": _measurement_value(properties.get("windGust")),
        "visibility": _measurement_value(properties.get("visibility")),
        "conditions": properties.get("textDescription"),
        "precipitation_last_hour": _measurement_value(
            properties.get("precipitationLastHour")
        ),
    }


def _live_fetch_weather(latitude, longitude):
    """Retrieve forecast, hourly forecast, and latest available observation."""
    point_url = f"{NWS_BASE_URL}/points/{latitude},{longitude}"
    point_data = fetch_json(point_url)
    point_properties = point_data.get("properties", {})

    forecast_url = point_properties.get("forecast")
    hourly_forecast_url = point_properties.get("forecastHourly")
    stations_url = point_properties.get("observationStations")

    if not forecast_url or not hourly_forecast_url or not stations_url:
        raise ValueError(
            "The NWS points response did not include all required weather URLs."
        )

    forecast_data = fetch_json(forecast_url)
    hourly_data = fetch_json(hourly_forecast_url)
    station_data = fetch_json(stations_url)

    stations = []
    for feature in station_data.get("features", []):
        station_properties = feature.get("properties", {})
        stations.append({
            "id": station_properties.get("stationIdentifier"),
            "name": station_properties.get("name"),
            "url": feature.get("id") or station_properties.get("@id"),
        })

    observation = None
    if stations:
        station_url = stations[0]["url"]
        if station_url:
            observation_data = fetch_json(f"{station_url}/observations/latest")
            observation = _parse_observation(
                observation_data.get("properties", {})
            )

    return {
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "grid_id": point_properties.get("gridId"),
            "grid_x": point_properties.get("gridX"),
            "grid_y": point_properties.get("gridY"),
            "forecast_office": point_properties.get("forecastOffice"),
            "forecast_zone": point_properties.get("forecastZone"),
            "county": point_properties.get("county"),
        },
        "forecast": forecast_data.get("properties", {}).get("periods", []),
        "hourly_forecast": hourly_data.get("properties", {}).get("periods", []),
        "observation": observation,
        "observation_stations": stations,
        "sources": [
            point_url,
            forecast_url,
            hourly_forecast_url,
            stations_url,
        ],
    }


# ------------------------------------------------------------------ as-of (recent + archive) layer
def _parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _ttl_for(end, now=None):
    """Responses whose time window closed more than 2 hours ago are stable; near-now ones expire in 5 minutes."""
    now = now or datetime.now(timezone.utc)
    return None if now - end > timedelta(hours=2) else 300


def _iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _meta(sources, notes=None):
    """data_source block: name + whether every response was a cached copy + the oldest original retrieval time."""
    cached = bool(sources) and all(s.get("cached") for s in sources)
    times = [s["retrieved_at"] for s in sources if s.get("retrieved_at")]
    return {"cached": cached, "cache_retrieved_at": min(times) if cached and times else None,
            "retrieved_at": min(times) if times else None, "sources": sources, "notes": list(notes or [])}


def fetch_zone_geometry(url):
    """GeoJSON geometry of an NWS forecast/county zone, cached on disk (zone shapes rarely change)."""
    data, meta = http_cache.cached_get_json(url, None, ttl_seconds=None, headers={"Accept": "application/geo+json"})
    return data.get("geometry"), meta


def fetch_alert_features_recent(as_of, area=None, point=None, now=None):
    """Raw NWS alert features that were in force at `as_of` (within the API's ~week of history).

    /alerts matches on ISSUE time, so a lookback window is queried; update/cancel chains are resolved the way a
    forecaster would have seen them at `as_of` (only messages sent by then count; superseded and cancelled ones drop).
    Returns (features, meta).
    """
    now = now or datetime.now(timezone.utc)
    as_of = as_of.astimezone(timezone.utc)
    start = max(as_of - RECENT_LOOKBACK, now - NWS_RETENTION)
    params = {"start": _iso(start), "end": _iso(as_of), "status": "actual"}
    if point:
        params["point"] = f"{point[0]:.4f},{point[1]:.4f}"
    elif area:
        params["area"] = area
    data, m = http_cache.cached_get_json(f"{NWS_BASE_URL}/alerts", params, ttl_seconds=_ttl_for(as_of, now),
                                         headers={"Accept": "application/geo+json"})
    msgs = [f for f in data.get("features", []) if (_parse_ts(f.get("properties", {}).get("sent")) or as_of) <= as_of]
    superseded = set()
    for f in msgs:
        for ref in f.get("properties", {}).get("references") or []:
            superseded.update(x for x in (ref.get("@id"), ref.get("identifier")) if x)
    keep = []
    for f in msgs:
        pr = f.get("properties", {})
        if {f.get("id"), pr.get("id"), pr.get("identifier")} & superseded or pr.get("messageType") == "Cancel":
            continue
        end = _parse_ts(pr.get("ends") or pr.get("expires"))
        if end and as_of >= end:
            continue
        keep.append(f)
    notes = [f"NWS alert history was queried from {params['start']} to {params['end']}; alerts issued before that are not available from the NWS API."]
    return keep, {**_meta([{"url": m["url"], "cached": m["cached"], "retrieved_at": m["retrieved_at"]}], notes), "window": [params["start"], params["end"]]}


def fetch_observation_recent(latitude, longitude, as_of, now=None, max_age_hours=3):
    """Latest NWS station observation at/before `as_of` (recent mode). Returns (observation|None, station|None, meta)."""
    now = now or datetime.now(timezone.utc)
    as_of = as_of.astimezone(timezone.utc)
    srcs, notes = [], []
    pt, m = http_cache.cached_get_json(f"{NWS_BASE_URL}/points/{latitude:.4f},{longitude:.4f}", None, ttl_seconds=None, headers={"Accept": "application/geo+json"})
    srcs.append(m)
    stations_url = pt.get("properties", {}).get("observationStations")
    if not stations_url:
        return None, None, _meta(srcs, ["NWS points response had no observation stations."])
    st, m = http_cache.cached_get_json(stations_url, None, ttl_seconds=None, headers={"Accept": "application/geo+json"})
    srcs.append(m)
    for feat in st.get("features", [])[:3]:
        sid = feat.get("properties", {}).get("stationIdentifier")
        obs, m = http_cache.cached_get_json(f"{NWS_BASE_URL}/stations/{sid}/observations",
                                            {"start": _iso(as_of - timedelta(hours=max_age_hours)), "end": _iso(as_of), "limit": 5},
                                            ttl_seconds=_ttl_for(as_of, now), headers={"Accept": "application/geo+json"})
        srcs.append(m)
        rows = [f["properties"] for f in obs.get("features", []) if _parse_ts(f["properties"].get("timestamp"))]
        rows = [r for r in rows if _parse_ts(r["timestamp"]) <= as_of]
        if rows:
            best = max(rows, key=lambda r: _parse_ts(r["timestamp"]))
            return _parse_observation(best), {"id": sid, "name": feat["properties"].get("name")}, _meta(srcs, notes)
    notes.append("No NWS observation found within 3 hours before the requested time.")
    return None, None, _meta(srcs, notes)


def _flat_from_normalized(a):
    """IEM-normalized alert -> the flat shape fetch_alerts has always returned (+ geometry/provenance extras)."""
    flat = {k: a.get(k) for k in ("id", "event", "headline", "description", "instruction", "severity", "urgency", "certainty",
                                  "status", "effective", "onset", "expires", "sent", "sender", "geometry", "geometry_kind",
                                  "source", "source_url", "retrieved_at", "cached", "distance_km")}
    flat["message_type"], flat["affected_areas"] = a.get("message_type"), a.get("areaDesc")
    return flat


def fetch_alerts_with_meta(latitude, longitude, as_of=None, now=None):
    """(alerts, mode, data_source) for any as-of moment. Live is the unchanged active-alerts query."""
    mode = classify_mode(as_of, now)
    if mode == "live":
        return fetch_alerts(latitude, longitude), mode, {"name": "NWS API (live)", "cached": False, "cache_retrieved_at": None,
                                                         "retrieved_at": datetime.now(timezone.utc).isoformat(), "notes": []}
    if mode == "recent":
        feats, meta = fetch_alert_features_recent(as_of, point=(latitude, longitude), now=now)
        alerts = [{**_flat_alert(f), "geometry": f.get("geometry"), "source": "NWS API alert history", "retrieved_at": meta["retrieved_at"], "cached": meta["cached"]} for f in feats]
        return alerts, mode, {"name": "NWS API (recent alert history)", **{k: meta[k] for k in ("cached", "cache_retrieved_at", "retrieved_at", "notes")}}
    r = iem_client.fetch_alerts_at(latitude, longitude, as_of)
    alerts = [_flat_from_normalized(a) for a in r["alerts"] if a.get("covers_point")]
    return alerts, mode, {"name": iem_client.SOURCE, "cached": r["cached"], "cache_retrieved_at": r["retrieved_at"] if r["cached"] else None,
                          "retrieved_at": r["retrieved_at"], "notes": r["notes"]}


def fetch_alerts(latitude, longitude, as_of=None):
    """Alerts affecting the coordinates: active now (as_of None/now), or those in force at `as_of`."""
    if as_of is None:
        return _live_fetch_alerts(latitude, longitude)
    return fetch_alerts_with_meta(latitude, longitude, as_of)[0]


def fetch_weather(latitude, longitude, as_of=None):
    """Live: forecast + observation (unchanged). Past: the observation at that time only (no archived forecasts exist)."""
    mode = classify_mode(as_of)
    if mode == "live":
        return _live_fetch_weather(latitude, longitude)
    if mode == "recent":
        obs, station, meta = fetch_observation_recent(latitude, longitude, as_of)
    else:
        r = iem_client.fetch_observation_at(latitude, longitude, as_of)
        obs, station = r["observation"], r["station"]
        meta = {"cached": r["cached"], "cache_retrieved_at": r["retrieved_at"] if r["cached"] else None, "retrieved_at": r["retrieved_at"],
                "notes": r["notes"], "sources": r["sources"]}
    return {
        "location": {"latitude": latitude, "longitude": longitude},
        "forecast": [], "hourly_forecast": [],
        "forecast_note": "Forecasts are not available for past times; only the observation at that time is shown.",
        "observation": obs, "observation_stations": [station] if station else [],
        "sources": [s["url"] for s in meta.get("sources", [])],
        "cached": meta["cached"], "retrieved_at": meta["retrieved_at"], "notes": meta["notes"],
    }


def build_weather_report(facility, manager_inputs=None, as_of=None):
    """
    Build a weather report for a selected facility.

    `facility` may be a dictionary or an object with matching attributes.
    Expected facility fields include id, name, address, latitude, and longitude.
    """
    manager_inputs = manager_inputs or {}

    def get_field(name, default=None):
        if isinstance(facility, dict):
            return facility.get(name, default)
        return getattr(facility, name, default)

    latitude = get_field("latitude")
    longitude = get_field("longitude")
    if latitude is None or longitude is None:
        raise ValueError("The selected facility must have latitude and longitude.")

    if as_of is None:
        alerts, mode = fetch_alerts(latitude, longitude), "live"
        weather = fetch_weather(latitude, longitude)
        data_source = {"name": "NWS API (live)", "cached": False, "cache_retrieved_at": None, "notes": []}
    else:
        alerts, mode, data_source = fetch_alerts_with_meta(latitude, longitude, as_of)
        weather = fetch_weather(latitude, longitude, as_of) if mode != "live" else _live_fetch_weather(latitude, longitude)
        data_source = {**data_source, "notes": data_source.get("notes", []) + ([weather["forecast_note"]] if weather.get("forecast_note") else [])}

    facility_data = {
        "id": get_field("id"),
        "name": get_field("name"),
        "address": get_field("address"),
        "latitude": latitude,
        "longitude": longitude,
    }

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode, "as_of": (as_of.astimezone(timezone.utc).isoformat() if as_of is not None else datetime.now(timezone.utc).isoformat()),
        "data_source": data_source,
        "facility": facility_data,
        "manager_update": manager_inputs,
        "alerts": alerts,
        "weather": weather,
        "data_sources": [
            (f"{NWS_BASE_URL}/alerts/active?point={latitude},{longitude}" if mode == "live" else f"as-of {mode} query for {latitude},{longitude}"),
            *weather["sources"],
        ],
    }
