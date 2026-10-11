"""Hazard data: live NWS alerts (with geometry) and archived replay snapshots, normalized identically.

Every alert carries provenance (source, retrieved_at, sent/effective/onset/expires) so the audit record can
distinguish when something was issued, when it was retrieved, and when it was evaluated.
"""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from shapely.geometry import shape, mapping
from shapely.ops import unary_union

from . import config
from parser import nws_client  # team's existing NWS client (fetch_json / fetch_alerts / fetch_weather)

# event -> (hazard_class, base_level). PROTOTYPE MAPPING anchored on the NWS product hierarchy
# (Warning > Watch > Advisory > Statement) and the severity of the underlying hazard. Not official policy.
#   5 = catastrophic / life-threatening   4 = warning-level danger   3 = elevated (major watch / moderate warning)
#   2 = watch / advisory                  1 = minor
EVENT_TABLE = {
    "Tornado Warning": ("tornado", 4), "Tornado Watch": ("tornado", 2),
    "Severe Thunderstorm Warning": ("convective", 3), "Severe Thunderstorm Watch": ("convective", 2),
    "Hurricane Warning": ("tropical", 5), "Hurricane Watch": ("tropical", 3),
    "Extreme Wind Warning": ("tropical", 5), "Tropical Storm Warning": ("tropical", 4),
    "Tropical Storm Watch": ("tropical", 2), "Storm Surge Warning": ("surge", 5), "Storm Surge Watch": ("surge", 3),
    "Flash Flood Warning": ("flood", 4), "Flash Flood Watch": ("flood", 2), "Flood Warning": ("flood", 3),
    "Flood Watch": ("flood", 2), "Flood Advisory": ("flood", 1), "Coastal Flood Warning": ("flood", 3),
    "Coastal Flood Watch": ("flood", 2), "Coastal Flood Advisory": ("flood", 1),
    "Blizzard Warning": ("winter", 4), "Ice Storm Warning": ("winter", 4), "Winter Storm Warning": ("winter", 4),
    "Winter Storm Watch": ("winter", 2), "Winter Weather Advisory": ("winter", 2), "Freezing Rain Advisory": ("winter", 2),
    "Wind Chill Warning": ("cold", 3), "Extreme Cold Warning": ("cold", 3), "Wind Chill Advisory": ("cold", 2),
    "High Wind Warning": ("wind", 3), "High Wind Watch": ("wind", 2), "Wind Advisory": ("wind", 1),
    "Excessive Heat Warning": ("heat", 3), "Extreme Heat Warning": ("heat", 3), "Heat Advisory": ("heat", 2),
    "Dense Fog Advisory": ("fog", 1), "Dense Smoke Advisory": ("smoke", 1), "Air Quality Alert": ("smoke", 1),
    "Red Flag Warning": ("fire", 2),
}
# hazard classes that can plausibly block or endanger a commute (used for the employee-impact estimate)
TRAVEL_IMPACT_CLASSES = {"tornado", "convective", "tropical", "surge", "flood", "winter", "wind"}
_URGENCY_W = {"Immediate": 30, "Expected": 20, "Future": 10}
_CERTAINTY_W = {"Observed": 9, "Likely": 6, "Possible": 3}
_SEVERITY_W = {"Extreme": 4, "Severe": 3, "Moderate": 2, "Minor": 1}
_SEV_DEFAULT_LEVEL = {"Extreme": 4, "Severe": 3, "Moderate": 2, "Minor": 1}
_MARINE_PREFIXES = ("AM", "GM", "PZ", "PK", "PH", "PM", "LS", "LM", "LH", "LE", "LO", "SL")


def _now():
    return datetime.now(timezone.utc)


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def classify(event, description, severity):
    cls, level = EVENT_TABLE.get(event, (None, None))
    if cls is None:
        cls, level = "other", _SEV_DEFAULT_LEVEL.get(severity, 1)
    text = (description or "").upper()
    if "FLASH FLOOD EMERGENCY" in text or "TORNADO EMERGENCY" in text or "PARTICULARLY DANGEROUS SITUATION" in text:
        level = 5
    return cls, level


def priority_score(level, urgency, certainty, severity):
    return level * 100 + _URGENCY_W.get(urgency, 0) + _CERTAINTY_W.get(certainty, 0) + _SEVERITY_W.get(severity, 0)


