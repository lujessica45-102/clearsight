"""Archived NWS products from the Iowa Environmental Mesonet (IEM), queried live for a point and an exact moment.

Nothing is stored in the repo: each call fetches (or reads a labelled cached copy of) real archive responses.

How it works
  - Zone/county based alerts (hurricane/storm surge/flood/winter/fire weather ...):
        /api/1/vtec/county_zone.geojson?valid=<minute>   every zone-based alert valid at that exact minute, with zone
        geometry. One nationwide response per minute, shared by every facility evaluated at that moment, so there is no
        "issue-date lookback" problem (the by-point endpoint only matches on issue DATE).
  - Storm-based polygons (tornado / severe thunderstorm / flash flood / extreme wind warnings):
        /api/1/vtec/sbw_interval.geojson?begints=&endts=&wfo=...   filtered to polygons valid at the moment.
  - Observations: /geojson/network/<ST>_ASOS.geojson (stations) + /api/1/obhistory.json (one day of obs).

Known limits (stated to the caller via `notes`): archived records carry no CAP severity/urgency/certainty and no
product text (so "emergency" wording cannot be detected); `expires` is IEM's FINAL archived end time, which can include
later extensions or cancellations (a small hindsight leak); the VTEC archive starts around 2005.
"""
import math
import threading
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from shapely.geometry import Point, mapping, shape
from shapely.ops import unary_union

try:
    from . import http_cache
except ImportError:      # imported as a top-level module (parser/ on sys.path)
    import http_cache

IEM_API = "https://mesonet.agron.iastate.edu/api/1"
IEM_GEOJSON = "https://mesonet.agron.iastate.edu/geojson"
NWS_BASE = "https://api.weather.gov"
SOURCE = "IEM archive of NWS products"
MARINE_PREFIXES = ("AM", "GM", "PZ", "PK", "PH", "PM", "LS", "LM", "LH", "LE", "LO", "SL")
KM_PER_DEG = 111.0
SBW_LOOKBACK_HOURS = 24

_zone_lock = threading.Lock()
_zone_memo = OrderedDict()   # valid-minute -> parsed zone features (kept small: ~2k shapes each)


def _minute(dt):
    return dt.astimezone(timezone.utc).replace(second=0, microsecond=0)


