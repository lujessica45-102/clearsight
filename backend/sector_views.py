"""How each of the four USDA sectors in closure/sectors.py would handle the same storm at the same office.

Runs Rithvika's rule engine once per sector (same hazards, same location; staff mix uses that sector's
essential/telework rates). No AI, no AWS key needed.   python -m backend.sector_views
Writes frontend/src/sectorDecisions.json
"""
import json
from backend.decide import ROOT, SCENARIO, SNAPSHOT, synthetic_employees, to_engine_facility
from closure import hazards, engine, roads
from closure import impact as impact_mod
from closure.sectors import SECTORS, POSTURE_LABELS

ORDER = ["headquarters", "research_lab", "field_office", "service_center"]   # chain of command, highest first


def main():
    offices = json.load(open(ROOT / "backend" / "florida_facilities.json"))
    picture = hazards.replay_picture(SCENARIO, SNAPSHOT)
    as_of = hazards.parse_ts(picture["as_of"])
    out = {}
    for o in offices:
        views = []
        for sec in ORDER:
            emps = synthetic_employees(o, sec)
            fac = to_engine_facility(o, emps, sec)
            win = engine.operating_window(fac, as_of)
            imp = impact_mod.analyze_employees(fac, emps, picture["alerts"], win["window_start"], win["window_end"])
            det = engine.evaluate(fac, picture, imp, roads.road_conditions(fac, "replay"), as_of)
            b = next((r for r in det["rules"] if r["id"] == det["binding_rule"]), None)
            m = imp["metrics"]
            views.append({
                "sector": sec, "label": SECTORS[sec]["label"], "description": SECTORS[sec]["description"],
                "rationale": SECTORS[sec]["rationale"], "params": SECTORS[sec]["params"],
                "posture": det["posture"], "posture_label": POSTURE_LABELS[det["posture"]],
                "action": SECTORS[sec]["playbook"][det["posture"]], "notes": det["sector_notes"],
                "binding": b and {k: b[k] for k in ("id", "name", "value", "threshold", "comparator")},
                "workforce": m["workforce"], "essential": m["essential_total"], "telework": m["telework_eligible_total"],
                "exposed": m["high_commute_risk"] + m["elevated_commute_risk"], "high_pct": m["high_pct"],
            })
        out[o["id"]] = views
        print(f"{o['name']:30}", " | ".join(f"{v['sector'][:6]}: {v['posture']}" for v in views))
    json.dump(out, open(ROOT / "frontend" / "src" / "sectorDecisions.json", "w"), indent=1)


if __name__ == "__main__":
    main()
