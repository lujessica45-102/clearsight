"""Strands agents. Each agent has real tools over verified data and a Pydantic structured-output contract.

Hazard Intelligence and Employee Impact run in parallel as entry nodes of a Strands Graph; the Operational
Decision agent is a downstream node that receives both outputs. The Communications & Audit agent runs only
after a human manager has recorded a decision.
"""
import json
import time

from strands import Agent, tool
from strands.models import BedrockModel
from strands.multiagent import GraphBuilder

from . import config
from .schemas import HazardAssessment, EmployeeImpactAssessment, SecondOpinion, NotificationPlan
from .sectors import SECTORS, POSTURE_LABELS, POSTURE_RANK
from strands_evidence import EvidenceRecorder  # team's hook: records every tool call an agent makes


HINDSIGHT = "If mode is 'replay', reason ONLY from information available at as_of; never use hindsight or your own knowledge of what happened afterwards (landfall time, final intensity, damage). "


def _model(fast=False):
    return BedrockModel(model_id=config.BEDROCK_FAST_MODEL_ID if fast else config.BEDROCK_MODEL_ID, region_name=config.BEDROCK_REGION,
                        max_tokens=config.AGENT_MAX_TOKENS, temperature=0.2)


def _alert_view(a, covers_ids):
    return {"alert_id": a["id"], "event": a["event"], "severity": a["severity"], "urgency": a["urgency"],
            "certainty": a["certainty"], "status": a["status"], "headline": a["headline"],
            "hazard_class": a["hazard_class"], "system_level_1_to_5": a["base_level"], "travel_impacting": a["travel_impacting"],
            "covers_facility": a["id"] in covers_ids, "issued_sent": a["sent"], "effective": a["effective"],
            "onset": a["onset"], "expires": a["expires"], "area": (a["areaDesc"] or "")[:200],
            "geometry_kind": a["geometry_kind"], "source": a["source"], "retrieved_at": a["retrieved_at"]}


def recipient_groups(impact):
    p = impact["people"]
    defs = [
        ("essential_staff", "Essential personnel", lambda e: e["essential"], False),
        ("telework_eligible", "Non-essential, telework-eligible staff", lambda e: not e["essential"] and e["telework_eligible"], False),
        ("onsite_nonessential_no_telework", "Non-essential staff who cannot telework", lambda e: not e["essential"] and not e["telework_eligible"], False),
        ("commute_high_risk", "Employees with HIGH commute risk (overlay)", lambda e: e["commute_risk"] == "high", True),
        ("commute_elevated_risk", "Employees with ELEVATED commute risk (overlay)", lambda e: e["commute_risk"] == "elevated", True),
        ("accessibility_support", "Employees with accessibility needs (overlay)", lambda e: e["accessibility_need"], True),
        ("no_or_low_exposure", "Employees with no/low commute exposure (overlay)", lambda e: e["commute_risk"] in ("none", "low"), True),
    ]
    return [{"group_id": gid, "label": label, "count": sum(1 for e in p if f(e)), "overlay": ov,
             "employee_ids": [e["id"] for e in p if f(e)]} for gid, label, f, ov in defs]


def _hazard_agent(ctx, rec):
    covers = {a["id"] for a in ctx.impact["facility_alerts"]}

    @tool
    def get_facility_context() -> dict:
        """Facility identity, sector, location, operating hours/window and evaluation time."""
        f = ctx.facility
        return {"facility": {k: f[k] for k in ("id", "name", "sector", "latitude", "longitude", "state")},
                "operating_context": ctx.deterministic["operating_context"], "mode": ctx.picture["mode"],
                "as_of": ctx.picture["as_of"],
                "scenario": {k: (ctx.picture.get("scenario") or {}).get(k) for k in ("title", "label")} or None,
                "data_notice": ctx.picture.get("disclaimer")}

    @tool
    def get_active_alerts() -> list:
        """All verified NWS alerts relevant to this facility region (live) or archived alerts in effect at the replay time. Includes severity, urgency, certainty, times and whether each covers the facility."""
        return [_alert_view(a, covers) for a in ctx.picture["alerts"]]

    @tool
    def get_alert_text(alert_id: str) -> dict:
        """Full official NWS description and instruction text for one alert id."""
        for a in ctx.picture["alerts"]:
            if a["id"] == alert_id:
                return {"alert_id": alert_id, "description": (a["description"] or "")[:1800], "instruction": (a["instruction"] or "")[:800]}
        return {"error": f"unknown alert_id {alert_id}"}

    @tool
    def get_weather_observation_and_forecast() -> dict:
        """Latest observation (with observed time) and next forecast periods, if available."""
        return ctx.picture.get("weather") or {"note": "No observation/forecast available"}

    return Agent(
        name="hazard_intelligence", model=_model(fast=True), callback_handler=None, hooks=[rec],
        tools=[get_facility_context, get_active_alerts, get_alert_text, get_weather_observation_and_forecast],
        structured_output_model=HazardAssessment,
        system_prompt=(
            "You are the Hazard Intelligence Agent for a USDA facility emergency decision-support tool. " + HINDSIGHT +
            "ALWAYS call get_facility_context and get_active_alerts first; never assume alert data. Use get_alert_text when the headline is not enough. "
            "Rank hazards by threat to THIS facility and its commuters: immediate life-safety events outweigh minor advisories; consider severity, urgency, certainty, "
            "whether the alert covers the facility, and timing versus the operating window. Detect simultaneous hazards. "
            "Keep verified_facts strictly to what NWS fields/text state; put your own inferences in agent_interpretation. "
            "If urgency/certainty are missing (archived data), say so in data_gaps instead of guessing. If there are no alerts, say so plainly. "
            "Use alert ids exactly as returned. Do not mention any data you did not retrieve."))


