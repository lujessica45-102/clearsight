"""Connects the teammates' backend (parser/) and the decision engine (closure/) to the React frontend.

Every weather fact is QUERIED at an as-of moment (closure.hazards.picture_at: live NWS now, NWS alert history for
about the last week, the IEM archive of NWS products for older dates); nothing historical is stored in the code.

Commands (run from the repo root):
  python -m backend.connect --seed all      load + geocode every office in parser/facilities.sql (Florida) and
                                            presets/*.sql (California)
  python -m backend.connect --seed 6        load + geocode only the first 6 not-yet-loaded offices
  python -m backend.connect                 print a summary of the live snapshot
  python -m backend.connect --asof 2018-10-10T09:00:00Z   same, for any moment (UTC, ISO-8601)
  python -m backend.connect --json          print the full snapshot
"""
import os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from parser.facility_cleaning.facilities import FacilityStore, geocode_address   # teammates' code
from closure import clock, hazards, store as audit_store                         # noqa: E402  as-of layer + decision log
from parser import iem_client, nws_client                                        # noqa: E402
from backend import engine_adapter as ea                                         # noqa: E402

SEED_FILES = [ROOT / "parser" / "facilities.sql"] + sorted((ROOT / "presets").glob("*.sql"))   # Florida list + presets (California)
LIMIT = int(os.getenv("LIVE_FACILITY_LIMIT", "200"))   # show every facility in the database
WORKERS = int(os.getenv("SNAPSHOT_WORKERS", "8"))
STATE_RE = re.compile(r",\s*([A-Z]{2})\s+\d{5}")
ROW_RE = re.compile(r"\(\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)'")   # first three quoted values: name, agency, address


def _db_path():
    """FACILITIES_DATABASE if set; else the repo's facilities.db when it already has offices; else ~/.clearsight/
    (keeps SQLite off the iCloud-synced Desktop folder)."""
    if os.getenv("FACILITIES_DATABASE"):
        return os.environ["FACILITIES_DATABASE"]
    repo_db = ROOT / "facilities.db"
    try:
        import sqlite3
        if repo_db.exists() and sqlite3.connect(repo_db).execute("select count(*) from facilities").fetchone()[0] > 0:
            return str(repo_db)
    except Exception:
        pass
    d = Path(os.getenv("CLEARSIGHT_DATA_DIR") or Path.home() / ".clearsight")
    d.mkdir(parents=True, exist_ok=True)
    return str(d / "facilities.db")


DB_PATH = _db_path()


def store():
    return FacilityStore(DB_PATH)


# ---------- office list (SQL files) ----------
@lru_cache(maxsize=1)
def sql_offices():
    """name -> {name, agency, address, state, source_file} from every seed file."""
    out = {}
    for f in SEED_FILES:
        if not f.exists():
            continue
        for n, agency, addr in ROW_RE.findall(f.read_text()):
            n, agency, addr = n.replace("''", "'"), agency.replace("''", "'"), addr.replace("''", "'")
            m = STATE_RE.search(addr)
            out.setdefault(n, {"name": n, "agency": agency, "address": addr, "state": m.group(1) if m else None, "source_file": f.name})
    return out