def _iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _parse(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _dist_km(geom, pt):
    return geom.distance(pt) * KM_PER_DEG


def _src(meta):
    return {"url": meta["url"], "cached": meta["cached"], "retrieved_at": meta["retrieved_at"], "stale": meta.get("stale", False)}


def _vtec_id(wfo, ph, sig, eventid, when):
    return f"VTEC:{wfo}.{ph}.{sig}.{int(eventid):04d}.{when.year if when else ''}"


def _event_url(wfo, ph, sig, eventid, when):
    return f"https://mesonet.agron.iastate.edu/vtec/?year={when.year if when else ''}&wfo=K{wfo}&phenomena={ph}&significance={sig}&eventid={int(eventid):04d}"


def _zone_features(valid):
    """Parsed (props, shape) for every non-marine zone alert valid at `valid` (a minute-resolution datetime)."""
    key = _iso(valid)
    with _zone_lock:
        if key in _zone_memo:
            _zone_memo.move_to_end(key)
            feats, src = _zone_memo[key]
            return feats, {**src, "cached": True}   # served from memory: a copy of the original response
    data, meta = http_cache.cached_get_json(f"{IEM_API}/vtec/county_zone.geojson", {"valid": key}, ttl_seconds=None, timeout=90)
    feats = []
    for f in data.get("features", []):
        p = f.get("properties", {})
        if not f.get("geometry") or (p.get("ugc") or "")[:2] in MARINE_PREFIXES:
            continue
        try:
            feats.append((p, shape(f["geometry"])))
        except Exception:
            continue
    out = (feats, _src(meta))
    with _zone_lock:
        _zone_memo[key] = out
        while len(_zone_memo) > 3:
            _zone_memo.popitem(last=False)
    return out


def _cwa_and_state(lat, lon):
    """Forecast office (CWA) and state for a point via api.weather.gov/points (works for any date; cached forever)."""
    data, meta = http_cache.cached_get_json(f"{NWS_BASE}/points/{lat:.4f},{lon:.4f}", None, ttl_seconds=None,
                                            headers={"Accept": "application/geo+json"})
    p = data.get("properties", {})
    return p.get("cwa"), (p.get("relativeLocation", {}).get("properties", {}) or {}).get("state"), p.get("timeZone"), _src(meta)


def _zone_alerts(lat, lon, as_of, radius_km, notes, sources):
    feats, src = _zone_features(_minute(as_of))
    sources.append(src)
    pt = Point(lon, lat)
    groups = {}
    for p, g in feats:
        k = (p["wfo"], p["phenomena"], p["significance"], p["eventid"])
        groups.setdefault(k, []).append((p, g))
    alerts, wfos = [], set()
    for (wfo, ph, sig, eid), zs in groups.items():
        d = min(_dist_km(g, pt) for _, g in zs)
        if d > radius_km:
            continue
        wfos.add(wfo)
        p0 = zs[0][0]
        sent, begin, end = _parse(p0.get("utc_product_issue")), _parse(p0.get("utc_issue")), _parse(p0.get("utc_expire"))
        union = unary_union([g for _, g in zs]).simplify(0.01)
        ugcs = sorted({p["ugc"] for p, _ in zs})
        alerts.append({
            "id": _vtec_id(wfo, ph, sig, eid, begin or sent), "event": p0["event_label"],
            "headline": f"{p0['event_label']} issued by NWS {wfo} (archived record)",
            "description": "Archived NWS VTEC record. The full product text was not retrieved, so emergency wording cannot be checked.",
            "instruction": None, "severity": None, "urgency": None, "certainty": None, "status": "Actual", "message_type": "Alert",
            "areaDesc": "UGC zones: " + ", ".join(ugcs[:14]) + (f" (+{len(ugcs) - 14} more)" if len(ugcs) > 14 else ""),
            "sent": sent.isoformat() if sent else None, "effective": sent.isoformat() if sent else None,
            "onset": begin.isoformat() if begin else None,
            # IEM's expire is the FINAL archived end (may include later extension/cancellation); drop it if it precedes the start
            "expires": end.isoformat() if end and begin and end > begin else None, "ends": None, "sender": f"NWS {wfo}",
            "geometry": mapping(union), "geometry_kind": "county_zone", "distance_km": round(d, 1),
            "covers_point": any(g.contains(pt) for _, g in zs), "expires_is_final_archived": True,
            "source": SOURCE, "source_url": _event_url(wfo, ph, sig, eid, begin or sent),
        })
    return alerts, wfos


def _sbw_alerts(lat, lon, as_of, radius_km, wfos, notes, sources):
    if not wfos:
        return []
    pt = Point(lon, lat)
    begin = as_of - timedelta(hours=SBW_LOOKBACK_HOURS)
    data, meta = http_cache.cached_get_json(
        f"{IEM_API}/vtec/sbw_interval.geojson",
        {"begints": _iso(begin), "endts": _iso(_minute(as_of) + timedelta(minutes=1)), "wfo": sorted(wfos), "include_can": "true"},
        ttl_seconds=None, timeout=90)
    sources.append(_src(meta))
    out = []
    for f in data.get("features", []):
        p, geom = f.get("properties", {}), f.get("geometry")
        if not geom:
            continue
        pb, pe = _parse(p.get("utc_polygon_begin")) or _parse(p.get("utc_issue")), _parse(p.get("utc_polygon_end")) or _parse(p.get("utc_expire"))
        if pb and as_of < pb or pe and as_of >= pe:
            continue   # polygon not in force at the requested moment
        g = shape(geom)
        d = _dist_km(g, pt)
        if d > radius_km:
            continue
        issue, expire = _parse(p.get("utc_issue")), _parse(p.get("utc_expire"))
        out.append({
            "id": _vtec_id(p["wfo"], p["phenomena"], p["significance"], p["eventid"], issue),
            "event": p["event_label"], "headline": f"{p['event_label']} issued by NWS {p['wfo']} (archived record)",
            "description": "Archived NWS storm-based warning polygon. The full product text was not retrieved, so emergency wording cannot be checked.",
            "instruction": None, "severity": None, "urgency": None, "certainty": None, "status": "Actual", "message_type": "Alert",
            "areaDesc": p.get("locations") or "Storm-based polygon",
            "sent": issue.isoformat() if issue else None, "effective": pb.isoformat() if pb else None,
            "onset": issue.isoformat() if issue else None, "expires": (pe or expire).isoformat() if (pe or expire) else None,
            "ends": None, "sender": f"NWS {p['wfo']}", "geometry": mapping(g.simplify(0.002)), "geometry_kind": "polygon",
            "distance_km": round(d, 1), "covers_point": g.contains(pt), "expires_is_final_archived": True,
            "source": SOURCE, "source_url": _event_url(p["wfo"], p["phenomena"], p["significance"], p["eventid"], issue),
        })
    return out


def fetch_alerts_at(lat, lon, as_of, radius_km=150, lookback_days=None):
    """Alerts valid at `as_of` (aware datetime) within radius_km of the point, as normalized dicts.

    Returns {"alerts": [...], "cached": bool, "retrieved_at": ISO (oldest source), "sources": [...], "notes": [...]}.
    `lookback_days` is accepted for API symmetry; the valid-at-minute endpoint does not need it.
    """
    notes = ["Archived records have no CAP severity/urgency/certainty or product text; hazard level comes from the NWS product type.",
             "End times are IEM's final archived values and can include later extensions or cancellations."]
    sources = []
    as_of = as_of.astimezone(timezone.utc)
    alerts, wfos = _zone_alerts(lat, lon, as_of, radius_km, notes, sources)
    try:
        cwa, _, _, src = _cwa_and_state(lat, lon)
        sources.append(src)
        if cwa:
            wfos.add(cwa)
    except Exception as e:
        notes.append(f"Could not look up the forecast office for storm-based polygons: {e}")
    try:
        alerts += _sbw_alerts(lat, lon, as_of, radius_km, wfos, notes, sources)
    except Exception as e:
        notes.append(f"Storm-based warning polygons could not be retrieved: {e}")
    oldest = min(s["retrieved_at"] for s in sources)
    for a in alerts:
        a["retrieved_at"] = oldest
        a["cached"] = all(s["cached"] for s in sources)
    return {"alerts": alerts, "cached": all(s["cached"] for s in sources), "retrieved_at": oldest, "sources": sources, "notes": notes}


# ---------------------------------------------------------------- observations
def _station_candidates(lat, lon, state, day):
    data, meta = http_cache.cached_get_json(f"{IEM_GEOJSON}/network/{state}_ASOS.geojson", None, ttl_seconds=None)
    out = []
    for f in data.get("features", []):
        p, c = f["properties"], f["geometry"]["coordinates"]
        b, e = p.get("archive_begin"), p.get("archive_end")
        if (b and b > day) or (e and e < day):
            continue
        d = math.hypot((c[1] - lat) * KM_PER_DEG, (c[0] - lon) * KM_PER_DEG * math.cos(math.radians(lat)))
        out.append((d, p.get("sid"), p.get("sname"), c[1], c[0]))
    return sorted(out)[:4], _src(meta)


def _f_to_c(f):
    return None if f is None else round((f - 32) * 5 / 9, 1)


def fetch_observation_at(lat, lon, as_of, state=None, max_age_hours=3, max_km=80):
    """Latest archived surface observation at/before `as_of` from the nearest ASOS station.

    Returns {"observation": {...}|None, "station": {...}|None, "cached", "retrieved_at", "sources", "notes"}.
    Observation keys mirror parser.nws_client._parse_observation (temperature in C, wind in km/h, visibility in m).
    """
    as_of = as_of.astimezone(timezone.utc)
    notes, sources = [], []
    if not state:
        _, state, _, src = _cwa_and_state(lat, lon)
        sources.append(src)
    if not state:
        return {"observation": None, "station": None, "cached": False, "retrieved_at": None, "sources": sources, "notes": ["State unknown; no station lookup."]}
    day = as_of.strftime("%Y-%m-%d")
    cands, src = _station_candidates(lat, lon, state, day)
    sources.append(src)
    for dist, sid, name, slat, slon in cands:
        if dist > max_km:
            break
        rows = []
        for d in (as_of - timedelta(days=1), as_of):
            data, meta = http_cache.cached_get_json(f"{IEM_API}/obhistory.json", {"network": f"{state}_ASOS", "station": sid, "date": d.strftime("%Y-%m-%d")}, ttl_seconds=None)
            sources.append(_src(meta))
            rows += data.get("data", [])
        best = None
        for r in rows:
            t = _parse(r.get("utc_valid"))
            if t and t <= as_of and as_of - t <= timedelta(hours=max_age_hours) and (best is None or t > best[0]):
                best = (t, r)
        if best:
            t, r = best
            kt = lambda v: None if v is None else round(v * 1.852, 1)
            obs = {"timestamp": t.isoformat(), "temperature": _f_to_c(r.get("tmpf")), "temperature_unit": "wmoUnit:degC",
                   "wind_speed": kt(r.get("sknt")), "wind_gust": kt(r.get("gust")),
                   "visibility": None if r.get("vsby") is None else round(r["vsby"] * 1609.34),
                   "conditions": r.get("wxcodes") or None, "precipitation_last_hour": None if r.get("p01i") is None else round(r["p01i"] * 25.4, 1),
                   "pressure_mb": r.get("mslp"), "raw": r.get("raw")}
            oldest = min(s["retrieved_at"] for s in sources)
            return {"observation": obs, "station": {"id": sid, "name": name, "distance_km": round(dist, 1), "latitude": slat, "longitude": slon},
                    "cached": all(s["cached"] for s in sources), "retrieved_at": oldest, "sources": sources, "notes": notes}
    notes.append(f"No archived observation within {max_km} km and {max_age_hours} h before the requested time.")
    return {"observation": None, "station": None, "cached": all(s["cached"] for s in sources), "retrieved_at": min(s["retrieved_at"] for s in sources),
            "sources": sources, "notes": notes}
