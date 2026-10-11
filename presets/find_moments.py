#!/usr/bin/env python3
"""Find, verify and bookmark demo moments for the ClearSight time control.

A moment is a BOOKMARK: a place (facility ids) and a timestamp, like a calendar entry. No weather is stored in
presets/moments.json; whenever a moment is selected the app queries NWS / the IEM archive live for it.

  scan    rank "decision mornings" (04:00 local) by the worst hazard covering a facility town, from the IEM archive
  verify  fetch the full picture for real (closure.hazards.picture_at) and say whether alerts cover the facility
  add     verify, then append a bookmark to presets/moments.json

Run from the repo root:
  python presets/find_moments.py scan --state CA --from 2018-01-01 --to 2025-12-31 --hazard fire --top 10
  python presets/find_moments.py verify --asof 2018-11-08T12:00:00Z --facility "Oroville Service Center"
  python presets/find_moments.py add --asof 2018-11-08T12:00:00Z --region CA --hazard fire \\
        --facility "Oroville Service Center,Butte County FSA" --label "California · Red Flag Warning, Butte County (Nov 2018)"

Coordinates come from the US Census geocoder (the team's geocode_address) and are cached in ~/.clearsight, never
stored in the repo.  Known limits: the by-point IEM endpoint matches on issue date and lists Fire Weather WATCHES with an
end time before their begin time (IEM stores the upgrade time), so `scan` cannot rank watches; `verify` (which uses the
valid-at-the-minute endpoint) is the arbiter of what is really in force at a given moment.
"""
import argparse
import json
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from parser import http_cache                                          # noqa: E402  response cache (real responses only)
from parser.facility_cleaning.facilities import geocode_address         # noqa: E402  team's US Census geocoder
from closure import hazards, clock                                      # noqa: E402

SQL_FILES = [ROOT / "parser" / "facilities.sql", ROOT / "presets" / "facilities.sql"]   # Florida list + California presets
MOMENTS = ROOT / "presets" / "moments.json"
BYPOINT = "https://mesonet.agron.iastate.edu/json/vtec_events_bypoint.py"
DATA_DIR = Path.home() / ".clearsight"
GEO_CACHE = DATA_DIR / "presets_geocode.json"
DECISION_HOUR = 4          # local hour of the realistic "morning closure call"
OPENING_HOUR = 8           # offices open 08:00 (matches backend/connect.py seed())
HAZARD_CLASSES = {"fire": {"fire"}, "tropical": {"tropical", "surge"}, "flood": {"flood"}, "winter": {"winter", "cold"},
                  "wind": {"wind"}, "tornado": {"tornado", "convective"}, "any": None}
STATS = Counter()


# ---------------------------------------------------------------- facilities (from the SQL files, geocoded on demand)
def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")        # same slug as backend/connect.py seed()


def load_facilities():
    out = {}
    for path in SQL_FILES:
        if not path.exists():
            continue
        text = path.read_text()
        for n, agency, addr in re.findall(r"\(\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)'", text):
            n, agency, addr = (x.replace("''", "'") for x in (n, agency, addr))
            m = re.search(r",\s*([^,]+),\s*([A-Z]{2})\s+\d{5}", addr)
            if not m:
                continue
            fid = slug(n)
            out.setdefault(fid, {"id": fid, "name": n, "agency": agency, "address": addr, "town": m.group(1).strip(),
                                 "state": m.group(2)})
    return out


def _geo_cache():
    try:
        return json.loads(GEO_CACHE.read_text())
    except Exception:
        return {}


def locate(fac):
    """Add latitude/longitude/timezone to a facility dict (US Census geocoder, cached under ~/.clearsight)."""
    cache = _geo_cache()
    if fac["address"] not in cache:
        lat, lon, matched = geocode_address(fac["address"])
        cache[fac["address"]] = [lat, lon, matched]
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        GEO_CACHE.write_text(json.dumps(cache, indent=1))
    lat, lon, matched = cache[fac["address"]]
    f = dict(fac, latitude=lat, longitude=lon, matched_address=matched)
    f["timezone"] = tz_for(f)
    return f


