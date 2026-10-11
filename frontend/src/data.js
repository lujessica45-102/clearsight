import { SCENARIO, FLORIDA_FACILITIES } from "./floridaFacilities.js";

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
  unknown:  { label: "Not decided", color: "#9aa3ad" },
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

// ---------------- Teammate's data: 25 Florida offices + Hurricane Michael replay ----------------
// Built from parser/facilities.sql and closure/replay/michael_2018.json (see floridaFacilities.js)
export const MOCK = {
  mode: "replay",
  scenario: SCENARIO,
  alert: {
    type: "hurricane",
    title: "Hurricane Michael",
    area: "Florida Panhandle",
    expires: "end time not in NWS archive",
    source: "National Weather Service (archived)",
    polygon: null,
  },
  facilities: FLORIDA_FACILITIES,
  employees: [],
};

// Live data from the backend; falls back to sample data if it's not ready
export async function getCurrent() {
  // Add ?demo to the address to show the Hurricane Michael replay instead of live data
  if (new URLSearchParams(window.location.search).has("demo")) return MOCK;
  try {
    const r = await fetch(API + "/api/current");
    if (!r.ok) throw new Error();
    return await r.json();
  } catch {
    return MOCK;
  }
}

// "12 of 14" when the backend knows employee counts, otherwise a dash
export const affectedText = f => (f.affected == null || f.total == null ? "—" : `${f.affected} of ${f.total}`);
