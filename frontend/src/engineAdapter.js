// Turns the decision engine's result for one office (the `engine` object the backend attaches to each facility)
// into the shapes the Overview, Second opinion and Email pages already display.

const STATUS_OF = { closure: "closed", telework: "telework", delayed_arrival: "delay", early_dismissal: "delay", normal: "normal" };
const SEV_OF = { closure: "red", telework: "yellow", delayed_arrival: "yellow", early_dismissal: "yellow", normal: "green" };
const GROUP_OF = e => e.essential ? "essential_staff" : e.telework_eligible ? "telework_eligible" : "onsite_nonessential_no_telework";

function localTime(iso, tz) {
  try {
    return new Date(iso).toLocaleString("en-US", { timeZone: tz, weekday: "short", month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" });
  } catch { return iso; }
}

// ctx = { postures, chainVerified, mode } from the API payload
export function applyEngine(fac, ctx = {}) {
  const d = fac.engine;
  if (!d) return { fac, employees: [] };
  const det = d.deterministic, m = d.metrics, labels = ctx.postures || {};
  const archived = ctx.mode && ctx.mode !== "live";
  const so = d.second_opinion?.status === "ok" ? d.second_opinion : null;
  const op2 = so?.second_opinion, fin = so?.final_ai_recommendation;
  const nt = d.notifications?.status === "ok" ? d.notifications.plan : null;
  const posture = fin?.posture || det.posture;
  const tz = d.engine_facility.timezone;
  const affectedN = m.high_commute_risk + m.elevated_commute_risk;
  const binding = det.rules.find(r => r.id === det.binding_rule);

  const sectors = [
    { name: "Rule engine", role: "Fixed thresholds, same every time",
      decision: det.posture_label, severity: SEV_OF[det.posture],
      bullets: [binding ? `Rule ${binding.id} fired: ${binding.name}` : "No rule fired", `Confidence: ${det.confidence.level}`, ...det.immediate_actions.slice(0, 1)] },
    op2 && { name: "AI second opinion", role: `Decision agent · ${so.model?.decision_and_comms || "Bedrock"}`,
      decision: `${op2.verdict.replaceAll("_", " ")}: ${labels[op2.recommended_posture]}`, severity: SEV_OF[op2.recommended_posture],
      bullets: op2.key_factors.slice(0, 3) },
    so?.hazard_assessment && { name: "Hazard check", role: "Hazard intelligence agent",
      decision: so.hazard_assessment.immediate_life_safety_threat ? "Immediate life-safety threat" : "No immediate life-safety threat",
      severity: so.hazard_assessment.immediate_life_safety_threat ? "red" : "yellow",
      bullets: [so.hazard_assessment.summary, ...so.hazard_assessment.data_gaps.slice(0, 1)] },
    { name: "Employee impact", role: so?.employee_impact ? "Employee impact agent" : "Commute exposure analysis",
      decision: `${affectedN} of ${m.workforce} employees affected`, severity: m.high_pct >= 40 ? "red" : affectedN ? "yellow" : "green",
      bullets: so?.employee_impact ? [so.employee_impact.headline, so.employee_impact.telework_assessment]
        : [`${m.high_commute_risk} high-risk and ${m.elevated_commute_risk} elevated-risk commutes`, d.impact_note] },
  ].filter(Boolean);

  const opinion = {
    decision: labels[posture], severity: SEV_OF[posture],
    explanation: op2?.reasoning || det.justification,
    sectors, sectorsLabel: "Who weighed in",
    sectorsNote: so ? "The rule engine sets a safety floor; the AI agents can raise the call but cannot quietly lower it."
                    : "AI second opinion was not run for this moment. The rule engine's result above is complete.",
  };

  const reasoning = {
    confidence: det.confidence.level,
    checkedAt: localTime(det.as_of, tz),
    path: [
      { id: "nws", source: `${d.alerts.length} ${archived ? "archived" : "current"} National Weather Service alert${d.alerts.length === 1 ? "" : "s"}` },
      { id: "emp", source: `${m.workforce} employees' commutes (synthetic)` },
      { id: "sector", source: "Service-center sector policy" },
      { id: "roads", source: d.roads.status === "ok" ? "Road closures" : "Road closures: not available (no traffic data for this moment)" },
      ...(so ? [{ id: "ai", source: "3 AI agents (hazard, impact, decision)" }] : []),
    ],
    rules: det.rules, labels,
    rule: binding ? `${binding.id}: ${binding.name}` : "No threshold crossed",
    ruleSource: binding ? binding.basis : "All rule thresholds are prototype assumptions, not official USDA/OPM policy.",
    whyThreshold: binding?.why_this_threshold,
    wouldChange: op2?.what_would_change?.length ? op2.what_would_change : det.sensitivity.map(s => `${s.change} → ${labels[s.would_recommend] || s.would_recommend}`),
    alternatives: det.alternatives_considered,
    record: { id: d.evaluation_id, sha: d.record?.sha256, verified: ctx.chainVerified },
  };

  // Per-employee instructions: from the AI communications plan when it exists, otherwise from the decision (OPM wording)
  const groupPlan = Object.fromEntries((nt?.group_plans || []).map(g => [g.group_id, g]));
  const ruleInstruction = e => {
    const extra = e.accessibility_need ? " Your supervisor will check in with you individually." : "";
    if (posture === "normal") return "Report as normal." + extra;
    if (e.essential) return "Essential: do not drive while the warning is in effect. Your supervisor will call with the coverage plan." + extra;
    if (posture === "closure") return (e.telework_eligible ? "Office closed: telework today if it is safe to do so." : "Office closed: stay home (excused absence).") + extra;
    if (posture === "telework") return (e.telework_eligible ? "Telework today." : "Do not travel: unscheduled leave is approved.") + extra;
    if (posture === "delayed_arrival") return "Do not leave home until the all-clear; the office opens late." + extra;
    return "Leave early when released in waves; do not wait for the storm." + extra;
  };

  const employees = d.employees.map(e => ({
    id: e.id, facility: fac.id, name: `Employee ${e.id.split("-").pop()}`,
    role: `${e.role_category} · lives ${e.home_community} · ${e.commute_km_straight_line} km commute`,
    email: `${e.id}@synthetic.invalid`,
    status: "on_site", essential: e.essential, teleworkOk: e.telework_eligible,
    affected: e.commute_risk === "high" || e.commute_risk === "elevated",
    risk: e.commute_risk, lat: e.home_lat, lon: e.home_lon,
    instruction: groupPlan[GROUP_OF(e)]?.instruction || ruleInstruction(e),
  }));

  // The email: the AI communications agent's draft if it was generated, otherwise drafted from the decision
  const when = new Date(det.as_of).toLocaleDateString("en-US", { timeZone: tz, weekday: "long", month: "long", day: "numeric" });
  const hazards = [...new Set(d.alerts.filter(a => a.covers_facility).map(a => a.event))];
  const watching = [...new Set(d.alerts.filter(a => !a.covers_facility).map(a => a.event))].slice(0, 2);
  const playbook = det.sector_playbook[posture];
  const ess = d.employees.filter(e => e.essential).length;
  const ruleEmail = {
    subject: posture === "normal" ? `${fac.name}: open as normal on ${when}` : `${fac.name}: ${labels[posture]} on ${when}`,
    body:
      `Hello ${fac.name} team,\n\n` +
      (posture === "normal"
        ? `${fac.name} is open as normal on ${when}. No National Weather Service warning covers the office or your commutes right now. We are monitoring ${watching.length ? watching.join(" and ") : "conditions"} and will update you if that changes.\n\n`
        : `Because of ${hazards.length ? hazards.join(" and ") : "the weather warnings"} covering our area, ${fac.name} will operate as: ${labels[posture]} on ${when}.\n\n`) +
      (posture === "normal" ? "" :
        `What this means for you:\n` +
        (ess ? `• Essential staff: do not drive while the warning is in effect. Your supervisor will call you with the coverage plan.\n` : "") +
        `• Telework-ready staff: ${posture === "delayed_arrival" ? "start remotely until the all-clear" : "telework today if it is safe to do so"}.\n` +
        `• Everyone else: ${posture === "closure" ? "stay home; your absence is excused" : posture === "telework" ? "do not travel; unscheduled leave is approved" : "wait for the all-clear before leaving home"}.\n` +
        `• Office: ${playbook}\n\n`) +
      `If you are not safe where you are, contact local emergency services first, then let your supervisor know.\n\n` +
      `Questions: reply to this email or call [office phone number].\n\nThank you,\n[Manager name]\n${fac.name}`,
    source: "Drafted from the rule engine's decision. The AI communications agent's version replaces this once generated.",
  };
  const email = nt
    ? { subject: nt.email.subject, body: nt.email.body, channels: nt.channel_recommendation, decidedBy: d.manager_decision?.decided_by,
        source: "Drafted by the communications agent (AI) after the manager's decision." }
    : ruleEmail;

  return {
    fac: {
      ...fac, status: STATUS_OF[posture], total: m.workforce, affected: affectedN,
      bullets: [...fac.bullets.slice(0, 1), `Recommendation: ${labels[posture]}${so ? " (rule engine + AI second opinion)" : " (rule engine)"}`, ...fac.bullets.slice(1)],
      opinion, reasoning, email, engine: d,
    },
    employees,
  };
}
