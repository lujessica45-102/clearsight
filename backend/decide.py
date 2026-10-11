"""Runs the decision engine (closure/) and the AI agents on the offices for ANY moment, and saves the AI results.

Nothing is hardcoded: weather is queried for the as-of moment (live NWS / NWS alert history / IEM archive).

  python -m backend.decide --asof 2018-10-10T09:00:00Z --state FL        rule engine + AI second opinion + draft email
  python -m backend.decide --moment <id>                                  moment from presets/moments.json (asof + facility_ids)
  python -m backend.decide --asof ISO --facilities id1,id2 [--no-ai]
  python -m backend.decide --asof ISO --all

AI needs AWS credentials in the environment (or ROOT/.env). Each facility that got AI analysis is written to
backend/ai_results/<facility_id>@<YYYYmmddTHHMMZ>.json; the /api/current snapshot merges these for exactly that
office and moment. Every step is also written to the tamper-evident decision log (closure/store.py).
"""
import json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIRST_CALM = 4          # AI also runs on the first 4 offices with no covering alert (rule engine runs on all selected)


def load_env():
    """Read KEY=VALUE lines from .env into the environment (values are never printed)."""
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
sys.path.insert(0, str(ROOT))

from closure import clock, store, workflow                       # noqa: E402
from backend import connect, engine_adapter as ea                 # noqa: E402


def moments():
    p = ROOT / "presets" / "moments.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text())
    return d["moments"] if isinstance(d, dict) else d


def evaluate(o, picture):
    """Rule engine for an office record (closure.workflow.evaluate_picture only knows closure's own fictional facilities).
    Writes the full audit record, including alert geometry, because the AI agents work from this evaluation."""
    fac, imp, rd, det = ea.evaluate_nolog(o, picture)
    eid = store.new_evaluation_id()
    rec = store.append(eid, fac["id"], "evaluation", {"facility": fac, "picture": picture, "impact": imp, "roads": rd, "deterministic": det})
    return workflow.Ctx(eid, fac, picture, imp, rd, det), rec


def run_ai(ctx):
    from closure import agents        # imported here so --no-ai works without strands/AWS
    out = {}
    so = agents.run_second_opinion(ctx)
    so["record"] = store.append(ctx.evaluation_id, ctx.facility["id"], "second_opinion", so)
    out["second_opinion"] = so
    # The design needs a human decision before an email can be drafted. For the saved demo we record the manager
    # accepting the rule engine's recommendation, clearly labelled as a demo stand-in.
    payload, rec = workflow.record_decision(ctx.evaluation_id, ctx.deterministic["posture"], None,
                                            "Demo stand-in: facility manager accepted the recommendation")
    out["manager_decision"] = {**payload, "record": rec}
    nt = agents.run_notifications(ctx, payload)
    if nt.get("status") == "ok":
        nt["record"] = store.append(ctx.evaluation_id, ctx.facility["id"], "notification_package", nt)
    out["notifications"] = nt
    return out


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv and len(sys.argv) > sys.argv.index(name) + 1 else None


def main():
    use_ai = "--no-ai" not in sys.argv
    asof, ids = arg("--asof"), None
    if arg("--moment"):
        m = next((m for m in moments() if m.get("id") == arg("--moment")), None)
        if not m:
            sys.exit(f"Unknown moment {arg('--moment')!r}. Known: {[m.get('id') for m in moments()]}")
        asof, ids = m["asof"], m.get("facility_ids") or None
    if not asof:
        sys.exit("Give --asof <ISO-8601 UTC> or --moment <id>. (A moment is required: nothing is hardcoded.)")
    if arg("--facilities"):
        ids = arg("--facilities").split(",")
    as_dt, _ = clock.resolve_as_of(asof)
    offices = connect.load_facilities()
    if ids:
        offices = [o for o in offices if o["id"] in ids]
    elif arg("--state"):
        offices = [o for o in offices if o["state"] == arg("--state").upper()]
    elif "--all" not in sys.argv:
        sys.exit("Choose offices: --facilities id,id | --state CA|FL | --all (or --moment with facility_ids).")
    if not offices:
        sys.exit("No matching offices.")

    print(f"As of {as_dt.isoformat()}: querying {len(offices)} offices ...", flush=True)
    pictures = connect.pictures_for(offices, as_dt)
    calm, written = 0, 0
    for o in offices:
        t0 = time.time()
        picture = pictures[o["id"]]
        if any("alert" in e.lower() for e in picture["errors"]):
            print(f"{o['name']:34} SKIPPED: alert data failed: {picture['errors'][:1]}")
            continue
        ctx, rec = evaluate(o, picture)
        warned = bool(ctx.impact["facility_alerts"])
        want_ai = use_ai and (warned or calm < FIRST_CALM)
        if not warned:
            calm += 1
        ai = run_ai(ctx) if want_ai else {}
        so = ai.get("second_opinion", {})
        print(f"{o['name']:34} {ctx.deterministic['posture']:16} "
              f"AI: {so.get('status', '-'):6} {(so.get('final_ai_recommendation') or {}).get('posture', ''):16} "
              f"email: {ai.get('notifications', {}).get('status', '-'):6} ({time.time() - t0:.0f}s)")
        for k in ("second_opinion", "notifications"):
            if ai.get(k, {}).get("status") == "failed":
                print("   ", k, "failed:", ai[k].get("error"))
        if ai:
            ea.save_ai(o["id"], as_dt, {"facility_id": o["id"], "as_of": as_dt.isoformat(), "evaluation_id": ctx.evaluation_id, "record": rec,
                                        "saved_at": datetime.now(timezone.utc).isoformat(), **ai})
            written += 1
    ok, _ = store.verify_chain()
    print(f"\nWrote {written} AI result file(s) to backend/ai_results/  (decision log chain verified: {ok})")


if __name__ == "__main__":
    main()
