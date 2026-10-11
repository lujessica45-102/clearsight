"""How each of the four USDA sectors in closure/sectors.py would handle the same moment at the same office.

Runs the rule engine once per sector on the same weather picture and staff, changing only the sector (its thresholds
and playbook). Called by backend/connect.py for every office, so the Second opinion page's 2x2 boxes stay live.
"""
from backend import engine_adapter as ea
from closure import engine, hazards, roads as roads_mod
from closure import impact as impact_mod
from closure.sectors import SECTORS, POSTURE_LABELS

ORDER = ["headquarters", "research_lab", "field_office", "service_center"]   # chain of command, highest first


def views_for(o, picture):
    emps = ea.synthetic_employees(o)
    as_of = hazards.parse_ts(picture["as_of"])
    out = []
    for sec in ORDER:
        fac = {**ea.to_engine_facility(o, emps), "sector": sec}
        win = engine.operating_window(fac, as_of)
        imp = impact_mod.analyze_employees(fac, emps, picture["alerts"], win["window_start"], win["window_end"])
        det = engine.evaluate(fac, picture, imp, roads_mod.road_conditions(fac, picture["mode"]), as_of)
        b = next((r for r in det["rules"] if r["id"] == det["binding_rule"]), None)
        m = imp["metrics"]
        out.append({
            "sector": sec, "label": SECTORS[sec]["label"], "rationale": SECTORS[sec]["rationale"], "params": SECTORS[sec]["params"],
            "posture": det["posture"], "posture_label": POSTURE_LABELS[det["posture"]],
            "action": SECTORS[sec]["playbook"][det["posture"]], "notes": det["sector_notes"],
            "binding": b and {k: b[k] for k in ("id", "name", "value", "threshold", "comparator")},
            "workforce": m["workforce"], "essential": m["essential_total"], "telework": m["telework_eligible_total"],
            "exposed": m["high_commute_risk"] + m["elevated_commute_risk"], "high_pct": m["high_pct"],
        })
    return out
