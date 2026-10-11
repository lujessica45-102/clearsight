"""Orchestration: evaluate -> second opinion -> manager decision -> notifications, every step logged."""
from datetime import datetime, timezone

from . import clock, synthetic, hazards, impact as impact_mod, roads as roads_mod, engine, store
from .sectors import POSTURE_LABELS


class Ctx:
    def __init__(self, evaluation_id, facility, picture, impact, roads, deterministic):
        self.evaluation_id, self.facility, self.picture = evaluation_id, facility, picture
        self.impact, self.roads, self.deterministic = impact, roads, deterministic


def evaluate(facility_id, as_of=None):
    """Query real sources for the facility at the as-of moment (ISO string / datetime / None = clock default), then evaluate."""
    facility = synthetic.get_facility(facility_id)
    as_dt, clock_info = clock.resolve_as_of(as_of)
    picture = hazards.picture_at(facility, as_dt)
    picture["clock"] = clock_info
    return evaluate_picture(facility, picture)


def evaluate_picture(facility, picture):
    """Rule engine + impact + audit record for an already-retrieved picture (also used with SYNTHETIC pictures in tests)."""
    as_of = hazards.parse_ts(picture["as_of"])
    win = engine.operating_window(facility, as_of)
    imp = impact_mod.analyze_employees(facility, synthetic.employees_for(facility["id"]), picture["alerts"], win["window_start"], win["window_end"])
    rd = roads_mod.road_conditions(facility, picture["mode"])
    det = engine.evaluate(facility, picture, imp, rd, as_of)
    eid = store.new_evaluation_id()
    rec = store.append(eid, facility["id"], "evaluation", {"facility": facility, "picture": picture, "impact": imp, "roads": rd, "deterministic": det})
    return Ctx(eid, facility, picture, imp, rd, det), rec


def load(evaluation_id):
    ev = store.latest(evaluation_id, "evaluation")
    if not ev:
        raise KeyError(evaluation_id)
    p = ev["payload"]
    return Ctx(evaluation_id, p["facility"], p["picture"], p["impact"], p["roads"], p["deterministic"])


def view(ctx, record=None):
    """JSON for the dashboard (alert geometry, employee points, metrics, recommendation)."""
    pic = ctx.picture
    covers = {a["id"] for a in ctx.impact["facility_alerts"]}
    alerts = [{**{k: a[k] for k in ("id", "event", "headline", "severity", "urgency", "certainty", "sent", "effective", "onset", "expires",
                                    "hazard_class", "base_level", "priority_score", "geometry", "geometry_kind", "source", "source_url",
                                    "retrieved_at", "areaDesc", "travel_impacting", "cached")},
               "covers_facility": a["id"] in covers, "used_in_decision": a["id"] in set(ctx.impact["relevant_alert_ids"])}
              for a in pic["alerts"]]
    return {
        "evaluation_id": ctx.evaluation_id, "record": record, "mode": pic["mode"], "clock": pic.get("clock"), "data_source": pic.get("data_source"),
        "disclaimer": pic.get("disclaimer"), "as_of": pic["as_of"], "retrieved_at": pic["retrieved_at"], "errors": pic["errors"],
        "facility": ctx.facility, "alerts": alerts, "weather": pic.get("weather"), "sources": pic["sources"],
        "employees": [{"lat": p["home_lat"], "lon": p["home_lon"], "risk": p["commute_risk"], "essential": p["essential"]} for p in ctx.impact["people"]],
        "metrics": ctx.impact["metrics"], "by_community": ctx.impact["by_community"], "impact_note": ctx.impact["method_note"],
        "roads": ctx.roads, "recommendation": ctx.deterministic,
    }


def record_decision(evaluation_id, selected_posture, reason, decided_by):
    ctx = load(evaluation_id)
    if selected_posture not in POSTURE_LABELS:
        raise ValueError("unknown posture")
    so = store.latest(evaluation_id, "second_opinion")
    ai = so["payload"].get("final_ai_recommendation", {}).get("posture") if so else None
    det = ctx.deterministic["posture"]
    is_override = selected_posture != det
    if is_override and not (reason or "").strip():
        raise ValueError("A reason is required when overriding the system recommendation.")
    payload = {"evaluation_id": evaluation_id, "selected_posture": selected_posture, "selected_label": POSTURE_LABELS[selected_posture],
               "deterministic_posture": det, "ai_posture": ai, "is_override": is_override,
               "differs_from_ai": ai is not None and selected_posture != ai, "reason": reason, "decided_by": decided_by,
               "decided_at": datetime.now(timezone.utc).isoformat(), "human_approved": True}
    return payload, store.append(evaluation_id, ctx.facility["id"], "manager_decision", payload)


def reconstruct(evaluation_id):
    """Everything needed to explain the decision afterwards, straight from the append-only log."""
    events = store.events_for(evaluation_id)
    if not events:
        raise KeyError(evaluation_id)
    by = {}
    for e in events:
        by.setdefault(e["event_type"], []).append({"event_id": e["event_id"], "created_at": e["created_at"], "sha256": e["sha256"], "payload": e["payload"]})
    ok, bad = store.verify_chain()
    ev = by["evaluation"][0]["payload"]
    return {"evaluation_id": evaluation_id, "chain_verified": ok, "first_bad_seq": bad,
            "timeline": [{"type": e["event_type"], "at": e["created_at"], "sha256": e["sha256"]} for e in events],
            "facility": ev["facility"], "weather_and_alerts": {"mode": ev["picture"]["mode"], "as_of": ev["picture"]["as_of"], "retrieved_at": ev["picture"]["retrieved_at"],
                                                              "alerts": [{k: a.get(k) for k in ("id", "event", "sent", "effective", "onset", "expires", "retrieved_at", "source", "source_url")} for a in ev["picture"]["alerts"]],
                                                              "errors": ev["picture"]["errors"], "clock": ev["picture"].get("clock"), "data_source": ev["picture"].get("data_source")},
            "employee_impact": ev["impact"]["metrics"], "roads": ev["roads"],
            "rule_thresholds": ev["deterministic"]["rules"], "initial_recommendation": {k: ev["deterministic"][k] for k in ("posture", "binding_rule", "justification", "confidence", "sensitivity", "evaluated_at", "as_of")},
            "second_opinion": by.get("second_opinion", [{}])[-1].get("payload"),
            "manager_decision": by.get("manager_decision", [{}])[-1].get("payload"),
            "notification_package": by.get("notification_package", [{}])[-1].get("payload")}