def _office_id(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ---------- one-time setup: put the office lists into the facility database ----------
def seed(count="all"):
    offices = list(sql_offices().values())
    s = store()
    existing = {f["name"] for f in s.all()}
    todo = [o for o in offices if o["name"] not in existing]
    if count != "all":
        todo = todo[:int(count)]

    approx = {}   # the teammates' town-level coordinates, used only when the street address cannot be geocoded
    fl_json = ROOT / "backend" / "florida_facilities.json"
    if fl_json.exists():
        import json
        approx = {x["name"]: (x["lat"], x["lon"]) for x in json.loads(fl_json.read_text())}

    def geo(o):
        try:
            return o, geocode_address(o["address"]), None
        except Exception as e:
            if o["name"] in approx:
                lat, lon = approx[o["name"]]
                return o, (lat, lon, o["address"] + " (approximate location: street address not found by the Census geocoder)"), None
            return o, None, e

    added = 0
    with ThreadPoolExecutor(max_workers=6) as pool:   # the Census geocoder is a plain HTTPS call: geocode in parallel, write sequentially
        for o, res, err in pool.map(geo, todo):
            if err or not res:
                print(f"  skipped {o['name']}: {err or 'no geocoder match'}")
                continue
            lat, lon, matched = res
            s.add({"id": _office_id(o["name"]), "name": o["name"], "address": matched, "latitude": lat, "longitude": lon,
                   "opening_time": "08:00", "closing_time": "16:30", "telework_available": True, "essential_staff_required": True,
                   "transportation_support_needed": False, "accessibility_support_needed": False})
            added += 1
            print(f"  added {o['name']} ({lat:.4f}, {lon:.4f})")
    print(f"Done: {added} offices added to {DB_PATH}")
    return added


def load_facilities():
    """Geocoded offices with agency + state (auto-seeds the database from the SQL files the first time it is empty)."""
    s = store()
    rows = s.all(include_permanently_closed=False)
    if not rows:
        print("Facility database is empty: loading offices from the SQL files (geocoding)...", flush=True)
        seed("all")
        rows = s.all(include_permanently_closed=False)
    meta = sql_offices()
    out = []
    for f in rows[:LIMIT]:
        m = meta.get(f["name"], {})
        addr = f["address"]
        state = m.get("state") or (STATE_RE.search(addr).group(1) if STATE_RE.search(addr) else None)
        if not state:
            continue
        out.append({"id": f["id"], "name": f["name"], "address": addr, "lat": f["latitude"], "lon": f["longitude"],
                    "agency": m.get("agency") or "USDA", "state": state})
    return out


# ---------- hazard text helpers ----------
def hazard_type(event):
    e = (event or "").lower()
    for words, t in [(("tornado",), "tornado"), (("hurricane", "tropical", "storm surge"), "hurricane"),
                     (("flood",), "flood"), (("fire", "red flag"), "fire"), (("heat",), "heat"),
                     (("winter", "ice", "snow", "blizzard", "freez", "cold"), "winter"), (("wind",), "wind")]:
        if any(w in e for w in words):
            return t
    return "default"


def readable(ts):
    """'2026-10-11T06:00:00-04:00' -> 'Sun 6:00 AM' (in the alert's own time zone)."""
    try:
        return datetime.fromisoformat(ts).strftime("%a %I:%M %p").replace(" 0", " ")
    except Exception:
        return ts or None


def _ring(geometry, max_points=80):
    """Outer ring of the biggest polygon, as [[lon, lat], ...], simplified (the frontend only uses it for map bounds)."""
    if not geometry:
        return None
    try:
        from shapely.geometry import shape
        g = shape(geometry)
        polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
        poly = max(polys, key=lambda p: p.area).simplify(0.02)
        pts = [[round(x, 4), round(y, 4)] for x, y in poly.exterior.coords]
        return pts if len(pts) <= max_points else pts[:: len(pts) // max_points + 1]
    except Exception:
        return None


# ---------- pictures: one weather picture per office, without stampeding the sources ----------
def _failed_picture(as_dt, err):
    now = datetime.now(timezone.utc)
    try:
        mode = nws_client.classify_mode(as_dt, now)
    except Exception:
        mode = "archive"
    return {"mode": mode, "scenario": None, "as_of": as_dt.isoformat(), "retrieved_at": now.isoformat(), "alerts": [], "weather": None,
            "sources": [], "errors": [f"Alert query failed: {err}"], "disclaimer": None,
            "data_source": {"name": "unavailable", "cached": False, "cache_retrieved_at": None, "retrieved_at": now.isoformat(), "notes": []}}


def pictures_for(facilities, as_dt, workers=WORKERS):
    """{facility_id: picture} for the same as-of moment. The shared fetches (IEM zone shapes for that minute, the NWS
    area alerts per state, the ASOS station list per state) are warmed ONCE before the parallel pass, so a cold
    snapshot never fires dozens of identical requests."""
    now = datetime.now(timezone.utc)
    mode = nws_client.classify_mode(as_dt, now)
    engine_facs = {o["id"]: {"id": o["id"], "name": o["name"], "latitude": o["lat"], "longitude": o["lon"], "state": o["state"]} for o in facilities}

    def one(o):
        try:
            return o["id"], hazards.picture_at(engine_facs[o["id"]], as_dt)
        except Exception as e:
            return o["id"], _failed_picture(as_dt, e)

    if mode == "archive":
        try:
            iem_client._zone_features(iem_client._minute(as_dt))   # one shared county/zone fetch for this minute
        except Exception:
            pass                                                    # each facility reports its own error below
    by_state = {}
    for o in facilities:
        by_state.setdefault(o["state"], []).append(o)
    with ThreadPoolExecutor(max_workers=max(1, len(by_state))) as pool:   # first office of each state warms that state's shared caches
        out = dict(pool.map(lambda fs: one(fs[0]), by_state.values()))
    rest = [o for fs in by_state.values() for o in fs[1:]]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        out.update(pool.map(one, rest))
    return out


# ---------- one office -> the frontend's facility JSON ----------
def _alert_failed(picture):
    return any("alert" in e.lower() for e in picture["errors"])


def build_facility(o, picture, as_dt):
    fac, imp, rd, det = ea.evaluate_nolog(o, picture)
    failed = _alert_failed(picture)
    m, labels = imp["metrics"], ea.POSTURE_LABELS
    posture = det["posture"]
    cover = sorted(imp["facility_alerts"], key=lambda a: -a["priority_score"])
    eid = rec = None
    ai = ea.load_ai(o["id"], as_dt)
    if not failed:
        eid, rec = ea.log_evaluation(fac, picture, imp, rd, det)
    if ai:   # stored AI second opinion / email for exactly this office and moment (see backend/decide.py)
        eid, rec = ai.get("evaluation_id") or eid, ai.get("record") or rec
    engine_payload = ea.slim(fac, picture, imp, rd, det, eid, rec,
                             {k: ai[k] for k in ("second_opinion", "manager_decision", "notifications") if ai and k in ai})
    if failed:
        engine_payload["data_failed"] = True
    else:   # how each of the four USDA sectors would handle this same moment (backend/sector_views.py)
        try:
            from backend.sector_views import views_for
            engine_payload["sector_views"] = views_for(o, picture)
        except Exception as e:
            print("sector views failed:", e)

    obs = (picture.get("weather") or {}).get("observation") or {}
    bullets = []
    if failed:
        bullets.append("Weather alert check failed: " + "; ".join(e for e in picture["errors"] if "alert" in e.lower())[:200])
        bullets.append("No recommendation is shown because the alert data could not be retrieved.")
    else:
        bullets += [a.get("headline") or a["event"] for a in cover[:2]] or ["No NWS alert covers this office at this time."]
        if obs.get("conditions") or obs.get("temperature") is not None:
            t = obs.get("temperature")
            bullets.append("Observed: " + (obs.get("conditions") or "conditions n/a") + (f", {t * 9 / 5 + 32:.0f}°F" if isinstance(t, (int, float)) else ""))
        if not cover and m["high_commute_risk"] + m["elevated_commute_risk"]:
            bullets.append(f"{m['high_commute_risk'] + m['elevated_commute_risk']} of {m['workforce']} employees live or commute inside an active alert area (synthetic staff).")
        bullets.append(f"Recommendation: {labels[posture]} (rule engine)")
        if det["immediate_actions"]:
            bullets.append(det["immediate_actions"][0])
        other = len(picture["alerts"]) - len(cover)
        if other > 0:
            bullets.append(f"{other} other nearby alert(s) do not cover this office.")
    for e in picture["errors"]:
        if not failed:
            bullets.append("Data note: " + e)

    top = cover[0] if cover else None
    alert = ({"type": hazard_type(top["event"]), "title": top["event"], "area": (top.get("areaDesc") or "")[:80],
              "expires": readable(top.get("expires")) or "end time not in archive",
              "source": top.get("sender") or "National Weather Service"} if top and not failed else None)
    return {
        "id": o["id"], "name": o["name"],
        "short": o["name"].replace(" Service Center", "").replace(" County FSA", " FSA"),
        "lat": o["lat"], "lon": o["lon"], "address": o["address"],
        "state": o["state"], "agency": o["agency"], "sector": fac["sector"], "timezone": fac["timezone"],
        "status": "unknown" if failed else ea.STATUS_OF[posture],
        "total": None if failed else m["workforce"], "affected": None if failed else m["high_commute_risk"] + m["elevated_commute_risk"],
        "bullets": bullets, "alert": alert, "alertPolygon": _ring(top.get("geometry")) if top and not failed else None,
        "alerts": [{"id": a["id"], "event": a["event"], "headline": a.get("headline"), "severity": a.get("severity"),
                    "urgency": a.get("urgency"), "certainty": a.get("certainty"), "level": a["base_level"], "sender": a.get("sender"),
                    "sent": a.get("sent"), "effective": a.get("effective"), "onset": a.get("onset"), "expires": a.get("expires"),
                    "affected_areas": a.get("areaDesc"), "covers_facility": a["id"] in {c["id"] for c in cover}} for a in picture["alerts"]],
        "weatherCapturedAt": picture["retrieved_at"], "dataSources": picture["sources"],
        "dataSource": picture["data_source"], "errors": picture["errors"],
        "opinion": None, "reasoning": None, "email": None,
        "engine": engine_payload,
    }


_chain = {"seq": None, "ok": True}


def _chain_ok():
    """verify_chain() re-hashes the whole decision log; only redo it when events were added."""
    try:
        with audit_store._conn() as c:
            seq = c.execute("SELECT COALESCE(MAX(seq), 0) FROM events").fetchone()[0]
        if _chain["seq"] != seq:
            _chain.update(seq=seq, ok=audit_store.verify_chain()[0])
        return _chain["ok"]
    except Exception:
        return False


def build_snapshot(as_of=None):
    """Snapshot for the as-of moment: `as_of` may be an ISO string, a datetime or None (= clock default: CLEARSIGHT_NOW or now).
    Raises closure.clock.ClockError for unusable moments."""
    as_dt, clock_info = clock.resolve_as_of(as_of)
    t0 = time.time()
    offices = load_facilities()
    pictures = pictures_for(offices, as_dt)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        facs = list(pool.map(lambda o: build_facility(o, pictures[o["id"]], as_dt), offices))

    msgs = {}
    for f in facs:
        for e in f["errors"]:
            msgs[e] = msgs.get(e, 0) + 1
    errors = [f"{m} (x{n} offices)" if n > 1 else m for m, n in msgs.items()]
    ds = next((p["data_source"] for p in pictures.values()), {"name": "unavailable", "cached": False, "notes": []})
    mode = next((p["mode"] for p in pictures.values()), clock_info.get("mode"))
    disclaimer = next((p["disclaimer"] for p in pictures.values() if p.get("disclaimer")), None)
    cached_all = bool(pictures) and all(p["data_source"].get("cached") for p in pictures.values())
    ds = {**ds, "cached": cached_all, "cache_retrieved_at": min((p["data_source"].get("cache_retrieved_at") or "~") for p in pictures.values()) if cached_all else None}

    covering = [f for f in facs if f["alert"] and f["status"] != "unknown"]
    worst = max(covering, key=lambda f: max((a["level"] for a in f["alerts"] if a["covers_facility"]), default=0), default=None)
    ok = _chain_ok()
    return {
        "mode": mode, "as_of": as_dt.isoformat(), "generated_at": datetime.now(timezone.utc).isoformat(),
        "clock": {"requested": clock_info.get("requested"), "source": clock_info.get("source"), "real_now": clock_info.get("real_now")},
        "data_source": ds, "disclaimer": disclaimer, "errors": errors, "build_seconds": round(time.time() - t0, 1),
        "postures": ea.POSTURE_LABELS, "chain_verified": ok,
        "alert": worst["alert"] if worst else {"type": "default", "title": "No active warnings", "area": "Monitored offices",
                                               "expires": "—", "source": "National Weather Service"},
        "facilities": facs, "employees": [],
    }


if __name__ == "__main__":
    if "--seed" in sys.argv:
        arg = sys.argv[sys.argv.index("--seed") + 1] if len(sys.argv) > sys.argv.index("--seed") + 1 else "all"
        seed("all" if arg == "all" else int(arg))
    else:
        import json
        asof = sys.argv[sys.argv.index("--asof") + 1] if "--asof" in sys.argv else None
        snap = build_snapshot(asof)
        if "--json" in sys.argv:
            print(json.dumps(snap, indent=2, default=str))
        else:
            print(f"Mode {snap['mode']} as of {snap['as_of']} ({snap['build_seconds']}s) | alert: {snap['alert']['title']}")
            for e in snap["errors"]:
                print("  ERROR:", e)
            for f in snap["facilities"]:
                print(f"- [{f['state']}] {f['name']}: {f['status']} | {f['bullets'][0]}")