def _finish(a):
    a["hazard_class"], a["base_level"] = classify(a.get("event"), a.get("description"), a.get("severity"))
    a["travel_impacting"] = a["hazard_class"] in TRAVEL_IMPACT_CLASSES
    a["priority_score"] = priority_score(a["base_level"], a.get("urgency"), a.get("certainty"), a.get("severity"))
    return a


def in_effect(alert, as_of):
    """('active'|'upcoming'|'expired', hours until onset or None)"""
    start = parse_ts(alert.get("onset")) or parse_ts(alert.get("effective")) or parse_ts(alert.get("sent"))
    end = parse_ts(alert.get("ends")) or parse_ts(alert.get("expires"))
    if end and as_of >= end:
        return "expired", None
    if start and as_of < start:
        return "upcoming", round((start - as_of).total_seconds() / 3600, 2)
    return "active", 0.0


# ---------------------------------------------------------------- live NWS
_zone_cache, _zone_lock = {}, threading.Lock()
_alert_cache = {}


def _zone_geometry(url):
    with _zone_lock:
        if url in _zone_cache:
            return _zone_cache[url]
    try:
        g = nws_client.fetch_json(url).get("geometry")
    except Exception:
        g = None
    with _zone_lock:
        _zone_cache[url] = g
    return g


def _resolve_geometry(props, feature_geometry):
    """Return (geojson|None, kind). Polygon alerts carry their own geometry; the rest are unions of NWS zone shapes."""
    if feature_geometry:
        return mapping(shape(feature_geometry).simplify(0.002)), "polygon"
    zones = [z for z in (props.get("affectedZones") or []) if z.rsplit("/", 1)[-1][:2] not in _MARINE_PREFIXES][:80]
    if not zones:
        return None, "none"
    with ThreadPoolExecutor(8) as ex:
        shapes = [shape(g) for g in ex.map(_zone_geometry, zones) if g]
    if not shapes:
        return None, "none"
    return mapping(unary_union(shapes).simplify(0.01)), "county_zone"


def _normalize_live(feature, retrieved_at):
    p = feature.get("properties", {})
    geom, kind = _resolve_geometry(p, feature.get("geometry"))
    a = {
        "id": feature.get("id") or p.get("id"), "event": p.get("event"), "headline": p.get("headline"),
        "description": p.get("description"), "instruction": p.get("instruction"),
        "severity": p.get("severity"), "urgency": p.get("urgency"), "certainty": p.get("certainty"),
        "status": p.get("status"), "message_type": p.get("messageType"), "areaDesc": p.get("areaDesc"),
        "sent": p.get("sent"), "effective": p.get("effective"), "onset": p.get("onset"),
        "expires": p.get("expires"), "ends": p.get("ends"), "sender": p.get("senderName"),
        "geometry": geom, "geometry_kind": kind,
        "source": "NWS API api.weather.gov", "source_url": feature.get("id"), "retrieved_at": retrieved_at,
    }
    return _finish(a)


MAX_REGIONAL_KM = 150


def _distance_km(alert, lat, lon):
    if not alert.get("geometry"):
        return None
    from shapely.geometry import Point
    return round(shape(alert["geometry"]).distance(Point(lon, lat)) * 111.0, 1)   # degrees -> km, approximate


