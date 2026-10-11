export const API = "http://172.236.108.63";

export const HAZARD_ICONS = {
  tornado: "🌪️", fire: "🔥", wildfire: "🔥", earthquake: "🌎", flood: "🌊",
  hurricane: "🌀", winter: "❄️", ice: "🧊", heat: "🌡️", wind: "💨", default: "⚠️",
};

// Facility operating status (always shown with a text label)
export const STATUS = {
  closed:   { label: "Closed",   color: "#d03b3b" },
  telework: { label: "Telework", color: "#ec835a" },
  delay:    { label: "Delay",    color: "#fab219" },
  normal:   { label: "Normal",   color: "#0ca30c" },
};

export const SEVERITY = {
  red:    { label: "Severe",   color: "#d03b3b" },
  yellow: { label: "Elevated", color: "#fab219" },
  green:  { label: "Low",      color: "#0ca30c" },
};

// What each employee should do, by facility status + their situation
export function instructionFor(emp, facility) {
  if (emp.status === "on_leave") return "On leave: FYI only";
  if (emp.status === "on_detail") return "On detail elsewhere: FYI only";
  if (facility.status === "normal") return "Report as normal";
  if (emp.essential) return "Essential: report when safe";
  if (facility.status === "delay") return "Arrive 2 hours late";
  if (emp.status === "teleworking") return "Continue teleworking";
  return emp.teleworkOk ? "Do not come in: telework" : "Do not come in: excused";
}

// ---------------- Sample data (until the backend serves /api/current) ----------------
const FIRST = ["Dana","Sam","Lee","Maria","Chris","Avery","Jordan","Pat","Riley","Casey","Morgan","Taylor","Jamie","Alex","Drew","Quinn","Reese","Skyler","Hayden","Rowan"];
const LAST  = ["Ruiz","Patel","Johnson","Gomez","Olson","Brooks","Kim","Nguyen","Schmidt","Miller","Larson","Hansen","Carter","Reyes","Fischer","Bauer","Ward","Price","Lund","Meyer"];
const ROLES = ["Office lead","Loan officer","Program technician","Soil conservationist","Facilities tech","Receptionist","District conservationist","Farm loan specialist","Rural development specialist","Engineering tech"];

function makeRoster(fac, seed) {
  const out = [];
  for (let k = 0; k < fac.total; k++) {
    const affected = k < fac.affected;
    const a = (k * 137.5 + seed * 40) * Math.PI / 180;
    const r = affected ? 0.006 + (k % 6) * 0.011 : 0.09 + (k % 4) * 0.03;
    const first = FIRST[(k + seed * 7) % FIRST.length], last = LAST[(k * 3 + seed * 5) % LAST.length];
    out.push({
      id: `${fac.id}-${k}`,
      facility: fac.id,
      name: `${first} ${last}`,
      role: ROLES[(k + seed) % ROLES.length],
      email: `${first}.${last}@usda.gov`.toLowerCase(),
      status: k === 3 ? "teleworking" : k === 5 ? "on_detail" : k === 7 ? "on_leave" : "on_site",
      essential: k === 0 || k === 4,
      teleworkOk: k % 5 !== 2,
      affected,
      lat: fac.lat + r * Math.sin(a),
      lon: fac.lon + r * 1.3 * Math.cos(a),
    });
  }
  return out;
}

