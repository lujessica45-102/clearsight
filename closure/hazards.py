"""Hazard data: live NWS alerts (with geometry) and archived replay snapshots, normalized identically.

Every alert carries provenance (source, retrieved_at, sent/effective/onset/expires) so the audit record can
distinguish when something was issued, when it was retrieved, and when it was evaluated.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from shapely.geometry import shape, mapping
from shapely.ops import unary_union

from parser import nws_client, iem_client  # team's NWS client + the IEM archive client (as-of queries)

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
    # fire weather: conditions warnings, NOT confirmation of an actual fire (NWS carries no evacuation orders / perimeters)
    "Fire Weather Watch": ("fire", 2), "Red Flag Warning": ("fire", 3), "Fire Warning": ("fire", 4),
    "Extreme Fire Danger": ("fire", 3),
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


# ---------------------------------------------------------------- as-of picture (live / recent / archive)
MAX_REGIONAL_KM = 150
_alert_cache = {}


def _zone_geometry(url):
    try:
        return nws_client.fetch_zone_geometry(url)[0]
    except Exception:
        return None


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


def _normalize_feature(feature, retrieved_at, source, cached=False):
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
        "source": source, "source_url": feature.get("id"), "retrieved_at": retrieved_at, "cached": cached,
    }
    return _finish(a)


def _distance_km(alert, lat, lon):
    if not alert.get("geometry"):
        return None
    from shapely.geometry import Point
    return round(shape(alert["geometry"]).distance(Point(lon, lat)) * 111.0, 1)   # degrees -> km, approximate


def _wanted(event, description, severity):
    cls, _ = classify(event, description, severity)
    return not (cls == "other" and severity not in ("Extreme", "Severe"))


def _live_alerts(facility, now, errors, sources):
    state, lat, lon = facility["state"], facility["latitude"], facility["longitude"]
    retrieved = now.isoformat()
    cached = _alert_cache.get(state)
    if cached and time.time() - cached[0] < 120:
        features = cached[1]
    else:
        try:
            data = nws_client.fetch_json(f"{nws_client.NWS_BASE_URL}/alerts/active", params={"area": state, "status": "actual"})
            features = data.get("features", [])
            _alert_cache[state] = (time.time(), features)
        except Exception as e:
            features = []
            errors.append(f"NWS area alerts for {state} failed: {e}")
    sources.append(f"{nws_client.NWS_BASE_URL}/alerts/active?area={state}&status=actual")
    try:
        point_ids = {a["id"] for a in nws_client.fetch_alerts(lat, lon)}
        sources.append(f"{nws_client.NWS_BASE_URL}/alerts/active?point={lat},{lon}")
    except Exception as e:
        point_ids = None
        errors.append(f"NWS point alerts failed: {e}")
    return features, point_ids, retrieved, "NWS API api.weather.gov", False


def _recent_alerts(facility, as_of, now, errors, sources, ds_sources):
    state, lat, lon = facility["state"], facility["latitude"], facility["longitude"]
    features, point_ids, retrieved, cached = [], None, now.isoformat(), False
    try:
        features, meta = nws_client.fetch_alert_features_recent(as_of, area=state, now=now)
        ds_sources.extend(meta["sources"]); retrieved, cached = meta["retrieved_at"], meta["cached"]
        sources.append(meta["sources"][0]["url"] + f" ?area={state}")
    except Exception as e:
        errors.append(f"NWS alert history for {state} failed: {e}")
    try:
        pf, pmeta = nws_client.fetch_alert_features_recent(as_of, point=(lat, lon), now=now)
        point_ids = {f.get("id") for f in pf}
        ds_sources.extend(pmeta["sources"])
    except Exception as e:
        errors.append(f"NWS point alert history failed: {e}")
    return features, point_ids, retrieved, "NWS API alert history (as of the requested time)", cached


def picture_at(facility, as_of=None, horizon_hours=36):
    """Real NWS data for a facility at an as-of moment (aware datetime; None = now).

    mode: 'live' (now) | 'recent' (about the last week: NWS alert history) | 'archive' (older: IEM archive of NWS products).
    Failures are returned in `errors`, never papered over with made-up data.
    """
    now = _now()
    as_of = (as_of or now).astimezone(timezone.utc)
    mode = nws_client.classify_mode(as_of, now)
    lat, lon = facility["latitude"], facility["longitude"]
    errors, alerts, sources, ds_sources, ds_notes = [], [], [], [], []
    weather = None

    if mode == "archive":
        try:
            r = iem_client.fetch_alerts_at(lat, lon, as_of, radius_km=MAX_REGIONAL_KM)
            ds_sources.extend(r["sources"]); ds_notes.extend(r["notes"])
            sources.extend(s["url"] for s in r["sources"])
            for a in r["alerts"]:
                a = _finish(dict(a))
                if not _wanted(a["event"], a["description"], a["severity"]):
                    continue
                a["nws_says_covers_facility_point"] = a.get("covers_point")
                state_, hrs = in_effect(a, as_of)
                if state_ == "expired" or (state_ == "upcoming" and hrs > horizon_hours):
                    continue
                alerts.append(a)
        except Exception as e:
            errors.append(f"Archive alert query failed: {e}")
        try:
            o = iem_client.fetch_observation_at(lat, lon, as_of, state=facility.get("state"))
            ds_sources.extend(o["sources"]); ds_notes.extend(o["notes"])
            if o["observation"]:
                weather = {"observation": o["observation"], "observation_station": o["station"], "forecast": [],
                           "forecast_note": "Forecasts are not available for past times.", "retrieved_at": o["retrieved_at"], "cached": o["cached"]}
        except Exception as e:
            errors.append(f"Archive observation query failed: {e}")
    else:
        if mode == "live":
            features, point_ids, retrieved, source, cached = _live_alerts(facility, now, errors, sources)
        else:
            features, point_ids, retrieved, source, cached = _recent_alerts(facility, as_of, now, errors, sources, ds_sources)
        for f in features:
            p = f.get("properties", {})
            if not _wanted(p.get("event"), p.get("description"), p.get("severity")):
                continue
            covers_point = (f.get("id") in point_ids) if point_ids is not None else None
            if not covers_point and not f.get("geometry"):
                continue   # resolve geometry only for alerts that cover the facility or are polygons
            a = _normalize_feature(f, retrieved, source, cached)
            a["nws_says_covers_facility_point"] = covers_point
            a["distance_km"] = 0.0 if covers_point else _distance_km(a, lat, lon)
            if not covers_point and (a["distance_km"] is None or a["distance_km"] > MAX_REGIONAL_KM):
                continue
            state_, hrs = in_effect(a, as_of)
            if state_ == "expired" or (state_ == "upcoming" and hrs > horizon_hours):
                continue
            alerts.append(a)
        try:
            if mode == "live":
                w = nws_client.fetch_weather(lat, lon)
                weather = {
                    "observation": w.get("observation"), "observation_station": (w.get("observation_stations") or [{}])[0],
                    "forecast": [{k: pd.get(k) for k in ("name", "startTime", "temperature", "temperatureUnit", "windSpeed",
                                                          "shortForecast", "probabilityOfPrecipitation")} for pd in w.get("forecast", [])[:6]],
                    "grid": w["location"], "retrieved_at": now.isoformat(),
                }
                sources.extend(w.get("sources", []))
            else:
                obs, station, meta = nws_client.fetch_observation_recent(lat, lon, as_of, now=now)
                ds_sources.extend(meta["sources"]); ds_notes.extend(meta["notes"])
                if obs:
                    weather = {"observation": obs, "observation_station": station, "forecast": [],
                               "forecast_note": "Forecasts are not available for past times.", "retrieved_at": meta["retrieved_at"], "cached": meta["cached"]}
        except Exception as e:
            errors.append(f"NWS forecast/observation failed: {e}")

    alerts.sort(key=lambda a: -a["priority_score"])
    names = {"live": "NWS API (live)", "recent": "NWS API (alert history, about the last week)", "archive": iem_client.SOURCE}
    cached_all = bool(ds_sources) and all(s.get("cached") for s in ds_sources)
    times = [s["retrieved_at"] for s in ds_sources if s.get("retrieved_at")]
    if mode == "live":
        ds_notes = []
    data_source = {"name": names[mode], "cached": cached_all, "cache_retrieved_at": min(times) if cached_all and times else None,
                   "retrieved_at": min(times) if times else now.isoformat(), "notes": ds_notes}
    disclaimer = None if mode == "live" else (
        f"Archived real NWS products as of {as_of:%Y-%m-%d %H:%M} UTC; not a live alert. "
        + ("Served from the IEM archive. " if mode == "archive" else "Served from the NWS API's alert history. ")
        + ("Cached copy of a real response retrieved " + data_source["cache_retrieved_at"][:19] + " UTC." if data_source["cached"] else ""))
    return {
        "mode": mode, "scenario": None, "as_of": as_of.isoformat(), "retrieved_at": now.isoformat(),
        "alerts": alerts, "weather": weather, "sources": sources, "errors": errors,
        "disclaimer": disclaimer.strip() if disclaimer else None, "data_source": data_source,
    }
