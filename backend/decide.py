"""Runs Rithvika's decision engine (closure/) on Jessica's Florida offices for the Hurricane Michael replay
and saves the results for the website. Her code is used unchanged; this file only adapts the facility format.

  python -m backend.decide           rule engine + AI second opinion + draft email (needs the AWS key in .env)
  python -m backend.decide --no-ai   rule engine only

Writes frontend/src/decisions.json. Every step is also written to her tamper-evident decision log.
"""
import json, os, random, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "src" / "decisions.json"
SCENARIO, SNAPSHOT = "michael_2018", 2          # Wed Oct 10 2018, 4:00 AM CDT: the morning closure call
FIRST_CALM = 4                                  # AI also runs on the first 4 offices with no warning (rule engine runs on all)


def load_env():
    """Read KEY=VALUE lines from .env into the environment (values are never printed)."""
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
(ROOT / "closure" / "data").mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT))

from closure import hazards, engine, store, roads, workflow, synthetic   # noqa: E402  teammate's code
from closure import impact as impact_mod                                 # noqa: E402
from closure.sectors import POSTURE_LABELS                               # noqa: E402


# ---------- adapter: Jessica's office record -> the facility format the engine expects ----------
def to_engine_facility(o, emps, sector="service_center"):
    return {
        "id": o["id"], "name": o["name"], "sector": sector,       # NRCS/FSA offices are service centers
        "latitude": o["lat"], "longitude": o["lon"],
        "timezone": "America/Chicago" if o["lon"] <= -85.0 else "America/New_York",   # Panhandle west of the Apalachicola is Central
        "opening_time": "08:00", "closing_time": "16:30", "state": "FL",
        "headcount": len(emps), "synthetic_employees": True,
        "telework_available": any(e["telework_eligible"] for e in emps),
        "essential_staff_required": any(e["essential"] for e in emps),
        "accessibility_support_needed": any(e["accessibility_need"] for e in emps),
    }


def synthetic_employees(o, sector="service_center"):
    """Made-up staff, generated the same way as closure/synthetic.py (fixed seed, her role and rate tables)."""
    rng = random.Random(f"clearsight-{o['id']}")
    n = rng.randint(12, 22)
    town = o["address"].split(",")[-2].strip()
    ess, tw = synthetic._ESSENTIAL_RATE[sector], synthetic._TELEWORK_RATE[sector]
    out = []
    for i in range(n):
        spread_km = rng.choice([4, 8, 15, 25])                              # rural commutes: some local, some long
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


def evaluate(o, picture):
    """Same steps as closure/workflow.evaluate, with our facility instead of her synthetic one."""
    emps = synthetic_employees(o)
    fac = to_engine_facility(o, emps)
    as_of = hazards.parse_ts(picture["as_of"])
    win = engine.operating_window(fac, as_of)
    imp = impact_mod.analyze_employees(fac, emps, picture["alerts"], win["window_start"], win["window_end"])
    rd = roads.road_conditions(fac, "replay")
    det = engine.evaluate(fac, picture, imp, rd, as_of)
    eid = store.new_evaluation_id()
    rec = store.append(eid, fac["id"], "evaluation", {"facility": fac, "picture": picture, "impact": imp, "roads": rd, "deterministic": det})
    return workflow.Ctx(eid, fac, picture, imp, rd, det), rec


def run_ai(ctx):
    from closure import agents        # imported here so --no-ai works without strands/AWS
    out = {}
    so = agents.run_second_opinion(ctx)
    so["record"] = store.append(ctx.evaluation_id, ctx.facility["id"], "second_opinion", so)
    out["second_opinion"] = so
    # Her design needs a human decision before an email can be drafted. For the saved demo we record the
    # manager accepting the rule engine's recommendation, clearly labelled as a demo stand-in.
    payload, rec = workflow.record_decision(ctx.evaluation_id, ctx.deterministic["posture"], None,
                                            "Demo stand-in: facility manager accepted the recommendation")
    out["manager_decision"] = {**payload, "record": rec}
    nt = agents.run_notifications(ctx, payload)
    if nt.get("status") == "ok":
        nt["record"] = store.append(ctx.evaluation_id, ctx.facility["id"], "notification_package", nt)
    out["notifications"] = nt
    return out


def slim(ctx, rec, ai):
    det = dict(ctx.deterministic)
    det.pop("evidence", None)
    people = [{k: p[k] for k in ("id", "home_community", "home_lat", "home_lon", "role_category", "essential", "telework_eligible",
                                 "accessibility_need", "commute_risk", "worst_event", "commute_km_straight_line")} for p in ctx.impact["people"]]
    covers = {a["id"] for a in ctx.impact["facility_alerts"]}
    alerts = [{"id": a["id"], "event": a["event"], "level": a["base_level"], "sender": a.get("sender"), "issued": a["sent"],
               "covers_facility": a["id"] in covers, "source_url": a.get("source_url")} for a in ctx.picture["alerts"]]
    return {"facility_id": ctx.facility["id"], "evaluation_id": ctx.evaluation_id, "record": rec,
            "engine_facility": ctx.facility, "deterministic": det, "metrics": ctx.impact["metrics"],
            "by_community": ctx.impact["by_community"], "impact_note": ctx.impact["method_note"],
            "alerts": alerts, "roads": ctx.roads, "employees": people, **ai}


def main():
    use_ai = "--no-ai" not in sys.argv
    offices = json.load(open(ROOT / "backend" / "florida_facilities.json"))
    picture = hazards.replay_picture(SCENARIO, SNAPSHOT)
    results, calm = {}, 0
    for o in offices:
        t0 = time.time()
        ctx, rec = evaluate(o, picture)
        warned = bool(ctx.impact["facility_alerts"])
        want_ai = use_ai and (warned or calm < FIRST_CALM)
        if not warned:
            calm += 1
        ai = run_ai(ctx) if want_ai else {}
        results[o["id"]] = slim(ctx, rec, ai)
        so = ai.get("second_opinion", {})
        print(f"{o['name']:30} {ctx.deterministic['posture']:16} "
              f"AI: {so.get('status', '-'):6} {(so.get('final_ai_recommendation') or {}).get('posture', ''):16} "
              f"email: {ai.get('notifications', {}).get('status', '-'):6} ({time.time() - t0:.0f}s)")
        for k in ("second_opinion", "notifications"):
            if ai.get(k, {}).get("status") == "failed":
                print("   ", k, "failed:", ai[k].get("error"))
    ok, bad = store.verify_chain()
    snap = picture["scenario"]
    json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "ai": use_ai, "chain_verified": ok,
               "scenario": {"id": SCENARIO, "snapshot": SNAPSHOT, "as_of": picture["as_of"], "label": snap.get("label"), "title": snap.get("title")},
               "postures": POSTURE_LABELS, "facilities": results},
              open(OUT, "w"), indent=1, default=str)
    print(f"\nSaved {len(results)} facilities to {OUT.relative_to(ROOT)}  (decision log chain verified: {ok})")


if __name__ == "__main__":
    main()