const FACILITIES = [
  {
    id: "ia-story-sc", name: "Story County Service Center", short: "Story County",
    lat: 42.0347, lon: -93.6199, total: 14, affected: 12, status: "closed",
    bullets: [
      "Inside the warned area; storm expected nearby around 5:40 AM",
      "12 of 14 employees live in or commute through the warned area",
      "Recommended posture: Closed (OPM: Closed)",
    ],
    reasoning: {
      confidence: "High",
      checkedAt: "4:52 AM",
      path: [
        { id: "q1", answer: "yes", found: "Tornado Warning in effect until 6:00 AM. Certainty: observed on radar.", source: "National Weather Service alerts" },
        { id: "q2", answer: "yes", found: "The office sits inside the warning area, about 4 miles from the storm's path.", source: "Warning map + office address" },
        { id: "q3", answer: "yes", found: "Debris and damage checks run 6–9 AM, overlapping the 6–8 AM commute.", source: "NWS hourly forecast" },
      ],
      steps: [
        { q: "What is happening?", a: "Tornado Warning issued by NWS Des Moines. A tornado has been detected on radar.", push: "up" },
        { q: "Is the office in the danger area?", a: "Yes. The office is inside the warned area.", push: "up" },
        { q: "Does it hit the commute?", a: "The warning ends at 6:00 AM, but debris and damage checks run through the 6–8 AM commute.", push: "up" },
        { q: "How many people are affected?", a: "12 of 14 employees live in or drive through the area.", push: "up" },
      ],
      rule: "Tornado Warning covering the office, plus damage risk during the commute → Close the office.",
      ruleSource: "NWS warning definitions · OPM operating status categories",
      timeline: [
        { label: "Tornado warning", from: 5.25, to: 6, kind: "hazard" },
        { label: "Debris & damage risk", from: 6, to: 9, kind: "risk" },
        { label: "Morning commute", from: 6, to: 8, kind: "commute" },
        { label: "Office hours", from: 8, to: 12, kind: "office" },
      ],
    },
    opinion: {
      decision: "Close the office. Employees should not come in today.",
      severity: "red",
      explanation:
        "The National Weather Service issued a Tornado Warning for Story County with the storm expected near the Service Center around 5:40 AM, " +
        "overlapping the morning commute and opening hours. A warning means a tornado has been detected, not just possible, so the risk to anyone " +
        "on the road or in the building is immediate. Twelve of fourteen employees live inside or near the warned area. Closing keeps people off " +
        "the roads; essential staff follow their own reporting instructions and others may telework if it is safe to do so.",
      sectors: [
        { name: "Office of the Secretary", role: "USDA-wide policy & emergency coordination", decision: "Support local closure", severity: "yellow",
          bullets: ["Local risk doesn't require a department-wide change", "Keep leadership informed through the normal chain", "Confirm employee accountability after the warning"] },
        { name: "Farm Production & Conservation", role: "Mission area that runs Service Centers", decision: "Close affected Service Centers", severity: "red",
          bullets: ["Story County office sits inside the warned area", "Farmer appointments can be rescheduled; no deadline at risk", "Approve telework for staff with equipment and power"] },
        { name: "Iowa State Office", role: "State Executive Director / State Conservationist", decision: "Close Story County; Boone opens late", severity: "red",
          bullets: ["Story County: tornado path crosses commute routes", "Boone: outside the warning, roads may have debris", "Des Moines: unaffected; normal operations"] },
        { name: "Story County Service Center", role: "County Executive Director / office lead", decision: "Closed today", severity: "red",
          bullets: ["Notify all 14 employees before 5:30 AM", "Essential staff: shelter in place, report only when safe", "Post a closure notice for walk-in farmers"] },
      ],
    },
    email: {
      subject: "Story County Service Center CLOSED today: Tornado Warning",
      body:
        "Team,\n\nThe National Weather Service has issued a Tornado Warning for Story County, with the storm expected near our office around 5:40 AM.\n\n" +
        "The Story County Service Center is CLOSED today.\n\n" +
        "• Do not travel to the office.\n" +
        "• If you are telework-ready and it is safe, please telework.\n" +
        "• Essential staff: shelter in place and report only once the warning has ended and it is safe to travel.\n" +
        "• If you are in the warned area, take shelter now in an interior room on the lowest floor.\n\n" +
        "Please reply to confirm you are safe once the warning has passed. We will send an update by 10:00 AM.\n\n" +
        "Stay safe,\nDana Ruiz\nCounty Executive Director",
    },
  },
  {
    id: "ia-boone-fo", name: "Boone Field Office", short: "Boone",
    lat: 42.0597, lon: -93.8802, total: 9, affected: 5, status: "delay",
    bullets: [
      "Just outside the warned area to the west",
      "Debris may block some county roads after the storm passes",
      "Recommended posture: Delayed arrival, 2 hours (OPM: Open with delayed arrival)",
    ],
    reasoning: {
      confidence: "Medium",
      checkedAt: "4:52 AM",
      path: [
        { id: "q1", answer: "yes", found: "Tornado Warning in effect just east of Boone until 6:00 AM.", source: "National Weather Service alerts" },
        { id: "q2", answer: "no", found: "The office is about 6 miles west of the warning area.", source: "Warning map + office address" },
        { id: "q2b", answer: "yes", found: "Commute routes for 5 employees cross the warning area.", source: "Employee roster (home areas)" },
        { id: "q4", answer: "yes", found: "5 of 9 employees (56%) are affected, which is more than half.", source: "Employee roster" },
      ],
      steps: [
        { q: "What is happening?", a: "Tornado Warning issued just east of Boone, in Story County.", push: "up" },
        { q: "Is the office in the danger area?", a: "No. The office is just outside the warned area, to the west.", push: "down" },
        { q: "Does it hit the commute?", a: "Some county roads may have debris until about 8:30 AM.", push: "up" },
        { q: "How many people are affected?", a: "5 of 9 employees use roads that cross the warned area.", push: "even" },
      ],
      rule: "Warning nearby, office outside it, roads affected early in the morning → Open 2 hours late.",
      ruleSource: "NWS warning definitions · OPM operating status categories",
      timeline: [
        { label: "Tornado warning (nearby)", from: 5.25, to: 6, kind: "hazard" },
        { label: "Debris on some roads", from: 6, to: 8.5, kind: "risk" },
        { label: "Morning commute", from: 6, to: 8, kind: "commute" },
        { label: "Office hours (delayed)", from: 10, to: 12, kind: "office" },
      ],
    },
    opinion: {
      decision: "Open 2 hours late. Employees come in after the storm has passed.",
      severity: "yellow",
      explanation:
        "Boone sits just west of the Tornado Warning area. The storm is expected to move northeast and away from the office by about 6:30 AM, " +
        "but roads used by five employees cross the warned area and may have debris afterward. A two-hour delayed arrival gives time for the warning " +
        "to expire and for county crews to clear roads, without losing the whole workday.",
      sectors: [
        { name: "Office of the Secretary", role: "USDA-wide policy & emergency coordination", decision: "No department action", severity: "green",
          bullets: ["Isolated, short-lived local hazard", "No change to national operating status", "Monitor through the state office"] },
        { name: "Farm Production & Conservation", role: "Mission area that runs Service Centers", decision: "Delayed arrival", severity: "yellow",
          bullets: ["Office outside the warned area", "Some commute routes cross it", "Normal service after 10:00 AM"] },
        { name: "Iowa State Office", role: "State Executive Director / State Conservationist", decision: "Open 2 hours late", severity: "yellow",
          bullets: ["Coordinate with Story County closure", "Check road reports at 8:00 AM", "Upgrade to closure if damage is reported"] },
        { name: "Boone Field Office", role: "Office lead", decision: "Open at 10:00 AM", severity: "yellow",
          bullets: ["Notify 9 employees before 6:00 AM", "Telework allowed for anyone whose route is blocked", "Reschedule early appointments"] },
      ],
    },
    email: {
      subject: "Boone Field Office opening 2 hours late today",
      body:
        "Team,\n\nA Tornado Warning is in effect just east of us in Story County this morning. The storm is moving away from Boone, but some roads may have debris.\n\n" +
        "The Boone Field Office will OPEN 2 HOURS LATE today (10:00 AM).\n\n" +
        "• Do not leave for work until the warning has expired.\n" +
        "• If your normal route is blocked, telework if you can and let me know.\n" +
        "• Early appointments will be rescheduled.\n\n" +
        "I'll send an update by 8:00 AM if anything changes.\n\nThanks,\nOffice Lead",
    },
  },
  {
    id: "ia-polk-so", name: "Des Moines State Office", short: "Des Moines",
    lat: 41.5868, lon: -93.6250, total: 40, affected: 3, status: "normal",
    bullets: [
      "About 30 miles south of the warned area",
      "3 employees commute from Story County",
      "Recommended posture: Normal operations",
    ],
    reasoning: {
      confidence: "High",
      checkedAt: "4:52 AM",
      path: [
        { id: "q1", answer: "yes", found: "Tornado Warning in effect about 30 miles north, in Story County.", source: "National Weather Service alerts" },
        { id: "q2", answer: "no", found: "Des Moines is well outside the warning area.", source: "Warning map + office address" },
        { id: "q2b", answer: "yes", found: "3 employees commute from Story County.", source: "Employee roster (home areas)" },
        { id: "q4", answer: "no", found: "3 of 40 employees (8%) are affected, which is well under half.", source: "Employee roster" },
      ],
      steps: [
        { q: "What is happening?", a: "Tornado Warning about 30 miles north, in Story County.", push: "even" },
        { q: "Is the office in the danger area?", a: "No. Des Moines is well outside the warned area.", push: "down" },
        { q: "Does it hit the commute?", a: "Only for 3 employees who commute from Story County.", push: "down" },
        { q: "How many people are affected?", a: "3 of 40 employees, and they can telework.", push: "down" },
      ],
      rule: "Office outside the hazard, few people affected → Stay open; affected commuters telework.",
      ruleSource: "NWS warning definitions · OPM operating status categories",
      timeline: [
        { label: "Tornado warning (30 mi north)", from: 5.25, to: 6, kind: "hazard" },
        { label: "Morning commute", from: 6, to: 8, kind: "commute" },
        { label: "Office hours", from: 8, to: 12, kind: "office" },
      ],
    },
    opinion: {
      decision: "Open as normal. Employees commuting from Story County may telework.",
      severity: "green",
      explanation:
        "The Des Moines State Office is well outside the Tornado Warning and is not expected to be affected. Three employees commute from Story County, " +
        "so they should not travel until the warning ends and may telework today. Everyone else reports as normal.",
      sectors: [
        { name: "Office of the Secretary", role: "USDA-wide policy & emergency coordination", decision: "No department action", severity: "green",
          bullets: ["No impact on the state office", "No change to national operating status", "Monitor through the state office"] },
        { name: "Farm Production & Conservation", role: "Mission area that runs Service Centers", decision: "Normal operations", severity: "green",
          bullets: ["State office outside the hazard", "Support affected county offices", "Track affected staff"] },
        { name: "Iowa State Office", role: "State Executive Director / State Conservationist", decision: "Open; telework for 3 commuters", severity: "green",
          bullets: ["Coordinate county closures from here", "Account for Story County staff", "Prepare for damage reports"] },
        { name: "Des Moines State Office", role: "Office administrator", decision: "Open as normal", severity: "green",
          bullets: ["Notify the 3 Story County commuters", "Everyone else reports as normal", "Keep the operations line staffed"] },
      ],
    },
    email: {
      subject: "Des Moines State Office open today; Story County commuters may telework",
      body:
        "Team,\n\nA Tornado Warning is in effect for Story County this morning. The Des Moines State Office is OPEN as normal.\n\n" +
        "• If you commute from Story County, do not travel until the warning has ended. Please telework today if you can.\n" +
        "• Everyone else, report as normal.\n\n" +
        "We are supporting our Story County and Boone colleagues today; please keep your phone on in case we need help.\n\nThanks,\nState Office",
    },
  },
];

export const MOCK = {
  alert: {
    type: "tornado",
    title: "Tornado Warning",
    area: "Story County, IA",
    expires: "6:00 AM CDT",
    source: "National Weather Service, Des Moines",
    polygon: [[-93.80, 41.95], [-93.50, 41.95], [-93.50, 42.12], [-93.80, 42.12]], // [lon, lat]
  },
  facilities: FACILITIES,
  employees: FACILITIES.flatMap((f, i) => makeRoster(f, i)),
};

// Live data from the backend; falls back to sample data if it's not ready
export async function getCurrent() {
  try {
    const r = await fetch(API + "/api/current");
    if (!r.ok) throw new Error();
    return await r.json();
  } catch {
    return MOCK;
  }
}
