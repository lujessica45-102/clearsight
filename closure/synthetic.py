"""SYNTHETIC USDA facilities and employees. Nothing here is real personnel data.

Facility names, sectors and headcounts are invented for the demo; city/community
coordinates are real places, but every employee home location is a randomly jittered
point near a community centroid, generated from a fixed seed (reproducible).
Seeded into the team's FacilityStore (parser/facilities.py) so the existing store is reused.
"""
import random
from functools import lru_cache

from . import config
from .sectors import SECTORS  # noqa: F401  (re-exported for convenience)

DISCLAIMER = "SYNTHETIC DATA: facilities and employees are fictional demo data, not real USDA records."

# name -> (lat, lon) community centroids (real places)
COMMUNITIES = {
    "Lincoln, NE": (40.8136, -96.7026), "Waverly, NE": (40.9189, -96.5289), "Hickman, NE": (40.6153, -96.6203),
    "Bennet, NE": (40.6806, -96.5081), "Raymond, NE": (40.9514, -96.7864), "Roca, NE": (40.6567, -96.6697),
    "Omaha, NE": (41.2565, -95.9345), "Bellevue, NE": (41.1544, -95.9146), "Papillion, NE": (41.1544, -96.0420),
    "Elkhorn, NE": (41.2889, -96.2403), "Gretna, NE": (41.1403, -96.2392), "Council Bluffs, IA": (41.2619, -95.8608),
    "Blair, NE": (41.5444, -96.1252), "Valley, NE": (41.3119, -96.3447),
    "Pensacola, FL": (30.4213, -87.2169), "Gulf Breeze, FL": (30.3571, -87.1639), "Milton, FL": (30.6324, -87.0397),
    "Perdido Key, FL": (30.3041, -87.4400), "Cantonment, FL": (30.6082, -87.3361),
    "Panama City, FL": (30.1588, -85.6602), "Lynn Haven, FL": (30.2452, -85.6482), "Callaway, FL": (30.1527, -85.5699),
    "Panama City Beach, FL": (30.1766, -85.8055), "Southport, FL": (30.2940, -85.7110), "Mexico Beach, FL": (29.9488, -85.4199),
    "Tallahassee, FL": (30.4383, -84.2807), "Crawfordville, FL": (30.1766, -84.3755), "Quincy, FL": (30.5872, -84.5833),
    "Havana, FL": (30.6226, -84.4141), "Midway, FL": (30.5127, -84.4691),
}

# id, name, sector, lat, lon, tz, hours, headcount, {community: weight}
_FACILITIES = [
    ("ne-lincoln-sc", "Lincoln Service Center", "service_center", 40.8050, -96.6900, "America/Chicago", ("07:30", "16:00"), 28,
     {"Lincoln, NE": 6, "Waverly, NE": 2, "Hickman, NE": 2, "Bennet, NE": 1, "Raymond, NE": 1, "Roca, NE": 1}),
    ("ne-lincoln-lab", "Lincoln Agricultural Research Laboratory", "research_lab", 40.8258, -96.6650, "America/Chicago", ("07:00", "16:30"), 46,
     {"Lincoln, NE": 7, "Waverly, NE": 2, "Hickman, NE": 2, "Bennet, NE": 1, "Roca, NE": 1}),
    ("ne-omaha-fo", "Omaha Field Office", "field_office", 41.2500, -95.9800, "America/Chicago", ("06:30", "15:00"), 34,
     {"Omaha, NE": 5, "Bellevue, NE": 3, "Papillion, NE": 3, "Council Bluffs, IA": 3, "Elkhorn, NE": 2, "Gretna, NE": 1}),
    ("ne-elkhorn-sc", "Elkhorn Service Center", "service_center", 41.2889, -96.2403, "America/Chicago", ("07:30", "16:00"), 22,
     {"Elkhorn, NE": 4, "Omaha, NE": 3, "Valley, NE": 2, "Gretna, NE": 2, "Blair, NE": 1}),
    ("ne-omaha-hq", "Omaha Regional Headquarters", "headquarters", 41.2600, -96.0100, "America/Chicago", ("08:00", "17:00"), 90,
     {"Omaha, NE": 8, "Elkhorn, NE": 3, "Bellevue, NE": 3, "Papillion, NE": 3, "Council Bluffs, IA": 3, "Gretna, NE": 2, "Blair, NE": 1}),
    ("fl-pensacola-sc", "Pensacola Service Center", "service_center", 30.4500, -87.2000, "America/Chicago", ("07:30", "16:00"), 30,
     {"Pensacola, FL": 6, "Gulf Breeze, FL": 2, "Milton, FL": 3, "Cantonment, FL": 2, "Perdido Key, FL": 1}),
    ("fl-pensacola-lab", "Pensacola Coastal Research Station", "research_lab", 30.4010, -87.2150, "America/Chicago", ("07:00", "16:30"), 38,
     {"Pensacola, FL": 6, "Gulf Breeze, FL": 3, "Perdido Key, FL": 3, "Milton, FL": 2}),
    ("fl-panamacity-fo", "Panama City Field Office", "field_office", 30.1760, -85.6900, "America/Chicago", ("06:30", "15:00"), 36,
     {"Panama City, FL": 5, "Lynn Haven, FL": 3, "Callaway, FL": 3, "Panama City Beach, FL": 3, "Southport, FL": 2, "Mexico Beach, FL": 1}),
    ("fl-panamacity-sc", "Panama City Service Center", "service_center", 30.1700, -85.6400, "America/Chicago", ("07:30", "16:00"), 26,
     {"Panama City, FL": 5, "Lynn Haven, FL": 3, "Callaway, FL": 3, "Panama City Beach, FL": 2, "Mexico Beach, FL": 1}),
    ("fl-tallahassee-hq", "Tallahassee Regional Headquarters", "headquarters", 30.4400, -84.2800, "America/New_York", ("08:00", "17:00"), 80,
     {"Tallahassee, FL": 9, "Midway, FL": 3, "Havana, FL": 2, "Quincy, FL": 2, "Crawfordville, FL": 2}),
]