def _impact_agent(ctx, rec):
    m = ctx.impact["metrics"]

    @tool
    def get_workforce_metrics() -> dict:
        """Quantified, computed workforce exposure metrics for this facility (counts and percentages)."""
        return {**m, "method_note": ctx.impact["method_note"], "geometry_kinds": ctx.impact["geometry_kinds"]}

    @tool
    def get_exposure_by_home_community() -> dict:
        """Per home community: total employees, high-risk and elevated-risk commuters."""
        return ctx.impact["by_community"]

    @tool
    def get_facility_exposure() -> list:
        """Alerts whose area covers the facility building itself during the decision window."""
        return [{"alert_id": a["id"], "event": a["event"], "level": a["base_level"], "onset": a["onset"], "expires": a["expires"]}
                for a in ctx.impact["facility_alerts"]]

    @tool
    def get_road_conditions() -> dict:
        """Verified road closure data status. If status is 'unavailable', no road data was evaluated."""
        return {k: ctx.roads[k] for k in ("status", "source", "reason", "events")}

    @tool
    def get_facility_workforce_profile() -> dict:
        """Sector, telework/essential/accessibility totals for planning."""
        return {"sector": ctx.facility["sector"], "sector_label": SECTORS[ctx.facility["sector"]]["label"],
                "essential_total": m["essential_total"], "telework_eligible_total": m["telework_eligible_total"],
                "accessibility_total": m["accessibility_total"], "workforce": m["workforce"], "data_is_synthetic": True}

    return Agent(
        name="employee_impact", model=_model(fast=True), callback_handler=None, hooks=[rec],
        tools=[get_workforce_metrics, get_exposure_by_home_community, get_facility_exposure, get_road_conditions, get_facility_workforce_profile],
        structured_output_model=EmployeeImpactAssessment,
        system_prompt=(
            "You are the Employee Impact Agent. " + HINDSIGHT + "Translate emergency conditions into workforce consequences using ONLY numbers returned by your tools. "
            "Call get_workforce_metrics, get_facility_exposure, get_exposure_by_home_community, get_road_conditions and get_facility_workforce_profile. "
            "Never invent commute times, road access or individual exposure: exposure is a straight-line approximation against alert shapes and road data may be unavailable; state that in data_limitations. "
            "Decide scenario_type: e.g. the facility may be unaffected while commutes are blocked (facility_ok_commute_blocked), or the facility itself is in the hazard. "
            "Quantify who is affected (essential staff, telework-eligible, no-telework staff, accessibility needs) and what each group implies operationally. "
            "Employee data is synthetic; say so in data_limitations. Counts you report must match tool values exactly."))


def _decision_agent(ctx, rec):
    det = ctx.deterministic

    @tool
    def get_deterministic_recommendation() -> dict:
        """The rule-engine recommendation: posture, binding rule, every rule with value/threshold/basis, alternatives considered, confidence factors, sensitivity."""
        keys = ("posture", "posture_label", "binding_rule", "rules", "alternatives_considered", "immediate_actions", "sector_notes",
                "confidence", "sensitivity", "justification", "operating_context", "assumptions")
        return {k: det[k] for k in keys}

    @tool
    def get_sector_policy() -> dict:
        """The facility sector's decision parameters, rationale and per-posture playbook."""
        s = SECTORS[ctx.facility["sector"]]
        return {"label": s["label"], "description": s["description"], "params": s["params"], "rationale": s["rationale"], "playbook": s["playbook"]}

    @tool
    def get_evidence_register() -> list:
        """Every input considered, with source and issued / effective / retrieved timestamps."""
        return [e for e in det["evidence"] if e["type"] != "employees"]

    return Agent(
        name="operational_decision", model=_model(), callback_handler=None, hooks=[rec],
        tools=[get_deterministic_recommendation, get_sector_policy, get_evidence_register],
        structured_output_model=SecondOpinion,
        system_prompt=(
            "You are the Operational Decision Agent giving an independent SECOND OPINION on a facility operating-status recommendation. " + HINDSIGHT +
            "You receive the Hazard Intelligence and Employee Impact assessments from upstream agents. Call get_deterministic_recommendation, get_sector_policy and get_evidence_register. "
            "Check whether the rule-engine result is justified, look for overlooked risks, conflicting evidence and thresholds that are barely crossed or barely missed, compare alternative postures with real tradeoffs "
            "(employee safety vs facility accessibility vs essential operations), and state uncertainty and missing data (e.g. no road data). "
            "You MAY disagree. Give your honest recommended_posture. Note: safety-critical rules R1, R2 and R6 are a floor the system enforces; if you recommend a lower posture than that floor, your disagreement will be shown but the floor will stay. "
            "Never present prototype thresholds as official policy. Be concrete and concise; `reasoning` must be a paragraph an emergency manager could repeat verbatim."))


