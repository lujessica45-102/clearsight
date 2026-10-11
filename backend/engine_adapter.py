"""Adapters between the teammates' office records and the decision engine in closure/.

Shared by backend/connect.py (the /api/current snapshot) and backend/decide.py (AI second opinions).
Nothing here fetches weather: pictures come from closure.hazards.picture_at.
"""
import hashlib
import json
import os
import random
import threading
from datetime import timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AI_DIR = ROOT / "backend" / "ai_results"

from closure import engine, hazards, impact as impact_mod, roads as roads_mod, store, synthetic   # noqa: E402
from closure.sectors import POSTURE_LABELS                                                          # noqa: E402

# Agency -> engine sector (closure/sectors.py)
SECTOR_OF_AGENCY = {"NRCS": "service_center", "FSA": "service_center", "RD": "service_center",
                    "ARS": "research_lab", "FS": "field_office", "APHIS": "field_office"}
STATUS_OF = {"closure": "closed", "telework": "telework", "delayed_arrival": "delay", "early_dismissal": "delay", "normal": "normal"}
HEADCOUNT = {"service_center": (12, 22), "research_lab": (20, 34), "field_office": (14, 26), "headquarters": (30, 50)}


def sector_for(agency):
    token = (agency or "").upper().replace("USDA", "").strip().split(" ")[0]
    return SECTOR_OF_AGENCY.get(token, "service_center")


def timezone_for(state, lon):
    if state == "CA":
        return "America/Los_Angeles"
    if state == "FL":
        return "America/Chicago" if lon <= -85.0 else "America/New_York"   # Panhandle west of the Apalachicola is Central
    return "America/Chicago"


def synthetic_employees(o):
    """Made-up staff (fixed seed per office, same role/rate tables as closure/synthetic.py). Service centers are
    generated exactly as before so earlier results stay reproducible."""
    sector = sector_for(o.get("agency"))
    rng = random.Random(f"clearsight-{o['id']}")
    lo, hi = HEADCOUNT[sector]
    n = rng.randint(lo, hi)
    town = o["address"].split(",")[-2].strip()
    ess, tw = synthetic._ESSENTIAL_RATE[sector], synthetic._TELEWORK_RATE[sector]
    out = []
    for i in range(n):
        spread_km = rng.choice([4, 8, 15, 25])
        lat = o["lat"] + rng.gauss(0, spread_km / 111.0)
        lon = o["lon"] + rng.gauss(0, spread_km / (111.0 * 0.87))
        dn, de = lat - o["lat"], lon - o["lon"]
        side = ("north" if dn > 0 else "south") if abs(dn) > abs(de) else ("east" if de > 0 else "west")
        essential = rng.random() < ess
        out.append({
            "id": f"{o['id']}-{i + 1:03d}", "facility_id": o["id"],
            "home_community": town if spread_km <= 4 else f"{side} of {town}",
            "home_lat": round(lat, 5), "home_lon": round(lon, 5),
            "role_category": rng.choice(synthetic._ROLES[sector]),
            "essential": essential, "telework_eligible": (not essential) and rng.random() < tw / (1 - ess),
            "accessibility_need": rng.random() < 0.06,
        })
    return out


def to_engine_facility(o, emps):
    sector = sector_for(o.get("agency"))
    return {
        "id": o["id"], "name": o["name"], "sector": sector,
        "latitude": o["lat"], "longitude": o["lon"],
        "timezone": timezone_for(o["state"], o["lon"]),
        "opening_time": "08:00", "closing_time": "16:30", "state": o["state"],
        "headcount": len(emps), "synthetic_employees": True,
        "telework_available": any(e["telework_eligible"] for e in emps),
        "essential_staff_required": any(e["essential"] for e in emps),
        "accessibility_support_needed": any(e["accessibility_need"] for e in emps),
    }


