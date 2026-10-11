"""Connects the teammates' backend (parser/) to the React frontend.

All weather and facility data comes from the teammates' code:
  - parser.facilities.FacilityStore / geocode_address  -> the offices
  - parser.nws_client.build_weather_report             -> live NWS alerts, forecast, observation
This file only RESHAPES that data into the format the frontend reads (see MOCK in
frontend/src/data.js). It makes no closure decisions: the decision fields are left
empty until the team's decision logic exists.

Commands (run from the repo root):
  python -m backend.connect --seed 6     load + geocode the first 6 offices from parser/facilities.db
  python -m backend.connect              print a summary of the live snapshot
  python -m backend.connect --json       print the full snapshot
"""
import os, re, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from parser.facilities import FacilityStore, geocode_address   # teammates' code
from parser.nws_client import build_weather_report             # teammates' code

DB_PATH = os.getenv("FACILITIES_DATABASE", str(ROOT / "facilities.db"))
SEED_SQL = ROOT / "parser" / "facilities.db"   # the teammates' list of Florida offices (SQL text)
LIMIT = int(os.getenv("LIVE_FACILITY_LIMIT", "100"))  # show every facility in the database

# Teammates' operating statuses -> the frontend's status names
STATUS_MAP = {"normal": "normal", "delayed_opening": "delay", "early_dismissal": "delay",
              "telework": "telework", "temporarily_closed": "closed", "unknown": "unknown"}


def store():
    return FacilityStore(DB_PATH)


# ---------- one-time setup: put the teammates' office list into their database ----------
def seed(count):
    # Read name + address from each entry in the teammates' list. (The file is SQL text, but its rows
    # don't all have the same number of fields, so we pull out the first three quoted values per row.)
    text = SEED_SQL.read_text()
    rows = re.findall(r"\(\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)'", text)
    offices = [(n.replace("''", "'"), addr.replace("''", "'")) for n, _agency, addr in rows]
    s, added = store(), 0
    existing = {f["name"] for f in s.all()}
    for name, address in offices:
        if added >= count:
            break
        if name in existing:
            continue
        try:
            lat, lon, matched = geocode_address(address)          # teammates' geocoder
        except Exception as e:
            print(f"  skipped {name}: {e}")
            continue
        s.add({"id": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"), "name": name, "address": matched,
               "latitude": lat, "longitude": lon, "opening_time": "08:00", "closing_time": "16:30",
               "telework_available": True, "essential_staff_required": True,
               "transportation_support_needed": False, "accessibility_support_needed": False})
        added += 1
        print(f"  added {name} ({lat:.4f}, {lon:.4f})")
    print(f"Done: {added} offices added to {DB_PATH}")


# ---------- reshape the teammates' weather report for the frontend ----------
def hazard_type(event):
    e = (event or "").lower()
    for words, t in [(("tornado",), "tornado"), (("hurricane", "tropical", "storm surge"), "hurricane"),
                     (("flood",), "flood"), (("fire", "red flag"), "fire"), (("heat",), "heat"),
                     (("winter", "ice", "snow", "blizzard", "freez", "cold"), "winter"), (("wind",), "wind")]:
        if any(w in e for w in words):
            return t
    return "default"


SEV = {"Extreme": 4, "Severe": 3, "Moderate": 2, "Minor": 1}


def readable(ts):
    """'2026-10-11T06:00:00-04:00' -> 'Sun 6:00 AM' (in the alert's own time zone)."""
    try:
        return datetime.fromisoformat(ts).strftime("%a %I:%M %p").replace(" 0", " ")
    except Exception:
        return ts or "—"


def to_frontend(fac, report):
    alerts = sorted(report["alerts"], key=lambda a: SEV.get(a.get("severity"), 0), reverse=True)
    top = alerts[0] if alerts else None
    obs = (report["weather"] or {}).get("observation") or {}
    hourly = (report["weather"] or {}).get("hourly_forecast") or []

    bullets = [a.get("headline") or a.get("event") for a in alerts[:3]]
    if obs.get("conditions"):
        t = obs.get("temperature")
        bullets.append(f"Now: {obs['conditions']}" + (f", {t * 9 / 5 + 32:.0f}°F" if isinstance(t, (int, float)) else ""))
    if hourly:
        bullets.append(f"Next hour: {hourly[0].get('shortForecast')}")

    return {
        "id": fac["id"], "name": fac["name"],
        "short": fac["name"].replace(" Service Center", "").replace(" County FSA", " FSA"),
        "lat": fac["latitude"], "lon": fac["longitude"], "address": fac["address"],
        "status": STATUS_MAP.get(fac.get("operating_status"), "unknown"),
        "total": None, "affected": None,             # no employee data in the backend yet
        "bullets": bullets or ["No active NWS alerts for this office."],
        "alert": ({"type": hazard_type(top.get("event")), "title": top.get("event"),
                   "area": (top.get("affected_areas") or "")[:80], "expires": readable(top.get("expires")),
                   "source": top.get("sender") or "National Weather Service"} if top else None),
        "alerts": alerts,                              # full list from the teammates' parser
        "weatherCapturedAt": report["captured_at"],
        "dataSources": report["data_sources"],
        # Decision fields stay empty until the team's decision logic exists:
        "opinion": None, "reasoning": None, "email": None,
    }


def build_snapshot():
    facs = store().all(include_permanently_closed=False)[:LIMIT]

    def one(fac):
        try:
            return to_frontend(fac, build_weather_report(fac))   # teammates' weather report
        except Exception as e:
            return ({"id": fac["id"], "name": fac["name"], "short": fac["name"], "lat": fac["latitude"],
                        "lon": fac["longitude"], "status": "unknown", "total": None, "affected": None,
                        "bullets": [f"Weather check failed: {e}"], "alert": None, "alerts": [],
                        "opinion": None, "reasoning": None, "email": None})

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=6) as pool:   # check several offices at once
        out = list(pool.map(one, facs))
    worst = max((f for f in out if f["alert"]), key=lambda f: SEV.get(f["alerts"][0].get("severity"), 0), default=None)
    return {"mode": "live", "generated_at": datetime.now(timezone.utc).isoformat(),
            "alert": worst["alert"] if worst else {"type": "default", "title": "No active warnings",
                                                   "area": "Monitored offices", "expires": "—",
                                                   "source": "National Weather Service"},
            "facilities": out, "employees": []}


if __name__ == "__main__":
    if "--seed" in sys.argv:
        seed(int(sys.argv[sys.argv.index("--seed") + 1]) if len(sys.argv) > sys.argv.index("--seed") + 1 else LIMIT)
    else:
        import json
        snap = build_snapshot()
        if "--json" in sys.argv:
            print(json.dumps(snap, indent=2, default=str))
        else:
            print("Alert:", snap["alert"]["title"])
            for f in snap["facilities"]:
                print(f"- {f['name']}: {len(f.get('alerts', []))} alert(s) | {f['bullets'][0]}")
