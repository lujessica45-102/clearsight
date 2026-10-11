// Turns the saved output of the team's decision engine (closure/, run by backend/decide.py)
// into the shapes the Overview, Second opinion and Email pages already display.
import DECISIONS from "./decisions.json";
import SECTOR_VIEWS from "./sectorDecisions.json";

const STATUS_OF = { closure: "closed", telework: "telework", delayed_arrival: "delay", early_dismissal: "delay", normal: "normal" };
const SEV_OF = { closure: "red", telework: "yellow", delayed_arrival: "yellow", early_dismissal: "yellow", normal: "green" };
const GROUP_OF = e => e.essential ? "essential_staff" : e.telework_eligible ? "telework_eligible" : "onsite_nonessential_no_telework";

export const DECISION_META = DECISIONS;

function localTime(iso, tz) {
  try {
    return new Date(iso).toLocaleString("en-US", { timeZone: tz, weekday: "short", month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" });
  } catch { return iso; }
}

export function applyEngine(fac) {
  const d = DECISIONS.facilities?.[fac.id];
  if (!d) return { fac, employees: [] };
  const det = d.deterministic, m = d.metrics, labels = DECISIONS.postures;
  const so = d.second_opinion?.status === "ok" ? d.second_opinion : null;
  const op2 = so?.second_opinion, fin = so?.final_ai_recommendation;
  const nt = d.notifications?.status === "ok" ? d.notifications.plan : null;
  const posture = fin?.posture || det.posture;
  const tz = d.engine_facility.timezone;
  const affectedN = m.high_commute_risk + m.elevated_commute_risk;
  const binding = det.rules.find(r => r.id === det.binding_rule);

  // Four USDA sectors (closure/sectors.py), chain of command order: her engine run once per sector on this storm
  const SECTOR_ROLE = {
    headquarters: "e.g. mission-area HQ · runs continuity of operations",
    research_lab: "e.g. Agricultural Research Service station",
    field_office: "e.g. APHIS / Forest Service field crews",
    service_center: "e.g. FSA / NRCS county office",
  };
  const SECTOR_SHORT = {
    headquarters: { normal: "Open as normal", delayed_arrival: "Late arrival, telework option", telework: "Mandatory telework, COOP on standby", early_dismissal: "Release early, finish from home", closure: "Building closed, COOP via telework" },
    research_lab: { normal: "Open; check backup power", delayed_arrival: "Late arrival; care staff keep shift", telework: "Telework; animal/plant care roster on site", early_dismissal: "Finish critical care, then release", closure: "Closed; essential-care crew only" },
    field_office: { normal: "Open; review field assignments", delayed_arrival: "Hold all field deployments", telework: "Stand down field work", early_dismissal: "Recall field crews now", closure: "Stand down all field operations" },
    service_center: { normal: "Open; lobby on alert", delayed_arrival: "Open late; reschedule appointments", telework: "Lobby closed; phones and online only", early_dismissal: "Close lobby, release in waves", closure: "Closed to the public" },
  };
  const ruleWhy = v => {
    const b = v.binding;
    if (!b) return "No warning covers the office and no staff commute is exposed.";
    if (b.id === "R1") return "A life-threatening warning (Hurricane Warning class, level 5 of 5) covers the office itself.";
    if (b.id === "R2") return "A serious warning covers the office during working hours.";
    if (b.id === "R3") return `${v.high_pct}% of staff have a dangerous commute; this sector closes at ${v.params.closure_exposed_pct}%.`;
    if (b.id === "R4") return `${v.high_pct}% of staff have a risky commute; this sector moves to telework at ${v.params.telework_exposed_pct}%.`;
    if (b.id === "R5") return `Risky commutes clear within 4 hours; this sector delays at ${v.params.delay_exposed_pct}%.`;
    return `${b.name}.`;
  };
  const sectors = (SECTOR_VIEWS[fac.id] || []).map(v => ({
    name: v.label, role: SECTOR_ROLE[v.sector],
    decision: SECTOR_SHORT[v.sector][v.posture], severity: SEV_OF[v.posture],
    bullets: [
      ruleWhy(v),
      v.notes?.length ? "Most affected staff can telework, so the sector keeps working remotely instead of closing." : v.rationale,
      `What to do: ${v.action}`,
      `${v.essential} of ${v.workforce} staff essential · ${v.telework} can telework`,
    ],
  }));

  const opinion = {
    decision: labels[posture], severity: SEV_OF[posture],
    explanation: op2?.reasoning || det.justification,
    sectors,
  };

  const reasoning = {
    confidence: det.confidence.level,
    checkedAt: localTime(det.as_of, tz),
    path: [
      { id: "nws", source: `${d.alerts.length} archived National Weather Service alerts` },
      { id: "emp", source: `${m.workforce} employees' commutes (synthetic)` },
      { id: "sector", source: "Service-center sector policy" },
      { id: "roads", source: d.roads.status === "ok" ? "Road closures" : "Road closures: not available in the archive" },
      ...(so ? [{ id: "ai", source: "3 AI agents (hazard, impact, decision)" }] : []),
    ],
    rules: det.rules, labels, binding: det.binding_rule, metrics: m,
    rule: binding ? `${binding.id}: ${binding.name}` : "No threshold crossed",
    ruleSource: binding ? binding.basis : "All rule thresholds are prototype assumptions, not official USDA/OPM policy.",
    whyThreshold: binding?.why_this_threshold,
    wouldChange: det.sensitivity.map(sv => {
      const c = sv.change, n = (c.match(/^(\d+) more/) || [])[1];
      const then = { normal: "Open as normal", delayed_arrival: "Delayed arrival", early_dismissal: "Early dismissal", telework: "Telework / leave", closure: "Full closure" }[sv.would_recommend];
      if (n) return { if: `${n} more staff get a dangerous commute`, then, up: true };
      if (/cancelled, downgraded or expires/.test(c)) return { if: "The warning is cancelled or ends before opening", then: "A lower response", up: false };
      if (/road closures/i.test(c)) return { if: "Road closures are confirmed on commute routes", then: "Possibly stricter", up: true };
      if (/Warning-level alert/.test(c)) return { if: "A warning is issued for the office area", then: "Early dismissal, telework or closure", up: true };
      return { if: c, then: then || sv.would_recommend, up: true };
    }),
    aiWouldChange: op2?.what_would_change || [],
    alternatives: det.alternatives_considered,
    record: { id: d.evaluation_id, sha: d.record?.sha256, verified: DECISIONS.chain_verified },
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
  const hazards = d.alerts.filter(a => a.covers_facility).map(a => a.event);
  const playbook = det.sector_playbook[posture];
  const ess = d.employees.filter(e => e.essential).length;
  const ruleEmail = {
    subject: posture === "normal" ? `${fac.name}: open as normal on ${when}` : `${fac.name}: ${labels[posture]} on ${when}`,
    body:
      `Hello ${fac.name} team,\n\n` +
      (posture === "normal"
        ? `${fac.name} is open as normal on ${when}. No National Weather Service warning covers the office or your commutes right now. We are monitoring Hurricane Michael and will update you if that changes.\n\n`
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

  // ---------- Notification package: who is included / excluded and why, and channel routing ----------
  // Groups mirror closure/agents.py recipient_groups(); the AI comms agent decides inclusion, reasons and channels.
  const people = d.employees;
  const GROUPS = [
    ["essential_staff", "Essential personnel", e => e.essential, false],
    ["telework_eligible", "Non-essential, telework-ready staff", e => !e.essential && e.telework_eligible, false],
    ["onsite_nonessential_no_telework", "Non-essential staff who cannot telework", e => !e.essential && !e.telework_eligible, false],
    ["commute_high_risk", "High-risk commute (overlay)", e => e.commute_risk === "high", true],
    ["commute_elevated_risk", "Elevated-risk commute (overlay)", e => e.commute_risk === "elevated", true],
    ["accessibility_support", "Accessibility needs (overlay)", e => e.accessibility_need, true],
    ["no_or_low_exposure", "No or low commute exposure (overlay)", e => e.commute_risk === "none" || e.commute_risk === "low", true],
  ].map(([id, label, f, overlay]) => ({ id, label, overlay, count: people.filter(f).length }));
  const G = Object.fromEntries(GROUPS.map(g => [g.id, g]));

  let notify;
  if (nt) {
    notify = {
      source: "ai",
      included: nt.group_plans.map(g => ({ id: g.group_id, label: G[g.group_id]?.label || g.group_id, count: g.count, why: g.why_included, instruction: g.instruction, channels: g.channels })),
      excluded: nt.excluded.map(g => ({ id: g.group_id, label: G[g.group_id]?.label || g.group_id, count: g.count, why: g.why_excluded })),
      channelSummary: nt.channel_recommendation, specific: nt.employee_specific_instructions,
      audit: nt.audit_explanation, followUps: nt.follow_up_actions, record: d.notifications.record,
    };
  } else {
    // Rule-based draft until the AI agent has been run
    const act = posture !== "normal";
    const inc = [], exc = [];
    const add = (id, why, instruction, channels) => G[id].count && inc.push({ ...G[id], why, instruction, channels });
    const skip = (id, why) => G[id].count && exc.push({ ...G[id], why });
    add("essential_staff", act ? "Coverage must be confirmed before anyone is released or told to stay home." : "Everyone gets the daily status.",
        act ? "Do not drive while the warning is in effect; supervisor will call with the coverage plan." : "Report as normal.",
        act ? ["Email", "Supervisor phone call"] : ["Email"]);
    add("telework_eligible", "Part of the all-staff announcement; their work can continue remotely.",
        act ? (posture === "delayed_arrival" ? "Start remotely until the all-clear." : "Telework today if it is safe to do so.") : "Report as normal.", ["Email"]);
    add("onsite_nonessential_no_telework", "Part of the all-staff announcement; they need to know whether to travel.",
        act ? (posture === "closure" ? "Stay home; absence is excused." : posture === "telework" ? "Do not travel; unscheduled leave is approved." : "Wait for the all-clear before leaving home.") : "Report as normal.", ["Email"]);
    if (act) {
      add("commute_high_risk", "Their home or route is inside a warning-level hazard, so email alone may not reach them in time.", "Do not travel; confirm you received this.", ["Text message (SMS)"]);
      add("commute_elevated_risk", "Their commute crosses a hazard area; a second channel makes sure they see it.", "Avoid travel until the all-clear.", ["Text message (SMS)"]);
      add("accessibility_support", "May need transport or individual help to stay safe.", "Supervisor will check in with you individually.", ["Supervisor phone call"]);
      skip("no_or_low_exposure", "Already covered by the all-staff email; no extra outreach needed because their commute is not exposed.");
    } else {
      ["commute_high_risk", "commute_elevated_risk", "accessibility_support"].forEach(id => skip(id, "No warning covers this office, so no extra outreach is needed."));
    }
    notify = {
      source: "rules", included: inc, excluded: exc,
      channelSummary: act
        ? "Email to all staff; text message to anyone with an exposed commute; supervisor phone calls to essential staff and anyone needing accessibility support; update the office phone line and website for customers."
        : "One all-staff email. No extra channels needed.",
      specific: [], audit: null, followUps: act ? ["Confirm every high-risk employee has acknowledged the text.", "Recheck the warnings before the next operating day."] : [],
    };
  }

  // ---------- One tailored email per included group ----------
  const PRED = {
    essential_staff: e => e.essential, telework_eligible: e => !e.essential && e.telework_eligible,
    onsite_nonessential_no_telework: e => !e.essential && !e.telework_eligible,
    commute_high_risk: e => e.commute_risk === "high", commute_elevated_risk: e => e.commute_risk === "elevated",
    accessibility_support: e => e.accessibility_need, no_or_low_exposure: e => e.commute_risk === "none" || e.commute_risk === "low",
  };
  const hazardText = hazards.length ? hazards.join(" and ") : "the current weather warnings";
  const statusLine = posture === "normal"
    ? `${fac.name} is open as normal on ${when}. No National Weather Service warning covers the office or your commute right now.`
    : `Because of the ${hazardText} covering our area, ${fac.name} will operate as: ${labels[posture]} on ${when}.`;
  const EXTRA = {
    essential_staff: "Your supervisor will call you this morning to confirm the coverage plan. Please keep your phone on and do not drive while the warning is in effect.",
    telework_eligible: "Log in at your normal start time and let your supervisor know you are online. If you lose power or internet, tell your supervisor and take leave as needed.",
    onsite_nonessential_no_telework: posture === "closure" ? "You do not need to request leave; your absence is excused while the office is closed." : posture === "normal" ? "" : "Unscheduled leave is approved for today. Do not put yourself at risk to get to the office.",
    commute_high_risk: `Your home or your route to the office is inside the area covered by the ${hazardText}. Please reply "received" (or text back) so we know you got this.`,
    commute_elevated_risk: `Your commute crosses an area affected by the ${hazardText}. Please reply "received" so we know you got this.`,
    accessibility_support: "Your supervisor will call you individually to check whether you need transport or any other help to stay safe.",
    no_or_low_exposure: "Your commute is not in the warned area, but please stay alert to changing conditions.",
  };
  const SHORT = { essential_staff: "essential staff", telework_eligible: "telework-ready staff", onsite_nonessential_no_telework: "on-site staff",
    commute_high_risk: "high-risk commutes", commute_elevated_risk: "elevated-risk commutes", accessibility_support: "accessibility support", no_or_low_exposure: "low-exposure staff" };
  const AUD = { essential_staff: "essential personnel", telework_eligible: "staff who are set up to telework",
    onsite_nonessential_no_telework: "staff whose work has to be done on site", commute_high_risk: "employees whose home or commute is inside the warned area",
    commute_elevated_risk: "employees whose commute crosses a hazard area", accessibility_support: "employees who may need extra support to stay safe",
    no_or_low_exposure: "employees whose commute is outside the warned area" };
  const groupEmail = g => ({
    subject: `${fac.name}: ${labels[posture]} on ${when} (${SHORT[g.id] || g.label})`,
    body:
      `Hello,\n\nThis message is for ${AUD[g.id] || "you"}.\n\n` +
      `${statusLine}\n\nWhat you need to do: ${g.instruction}\n\n` +
      (EXTRA[g.id] ? `${EXTRA[g.id]}\n\n` : "") +
      `If you are ever unsafe where you are, contact local emergency services first, then let your supervisor know.\n\n` +
      `Questions: reply to this email or call [office phone number].\n\nThank you,\n[Manager name]\n${fac.name}`,
  });
  if (nt) notify.allStaff = { subject: nt.email.subject, body: nt.email.body };
  notify.included = notify.included.map(g => ({ ...g, members: people.filter(PRED[g.id] || (() => false)).map(e => e.id), email: groupEmail(g) }));

  return {
    fac: {
      ...fac, status: STATUS_OF[posture], total: m.workforce, affected: affectedN,
      bullets: [...fac.bullets.slice(0, 1), `Recommendation: ${labels[posture]}${so ? " (rule engine + AI second opinion)" : " (rule engine)"}`, ...fac.bullets.slice(1)],
      opinion, reasoning, email, notify, engine: d,
    },
    employees,
  };
}