def _comms_agent(ctx, rec):
    @tool
    def get_recipient_groups() -> list:
        """Candidate recipient groups with exact counts (overlay groups overlap with the base groups). Use only these group_ids."""
        return [{k: g[k] for k in ("group_id", "label", "count", "overlay")} for g in recipient_groups(ctx.impact)]

    @tool
    def get_sector_playbook() -> dict:
        """Sector-specific instructions for each operating posture."""
        return SECTORS[ctx.facility["sector"]]["playbook"]

    @tool
    def get_facility_and_hazard_summary() -> dict:
        """Facility, operating hours, and the top hazards with issuance times for the announcement."""
        return {"facility": {k: ctx.facility[k] for k in ("name", "sector", "opening_time", "closing_time", "timezone")},
                "mode": ctx.picture["mode"], "operating_context": ctx.deterministic["operating_context"],
                "alerts_covering_this_facility": [{"event": a["event"], "headline": a["headline"], "issued": a["sent"], "expires": a["expires"]}
                                                  for a in ctx.impact["facility_alerts"]],
                "note": "Only alerts_covering_this_facility may be described as in effect at this facility. Other regional alerts must not be attributed to it."}

    return Agent(
        name="communications_audit", model=_model(), callback_handler=None, hooks=[rec],
        tools=[get_recipient_groups, get_sector_playbook, get_facility_and_hazard_summary],
        structured_output_model=NotificationPlan,
        system_prompt=(
            "You are the Communications & Audit Agent. A human manager has ALREADY approved an operating decision (given in the prompt). "
            "Prepare a DRAFT notification package; you cannot and must not send anything. Call get_recipient_groups, get_sector_playbook and get_facility_and_hazard_summary. "
            "Choose recipient groups (use only returned group_ids), say why each is included and who is excluded and why, give group-specific instructions "
            "(essential vs non-essential, telework vs on-site, accessibility), recommend channels (e.g. email, SMS/text, phone tree, intranet banner, supervisor call), "
            "and write a concise professional all-staff email announcing the manager's decision (not your own preference). Use bracketed placeholders like [Manager name] and [phone number]; never invent contact details. "
            "If the manager overrode the system recommendation, record that factually in audit_explanation along with their stated reason, without criticising it. "
            "Do not claim the notification was sent."))


def _text(res):
    return res.structured_output.model_dump() if res.structured_output is not None else None


def friendly_error(e):
    """Map Bedrock/AWS failures to an actionable message. The caller must NOT show any AI content when this is used."""
    msg = f"{type(e).__name__}: {e}"
    low = msg.lower()
    if "expiredtoken" in low or "unrecognizedclient" in low or "security token" in low or "nocredentials" in low or "unable to locate credentials" in low:
        return "AWS credentials are missing, invalid or expired. Refresh the hackathon credentials and restart the server. No AI analysis was produced. (" + msg[:160] + ")"
    if "accessdenied" in low or "not authorized" in low:
        return f"The AWS role is not permitted to invoke the configured Bedrock model ({config.BEDROCK_MODEL_ID}). No AI analysis was produced. (" + msg[:160] + ")"
    if "throttl" in low or "too many requests" in low:
        return "Bedrock is throttling requests; wait a moment and retry. No AI analysis was produced."
    return "AI analysis failed: " + msg[:300] + " No AI analysis was produced."