def evaluate_nolog(o, picture):
    """The same steps as closure.workflow.evaluate_picture, without writing an audit record."""
    emps = synthetic_employees(o)
    fac = to_engine_facility(o, emps)
    as_of = hazards.parse_ts(picture["as_of"])
    win = engine.operating_window(fac, as_of)
    imp = impact_mod.analyze_employees(fac, emps, picture["alerts"], win["window_start"], win["window_end"])
    rd = roads_mod.road_conditions(fac, picture["mode"])
    det = engine.evaluate(fac, picture, imp, rd, as_of)
    return fac, imp, rd, det


# ---------------------------------------------------------------- audit log (deduplicated)
_idx_lock = threading.Lock()


def _index_path():
    return Path(os.getenv("CLEARSIGHT_DATA_DIR") or Path.home() / ".clearsight") / "snapshot_evaluations.json"


def log_evaluation(fac, picture, imp, rd, det):
    """Append one audit record per distinct (facility, as-of minute, alerts, posture). Browsing the dashboard again
    does not add records. Alert geometry is omitted from the stored picture to keep the log small."""
    # archive/recent: one record per distinct moment; live: the moment moves every minute, so one per 6-hour window unless alerts/posture change
    moment = picture["as_of"][:10] + f"h{int(picture['as_of'][11:13]) // 6}" if picture["mode"] == "live" else picture["as_of"][:16]
    key = hashlib.sha256(json.dumps([fac["id"], picture["mode"], moment, sorted(a["id"] or "" for a in picture["alerts"]), det["posture"]]).encode()).hexdigest()
    with _idx_lock:
        p = _index_path()
        index = {}
        if p.exists():
            try:
                index = json.loads(p.read_text())
            except Exception:
                index = {}
        if key in index:
            return index[key]["evaluation_id"], index[key]["record"]
        slim_picture = {**picture, "alerts": [{**a, "geometry": None} for a in picture["alerts"]]}
        eid = store.new_evaluation_id()
        rec = store.append(eid, fac["id"], "evaluation", {"facility": fac, "picture": slim_picture, "impact": imp, "roads": rd,
                                                          "deterministic": det, "note": "dashboard evaluation; alert geometry omitted"})
        index[key] = {"evaluation_id": eid, "record": rec}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(index))
        return eid, rec


# ---------------------------------------------------------------- engine payload (decide.slim shape)
def slim(fac, picture, imp, rd, det, evaluation_id, record, ai=None):
    det = dict(det)
    det.pop("evidence", None)
    people = [{k: p[k] for k in ("id", "home_community", "home_lat", "home_lon", "role_category", "essential", "telework_eligible",
                                 "accessibility_need", "commute_risk", "worst_event", "commute_km_straight_line")} for p in imp["people"]]
    covers = {a["id"] for a in imp["facility_alerts"]}
    alerts = [{"id": a["id"], "event": a["event"], "level": a["base_level"], "sender": a.get("sender"), "issued": a["sent"],
               "covers_facility": a["id"] in covers, "source_url": a.get("source_url")} for a in picture["alerts"]]
    return {"facility_id": fac["id"], "evaluation_id": evaluation_id, "record": record,
            "engine_facility": fac, "deterministic": det, "metrics": imp["metrics"],
            "by_community": imp["by_community"], "impact_note": imp["method_note"],
            "alerts": alerts, "roads": rd, "employees": people, **(ai or {})}


# ---------------------------------------------------------------- stored AI results
def as_of_key(as_of):
    """Minute-resolution UTC key used in ai_results file names."""
    return as_of.astimezone(timezone.utc).strftime("%Y%m%dT%H%MZ")


def ai_path(facility_id, as_of):
    return AI_DIR / f"{facility_id}@{as_of_key(as_of)}.json"


def load_ai(facility_id, as_of):
    p = ai_path(facility_id, as_of)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def save_ai(facility_id, as_of, result):
    AI_DIR.mkdir(parents=True, exist_ok=True)
    ai_path(facility_id, as_of).write_text(json.dumps(result, indent=1, default=str))


__all__ = ["POSTURE_LABELS", "STATUS_OF"]