def tz_for(f):
    if f["state"] == "CA":
        return "America/Los_Angeles"
    if f["state"] == "FL":
        return "America/Chicago" if f["longitude"] <= -85.0 else "America/New_York"   # Panhandle west of the Apalachicola is Central
    return "America/Chicago"


def find(facs, query):
    q = query.strip().lower()
    if q in facs:
        return facs[q]
    hits = [f for f in facs.values() if q == f["name"].lower()] or [f for f in facs.values() if q in f["name"].lower() or q == f["id"]]
    if len(hits) != 1:
        raise SystemExit(f"Facility {query!r} matched {len(hits)} entries: {[h['name'] for h in hits][:6]}")
    return hits[0]


# ---------------------------------------------------------------- scan
def local_decision_utc(day, tzname):
    return datetime(day.year, day.month, day.day, DECISION_HOUR, 0, tzinfo=ZoneInfo(tzname)).astimezone(timezone.utc)


def _parse(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc) if s else None
    except ValueError:
        return None


def query_events(lat, lon, start, end):
    """IEM VTEC events issued between two dates covering the point; 4-year chunks (responses are small)."""
    events, d0 = [], start
    while d0 <= end:
        d1 = min(date(d0.year + 3, 12, 31), end)
        data, meta = http_cache.cached_get_json(BYPOINT, {"lon": round(lon, 4), "lat": round(lat, 4), "sdate": d0.isoformat(), "edate": (d1 + timedelta(days=1)).isoformat()},
                                                ttl_seconds=None, timeout=120)
        STATS["queries"] += 1
        STATS["cached"] += int(meta["cached"])
        events += data.get("events", [])
        d0 = d1 + timedelta(days=1)
    return events


def scan_town(fac, start, end, want):
    try:
        f = locate(fac)
    except Exception as e:                  # an address the Census geocoder cannot resolve: skip this town, keep scanning
        STATS["geocode_failed"] += 1
        print(f"  skipped {fac['town']}, {fac['state']} ({fac['name']}): {e}", file=sys.stderr)
        return []
    evs = query_events(f["latitude"], f["longitude"], start - timedelta(days=8), end)
    days = {}
    for e in evs:
        b, x = _parse(e.get("issue")), _parse(e.get("expire"))
        if not b or not x or x <= b:        # IEM stores the upgrade time as the end of a Watch: never in force on its own
            continue
        name = f"{e['ph_name']} {e['sig_name']}"
        cls, level = hazards.classify(name, None, None)
        if cls == "other" or (want and cls not in want):
            continue
        d = b.astimezone(ZoneInfo(f["timezone"])).date() - timedelta(days=1)
        for _ in range(12):                 # a warning rarely matters beyond ~10 days; keeps rows bounded
            d += timedelta(days=1)
            if d < start or d > end:
                continue
            t = local_decision_utc(d, f["timezone"])
            if b <= t < x:
                days.setdefault(d, {})[name] = (level, cls)
    rows = []
    for d, evmap in days.items():
        top = sorted(evmap.items(), key=lambda kv: -kv[1][0])
        rows.append({"date": d, "town": f["town"], "state": f["state"], "facility": f["name"], "asof": local_decision_utc(d, f["timezone"]),
                     "level": top[0][1][0], "cls": top[0][1][1], "n": len(top), "events": [k for k, _ in top[:3]]})
    return rows