_STATE = {"ne": "NE", "fl": "FL"}
_ROLES = {
    "service_center": ["program technician", "loan specialist", "conservation planner", "clerk"],
    "research_lab": ["research scientist", "lab technician", "animal/plant care technician", "facility operations"],
    "field_office": ["field inspector", "wildlife technician", "field coordinator", "dispatcher"],
    "headquarters": ["analyst", "program manager", "IT specialist", "administrative officer"],
}
_ESSENTIAL_RATE = {"service_center": 0.10, "research_lab": 0.35, "field_office": 0.25, "headquarters": 0.12}
_TELEWORK_RATE = {"service_center": 0.30, "research_lab": 0.20, "field_office": 0.15, "headquarters": 0.85}


def facility_meta():
    return {f[0]: f for f in _FACILITIES}


def _seed_store():
    try:
        from parser.facility_cleaning.facilities import FacilityStore   # current location
    except ImportError:
        from parser.facilities import FacilityStore                     # older layout
    store = FacilityStore(config.FACILITIES_DB)
    have = {f["id"] for f in store.all()}
    for fid, name, sector, lat, lon, tz, (o, c), n, _ in _FACILITIES:
        if fid in have:
            continue
        emps = employees_for(fid)
        store.add({
            "id": fid, "name": f"{name} (synthetic)", "address": f"Synthetic address, {_STATE[fid[:2]]}",
            "latitude": lat, "longitude": lon, "opening_time": o, "closing_time": c,
            "telework_available": any(e["telework_eligible"] for e in emps),
            "essential_staff_required": any(e["essential"] for e in emps),
            "transportation_support_needed": False,
            "accessibility_support_needed": any(e["accessibility_need"] for e in emps),
        })
    return store


def list_facilities():
    """Facilities from the team's FacilityStore (seeded on first use) plus synthetic sector/timezone metadata."""
    store = _seed_store()
    meta = facility_meta()
    out = []
    for f in store.all():
        m = meta.get(f["id"])
        if not m:
            continue
        out.append({
            "id": f["id"], "name": m[1], "sector": m[2], "latitude": f["latitude"], "longitude": f["longitude"],
            "timezone": m[5], "opening_time": f["opening_time"], "closing_time": f["closing_time"],
            "state": _STATE[f["id"][:2]], "headcount": m[7], "synthetic": True,
            "telework_available": bool(f["telework_available"]),
            "essential_staff_required": bool(f["essential_staff_required"]),
            "accessibility_support_needed": bool(f["accessibility_support_needed"]),
        })
    return out


def get_facility(facility_id):
    for f in list_facilities():
        if f["id"] == facility_id:
            return f
    raise KeyError(f"unknown facility: {facility_id}")


@lru_cache(maxsize=None)
def _employees(facility_id):
    fid, name, sector, flat, flon, tz, hours, n, weights = facility_meta()[facility_id]
    rng = random.Random(f"clearsight-{facility_id}")
    names, w = zip(*weights.items())
    emps = []
    for i in range(n):
        comm = rng.choices(names, weights=w)[0]
        clat, clon = COMMUNITIES[comm]
        spread_km = 2.5 if comm.split(",")[0] in ("Lincoln", "Omaha", "Pensacola", "Panama City", "Tallahassee") else 1.5
        lat = clat + rng.gauss(0, spread_km / 111.0)
        lon = clon + rng.gauss(0, spread_km / (111.0 * 0.85))
        essential = rng.random() < _ESSENTIAL_RATE[sector]
        telework = (not essential) and rng.random() < _TELEWORK_RATE[sector] / (1 - _ESSENTIAL_RATE[sector])
        emps.append({
            "id": f"{facility_id}-{i + 1:03d}", "facility_id": facility_id,
            "home_community": comm, "home_lat": round(lat, 5), "home_lon": round(lon, 5),
            "role_category": rng.choice(_ROLES[sector]),
            "essential": essential, "telework_eligible": telework,
            "accessibility_need": rng.random() < 0.06,
        })
    return tuple(emps)


def employees_for(facility_id):
    return [dict(e) for e in _employees(facility_id)]
