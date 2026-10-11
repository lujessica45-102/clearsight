import { applyEngine } from "./engineAdapter.js";

// Same-origin by default (the Vite dev server proxies /api to the backend); set VITE_API_URL to point elsewhere.
export const API = import.meta.env.VITE_API_URL ?? "";

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

// ---------------- Data from the backend (always queried, never stored in the app) ----------------
export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

const detailText = d => (typeof d === "string" ? d : d ? JSON.stringify(d) : "");

async function getJson(path) {
  let r;
  try {
    r = await fetch(`${API}${path}`, { headers: { Accept: "application/json" } });
  } catch {
    throw new ApiError("Can't reach the data service.", 0);
  }
  if (r.status === 400) {
    const b = await r.json().catch(() => ({}));
    throw new ApiError(detailText(b.detail) || "That time can't be used.", 400);
  }
  if ([502, 503, 504].includes(r.status)) throw new ApiError(`Can't reach the data service (HTTP ${r.status}).`, r.status);
  if (!r.ok) throw new ApiError(`The data service returned an error (HTTP ${r.status}).`, r.status);
  try { return await r.json(); } catch { throw new ApiError("The data service sent a response we couldn't read.", r.status); }
}

// asOf: ISO-8601 UTC instant, or null for live. Adds the decision-engine view (status, advice, email, employees) to each office.
export async function getCurrent(asOf) {
  const p = await getJson(`/api/current${asOf ? `?asof=${encodeURIComponent(asOf)}` : ""}`);
  const ctx = { postures: p.postures || {}, chainVerified: p.chain_verified, mode: p.mode };
  const done = (p.facilities || []).map(f => applyEngine(f, ctx));
  return { ...p, facilities: done.map(d => d.fac), employees: done.flatMap(d => d.employees) };
}

// Ready-made places and times to jump to (just a place + a timestamp; the weather is still fetched live)
export async function getMoments() {
  try { return (await getJson("/api/moments")).moments || []; } catch { return []; }
}

export const STATE_NAMES = { FL: "Florida", CA: "California", NE: "Nebraska" };

// "12 of 14" when the backend knows employee counts, otherwise a dash
export const affectedText = f => (f.affected == null || f.total == null ? "—" : `${f.affected} of ${f.total}`);