def cmd_scan(a):
    facs = load_facilities()
    pool = [f for f in facs.values() if a.state == "ALL" or f["state"] == a.state]
    towns = {}
    for f in pool:                          # one representative facility per town
        towns.setdefault((f["state"], f["town"]), f)
    if a.towns:
        keys = [t.strip().lower() for t in a.towns.split(",")]
        towns = {k: v for k, v in towns.items() if any(q in k[1].lower() for q in keys)}
    want = HAZARD_CLASSES[a.hazard]
    start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    t0 = time.time()
    print(f"Scanning {len(towns)} towns, {start} to {end}, hazard={a.hazard}, decision time {DECISION_HOUR:02d}:00 local ...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=max(1, min(a.workers, 3))) as ex:
        results = list(ex.map(lambda f: scan_town(f, start, end, want), towns.values()))
    rows = sorted((r for rs in results for r in rs), key=lambda r: (-r["level"], -r["n"], r["date"]))
    shown = []
    for r in rows:                          # one row per event cluster: same hazard class within 3 days of a better row
        dup = next((s for s in shown if s["cls"] == r["cls"] and abs((s["date"] - r["date"]).days) <= 3 and (s["state"] == r["state"])), None)
        if dup:
            dup.setdefault("also", set()).add(r["town"])
            continue
        shown.append(r)
    shown.sort(key=lambda r: (-r["level"], -r["n"], -len(r.get("also", ())), r["date"]))   # ties: widest-reaching event first
    print(f"{'DATE (local)':12} {'AS-OF (UTC)':17} {'LVL':3} {'#':2} {'TOWN':18} {'FACILITY':32} TOP EVENTS")
    for r in shown[:a.top]:
        also = f"  (+{len(r['also'])} nearby towns)" if r.get("also") else ""
        print(f"{r['date']!s:12} {r['asof']:%Y-%m-%dT%H:%MZ} {r['level']:3} {r['n']:2} {r['town'][:18]:18} {r['facility'][:32]:32} {', '.join(r['events'])}{also}")
    print(f"\n{STATS['queries']} IEM queries ({STATS['cached']} from cache), {time.time() - t0:.1f}s, {len(towns)} towns, {sum(len(r) for r in results)} town-days matched", file=sys.stderr)


# ---------------------------------------------------------------- verify / add
def covers(a):
    return a.get("nws_says_covers_facility_point") is True or a.get("distance_km") == 0.0


def run_verify(fac, asof, hazard, quiet=False):
    f = locate(fac)
    pic = hazards.picture_at({"id": f["id"], "name": f["name"], "latitude": f["latitude"], "longitude": f["longitude"], "state": f["state"]}, asof)
    cov = [x for x in pic["alerts"] if covers(x)]
    want = HAZARD_CLASSES.get(hazard)
    if hazard == "none":
        ok = not any(x["base_level"] >= 2 for x in cov) and not pic["errors"]
        need = "no alert of level >= 2 covering the facility (calm control)"
    else:
        match = [x for x in cov if want is None or x["hazard_class"] in want]
        ok = bool(match) and not pic["errors"]
        need = f"at least one {hazard} alert covering the facility"
    if not quiet:
        print(f"\n{f['name']} ({f['town']}, {f['state']}; {f['latitude']:.3f},{f['longitude']:.3f}) @ {asof:%Y-%m-%d %H:%MZ}  mode={pic['mode']}  "
              f"cached={pic['data_source'].get('cached')}  alerts fetched={len(pic['alerts'])}  covering={len(cov)}")
        for x in pic["alerts"]:
            print(f"   {'COVERS ' if covers(x) else 'nearby '} L{x['base_level']} {x['hazard_class']:9} {x['event']:30} {x.get('distance_km')} km  issued={x.get('sent')}")
        for e in pic["errors"]:
            print("   ERROR:", e)
        print(f"   -> {'PASS' if ok else 'FAIL'}: need {need}")
    return ok, pic, f


def parse_asof(s):
    dt, _ = clock.resolve_as_of(s)
    return dt


def cmd_verify(a):
    facs, asof = load_facilities(), parse_asof(a.asof)
    results = [run_verify(find(facs, q), asof, a.hazard)[0] for q in a.facility.split(",")]
    sys.exit(0 if all(results) else 1)


def cmd_add(a):
    facs, asof = load_facilities(), parse_asof(a.asof)
    chosen = [find(facs, q) for q in a.facility.split(",")]
    states = {c["state"] for c in chosen}
    if states - {"FL", "CA"} or (a.region not in states):
        raise SystemExit("Moments cover FL and CA facilities only, and --region must match the facilities' state.")
    located = []
    for c in chosen:
        ok, _, f = run_verify(c, asof, a.hazard)
        if not ok:
            raise SystemExit(f"Not added: verification failed for {c['name']}.")
        located.append(f)
    local = asof.astimezone(ZoneInfo(located[0]["timezone"]))
    when = f"{local:%a %b %-d %Y %-I:%M %p %Z}"
    timing = (f"Decision time {when}, before the {OPENING_HOUR:02d}:00 opening, the realistic early-morning closure call."
              if local.hour < OPENING_HOUR else f"Decision time {when}, during operating hours.")
    doc = json.loads(MOMENTS.read_text()) if MOMENTS.exists() else {"moments": []}
    mid = a.id or f"{a.region.lower()}-{a.hazard}-{local:%Y%m%d}-{slug(located[0]['town'])}"
    if any(m["id"] == mid for m in doc["moments"]):
        if not a.replace:
            raise SystemExit(f"Moment {mid!r} already exists (use --replace).")
        doc["moments"] = [m for m in doc["moments"] if m["id"] != mid]
    doc["moments"].append({"id": mid, "label": a.label, "asof": asof.strftime("%Y-%m-%dT%H:%M:%SZ"), "region": a.region, "hazard": a.hazard,
                           "note": (a.note + " " if a.note else "") + timing, "facility_ids": [c["id"] for c in chosen],
                           "verified_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    doc["moments"].sort(key=lambda m: (m["region"], m["asof"]))
    doc["description"] = ("Bookmarks only: a place (facility ids) and a timestamp. No weather data is stored here; selecting a moment makes "
                          "the app query NWS / the IEM archive live for that time. Managed by presets/find_moments.py.")
    MOMENTS.write_text(json.dumps({"description": doc["description"], "moments": doc["moments"]}, indent=1, ensure_ascii=False) + "\n")
    print(f"Added {mid} -> {MOMENTS.relative_to(ROOT)}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="rank decision mornings by worst covering hazard")
    s.add_argument("--state", default="ALL", choices=["CA", "FL", "ALL"])
    s.add_argument("--from", dest="start", default="2018-01-01")
    s.add_argument("--to", dest="end", default=date.today().isoformat())
    s.add_argument("--top", type=int, default=10)
    s.add_argument("--hazard", default="any", choices=sorted(HAZARD_CLASSES))
    s.add_argument("--towns", help="comma-separated town name fragments to limit the scan")
    s.add_argument("--workers", type=int, default=2)
    s.set_defaults(fn=cmd_scan)
    v = sub.add_parser("verify", help="fetch the real picture and check coverage")
    v.add_argument("--asof", required=True)
    v.add_argument("--facility", required=True, help="name or id; comma-separated for several")
    v.add_argument("--hazard", default="any", choices=sorted(HAZARD_CLASSES) + ["none"])
    v.set_defaults(fn=cmd_verify)
    d = sub.add_parser("add", help="verify then append a bookmark to presets/moments.json")
    d.add_argument("--asof", required=True)
    d.add_argument("--label", required=True)
    d.add_argument("--region", required=True, choices=["CA", "FL"])
    d.add_argument("--hazard", required=True, choices=sorted(HAZARD_CLASSES) + ["none"])
    d.add_argument("--facility", required=True)
    d.add_argument("--note", default="")
    d.add_argument("--id")
    d.add_argument("--replace", action="store_true")
    d.set_defaults(fn=cmd_add)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