def run_second_opinion(ctx):
    """Graph: (hazard_intelligence || employee_impact) -> operational_decision."""
    t0 = time.time()
    recs = {n: EvidenceRecorder(ctx.facility["id"]) for n in ("hazard_intelligence", "employee_impact", "operational_decision")}
    hz, imp, dec = _hazard_agent(ctx, recs["hazard_intelligence"]), _impact_agent(ctx, recs["employee_impact"]), _decision_agent(ctx, recs["operational_decision"])
    b = GraphBuilder()
    b.add_node(hz, "hazard_intelligence"); b.add_node(imp, "employee_impact"); b.add_node(dec, "operational_decision")
    b.add_edge("hazard_intelligence", "operational_decision"); b.add_edge("employee_impact", "operational_decision")
    b.set_max_node_executions(4)
    graph = b.build()
    task = (f"Evaluate facility {ctx.facility['id']} ({ctx.facility['name']}) in {ctx.picture['mode']} mode as of {ctx.picture['as_of']}. "
            f"Rule-engine posture to validate or challenge: {ctx.deterministic['posture']}.")
    try:
        gr = graph(task)
    except Exception as e:
        return {"status": "failed", "error": friendly_error(e), "duration_s": round(time.time() - t0, 1)}
    out = {"status": "ok", "graph_status": str(gr.status), "model": {"decision_and_comms": config.BEDROCK_MODEL_ID, "hazard_and_impact": config.BEDROCK_FAST_MODEL_ID, "region": config.BEDROCK_REGION}}
    for node, key in (("hazard_intelligence", "hazard_assessment"), ("employee_impact", "employee_impact"), ("operational_decision", "second_opinion")):
        nr = gr.results.get(node)
        out[key] = _text(nr.result) if nr is not None and nr.result is not None and hasattr(nr.result, "structured_output") else None
    if not all(out[k] for k in ("hazard_assessment", "employee_impact", "second_opinion")):
        out["status"] = "failed"
        out["error"] = "One or more agents did not return structured output; no AI result is claimed."
    out["tool_calls"] = {n: r.tool_calls for n, r in recs.items()}
    out["duration_s"] = round(time.time() - t0, 1)
    if out["status"] == "ok":
        out["final_ai_recommendation"] = reconcile(ctx.deterministic, out["second_opinion"])
    return out


SAFETY_RULES = {"R1", "R2", "R6"}


def reconcile(det, opinion):
    """The agent may escalate or disagree, but may not quietly lower a posture set by a safety-critical rule."""
    floor = None
    for r in det["rules"]:
        if r["fired"] and r["id"] in SAFETY_RULES and r["posture_if_fired"]:
            if floor is None or POSTURE_RANK[r["posture_if_fired"]] > POSTURE_RANK[floor["posture"]]:
                floor = {"rule": r["id"], "posture": r["posture_if_fired"]}
    want = opinion["recommended_posture"]
    blocked = bool(floor and POSTURE_RANK[want] < POSTURE_RANK[floor["posture"]])
    final = floor["posture"] if blocked else want
    return {"posture": final, "posture_label": POSTURE_LABELS[final], "agent_recommended": want,
            "deterministic_posture": det["posture"], "agent_disagrees_with_deterministic": want != det["posture"],
            "safety_floor": floor, "agent_downgrade_blocked_by_safety_floor": blocked,
            "agent_escalated_above_deterministic": POSTURE_RANK[want] > POSTURE_RANK[det["posture"]]}


def run_notifications(ctx, decision, second_opinion_summary=None):
    t0 = time.time()
    rec = EvidenceRecorder(ctx.facility["id"])
    agent = _comms_agent(ctx, rec)
    prompt = (f"APPROVED MANAGER DECISION (human): posture={decision['selected_posture']} ({POSTURE_LABELS[decision['selected_posture']]}). "
              f"System recommendation was {decision['deterministic_posture']}; AI second opinion was {decision.get('ai_posture')}. "
              f"Override of system recommendation: {decision['is_override']}. Manager reason: {decision.get('reason') or '(none given)'}. "
              f"Decision made by: {decision.get('decided_by') or '[Facility manager]'}. Facility: {ctx.facility['name']}. Prepare the draft notification package.")
    try:
        res = agent(prompt)
    except Exception as e:
        return {"status": "failed", "error": friendly_error(e)}
    plan = _text(res)
    if plan is None:
        return {"status": "failed", "error": "Communications agent returned no structured output; no package is claimed."}
    groups = {g["group_id"]: g for g in recipient_groups(ctx.impact)}
    for gp in plan["group_plans"]:
        g = groups.get(gp["group_id"])
        gp["count"] = g["count"] if g else None
        gp["recipient_ids_synthetic"] = g["employee_ids"] if g else []
        gp["valid_group"] = g is not None
    for ex in plan["excluded"]:
        g = groups.get(ex["group_id"]); ex["count"] = g["count"] if g else None
    return {"status": "ok", "delivery_status": "DRAFT_NOT_SENT: nothing has been emailed or messaged", "plan": plan,
            "tool_calls": rec.tool_calls, "duration_s": round(time.time() - t0, 1),
            "model": {"id": config.BEDROCK_MODEL_ID, "region": config.BEDROCK_REGION}}
