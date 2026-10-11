"""Road closure / travel-condition signal.

State 511 feeds need developer API keys. Without a key this module reports status="unavailable" with the
reason; it NEVER invents closures. The keyed fetch below follows the Iteris-style 511 developer API
(fl511.com / 511 Nebraska) but has NOT been exercised against a live key during development.
"""
import requests

from . import config
from .geo import haversine_km

_ENDPOINTS = {
    "NE": ("https://511.nebraska.gov/api/v2/get/event", lambda: config.NE511_API_KEY, "Nebraska 511"),
    "FL": ("https://fl511.com/api/v2/get/event", lambda: config.FL511_API_KEY, "Florida 511"),
}


def road_conditions(facility, mode, radius_km=60):
    state = facility["state"]
    base = {"status": "unavailable", "source": _ENDPOINTS[state][2], "events": [], "reason": None}
    if mode == "replay":
        base["reason"] = "No archived 511 road data is available for this historical scenario."
        return base
    url, key_fn, name = _ENDPOINTS[state]
    key = key_fn()
    if not key:
        base["reason"] = f"{name} requires a developer API key ({state}511_API_KEY not set). Road closures were NOT evaluated."
        return base
    try:
        r = requests.get(url, params={"key": key, "format": "json"}, timeout=20)
        r.raise_for_status()
        events = []
        for e in r.json():
            lat, lon = e.get("Latitude"), e.get("Longitude")
            if lat is None or lon is None:
                continue
            d = haversine_km(facility["latitude"], facility["longitude"], lat, lon)
            if d <= radius_km and (e.get("IsFullClosure") or "clos" in str(e.get("EventType", "")).lower()):
                events.append({"id": e.get("ID"), "road": e.get("RoadwayName"), "type": e.get("EventType"),
                               "full_closure": bool(e.get("IsFullClosure")), "description": e.get("Description"),
                               "last_updated": e.get("LastUpdated"), "lat": lat, "lon": lon, "distance_km": round(d, 1)})
        return {"status": "ok", "source": name, "events": events, "reason": None, "radius_km": radius_km}
    except Exception as ex:
        base["reason"] = f"{name} request failed: {ex}"
        return base