def live_picture(facility, horizon_hours=36):
    """Real current NWS data for a facility. Failures are returned in `errors`, never papered over."""
    now = _now()
    retrieved = now.isoformat()
    state = facility["state"]
    errors, alerts, sources = [], [], []
    lat, lon = facility["latitude"], facility["longitude"]

    cache_key = (state,)
    cached = _alert_cache.get(cache_key)
    if cached and time.time() - cached[0] < 120:
        features, area_retrieved = cached[1], cached[2]
    else:
        url = f"{nws_client.NWS_BASE_URL}/alerts/active"
        try:
            data = nws_client.fetch_json(url, params={"area": state, "status": "actual"})
            features, area_retrieved = data.get("features", []), retrieved
            _alert_cache[cache_key] = (time.time(), features, area_retrieved)
        except Exception as e:
            features, area_retrieved = [], retrieved
            errors.append(f"NWS area alerts for {state} failed: {e}")
    sources.append(f"{nws_client.NWS_BASE_URL}/alerts/active?area={state}&status=actual")

    point_ids = None
    try:
        point_ids = {a["id"] for a in nws_client.fetch_alerts(lat, lon)}
        sources.append(f"{nws_client.NWS_BASE_URL}/alerts/active?point={lat},{lon}")
    except Exception as e:
        errors.append(f"NWS point alerts failed: {e}")

    for f in features:
        p = f.get("properties", {})
        cls, _ = classify(p.get("event"), p.get("description"), p.get("severity"))
        if cls == "other" and p.get("severity") not in ("Extreme", "Severe"):
            continue
        covers_point = (f.get("id") in point_ids) if point_ids is not None else None
        # resolve geometry only for alerts that matter (cover the facility, or are polygons)
        if not covers_point and not f.get("geometry"):
            continue
        a = _normalize_live(f, area_retrieved)
        a["nws_says_covers_facility_point"] = covers_point
        a["distance_km"] = 0.0 if covers_point else _distance_km(a, lat, lon)
        if not covers_point and (a["distance_km"] is None or a["distance_km"] > MAX_REGIONAL_KM):
            continue
        state_, hrs = in_effect(a, now)
        if state_ == "expired" or (state_ == "upcoming" and hrs > horizon_hours):
            continue
        alerts.append(a)

    weather = None
    try:
        w = nws_client.fetch_weather(lat, lon)
        weather = {
            "observation": w.get("observation"), "observation_station": (w.get("observation_stations") or [{}])[0],
            "forecast": [{k: pd.get(k) for k in ("name", "startTime", "temperature", "temperatureUnit", "windSpeed",
                                                  "shortForecast", "probabilityOfPrecipitation")}
                         for pd in w.get("forecast", [])[:6]],
            "grid": w["location"], "retrieved_at": retrieved,
        }
        sources.extend(w.get("sources", []))
    except Exception as e:
        errors.append(f"NWS forecast/observation failed: {e}")

    alerts.sort(key=lambda a: -a["priority_score"])
    return {
        "mode": "live", "scenario": None, "as_of": retrieved, "retrieved_at": retrieved,
        "alerts": alerts, "weather": weather, "sources": sources, "errors": errors,
        "disclaimer": None,
    }


# ---------------------------------------------------------------- historical replay
def list_replay_scenarios():
    out = []
    for p in sorted(config.REPLAY_DIR.glob("*.json")):
        d = json.loads(p.read_text())
        out.append({"scenario_id": d["scenario_id"], "title": d.get("title"), "disclaimer": d.get("disclaimer"),
                    "snapshots": [{"index": i, "as_of": s["as_of"], "label": s.get("label")}
                                  for i, s in enumerate(d.get("snapshots", []))]})
    return out


def replay_picture(scenario_id, snapshot_index):
    matches = [p for p in config.REPLAY_DIR.glob("*.json") if json.loads(p.read_text()).get("scenario_id") == scenario_id]
    if not matches:
        raise KeyError(f"unknown replay scenario: {scenario_id}")
    d = json.loads(matches[0].read_text())
    snap = d["snapshots"][snapshot_index]
    retrieved = _now().isoformat()
    alerts = []
    for raw in snap.get("alerts", []):
        a = {k: raw.get(k) for k in ("id", "event", "headline", "description", "instruction", "severity", "urgency",
                                     "certainty", "status", "message_type", "areaDesc", "sent", "effective", "onset",
                                     "expires", "ends", "sender", "geometry", "geometry_kind")}
        a["status"] = a["status"] or "Actual"
        a["source"] = f"HISTORICAL ARCHIVE ({d.get('title')})"
        a["source_url"] = raw.get("source_url")
        a["retrieved_at"] = retrieved
        alerts.append(_finish(a))
    alerts.sort(key=lambda a: -a["priority_score"])
    obs = (snap.get("observations") or [None])[0]
    return {
        "mode": "replay", "scenario": {"scenario_id": d["scenario_id"], "title": d.get("title"), "label": snap.get("label"),
                                         "snapshot_index": snapshot_index, "facts": d.get("facts")},
        "as_of": snap["as_of"], "retrieved_at": retrieved, "alerts": alerts,
        "weather": {"observation": obs, "observations": snap.get("observations"), "forecast": None} if obs else None,
        "sources": [s.get("url") for s in d.get("sources", [])], "errors": [],
        "disclaimer": d.get("disclaimer"),
    }
