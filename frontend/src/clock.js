// Time helpers for the clock control. The backend takes an ISO-8601 UTC instant (?asof=);
// people think in the facility's local time, so everything here converts between the two.

export const MIN_YEAR = 2005; // IEM's archive of NWS products starts around here (the server enforces the real limit)

const fmtCache = new Map();
function dtf(tz, opts) {
  const key = tz + JSON.stringify(opts);
  if (!fmtCache.has(key)) fmtCache.set(key, new Intl.DateTimeFormat("en-US", { timeZone: tz, ...opts }));
  return fmtCache.get(key);
}

export const browserTz = () => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

function parts(date, tz, opts) {
  return Object.fromEntries(dtf(tz, opts).formatToParts(date).map(p => [p.type, p.value]));
}

// "2018-10-10T09:00:00Z" + "America/Chicago" -> "Wed Oct 10, 2018 · 4:00 AM CDT"
export function fmtAsOf(iso, tz) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso || "";
  const p = parts(d, tz, { weekday: "short", month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" });
  return `${p.weekday} ${p.month} ${p.day}, ${p.year} · ${p.hour}:${p.minute} ${p.dayPeriod} ${p.timeZoneName}`;
}

export function tzAbbr(tz, iso) {
  return parts(iso ? new Date(iso) : new Date(), tz, { timeZoneName: "short" }).timeZoneName;
}

// Instant -> value for <input type="datetime-local"> in the given time zone: "YYYY-MM-DDTHH:mm"
export function isoToWall(iso, tz) {
  const p = parts(new Date(iso), tz, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  return `${p.year}-${p.month}-${p.day}T${p.hour === "24" ? "00" : p.hour}:${p.minute}`;
}

// How far the zone is ahead of UTC at this instant, in ms
function offsetMs(utcMs, tz) {
  const p = parts(new Date(utcMs), tz, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" });
  const asIfUtc = Date.UTC(+p.year, +p.month - 1, +p.day, p.hour === "24" ? 0 : +p.hour, +p.minute, +p.second);
  return asIfUtc - Math.floor(utcMs / 1000) * 1000;
}

// "2018-10-10T04:00" read as wall-clock time in tz -> "2018-10-10T09:00:00Z"
export function wallToIso(wall, tz) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(wall || "");
  if (!m) return null;
  const guess = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]);
  let utc = guess - offsetMs(guess, tz);
  utc = guess - offsetMs(utc, tz); // second pass settles daylight-saving boundaries
  return toIso(new Date(utc));
}

export const toIso = d => d.toISOString().replace(".000Z", "Z");

export function parseAsOf(s) {
  if (!s) return null;
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : toIso(d);
}

// Move an as-of instant (null = now) by a number of milliseconds
export function nudge(asOf, ms, now = new Date()) {
  const base = asOf ? new Date(asOf) : now;
  return toIso(new Date(base.getTime() + ms));
}

export const HOUR = 3600e3, DAY = 24 * HOUR;

// Returns a message if this instant can't be used, otherwise null (the server has the final say)
export function checkAsOf(iso, now = new Date()) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "That date and time isn't valid.";
  if (d.getTime() > now.getTime() + 60e3) return "That time is in the future. NWS data only exists up to now.";
  return null;
}

// ---- remembering the chosen moment across reloads ----
const KEY = "asof";

export function readInitialAsOf() {
  try {
    const fromUrl = parseAsOf(new URLSearchParams(window.location.search).get("asof"));
    if (fromUrl) return fromUrl;
    // A plain reload keeps the moment you were looking at; opening the app fresh starts live.
    const nav = performance.getEntriesByType("navigation")[0];
    if (nav && nav.type === "reload") return parseAsOf(localStorage.getItem(KEY));
  } catch { /* storage or URL blocked */ }
  return null;
}

export function storeAsOf(iso) {
  try { if (iso) localStorage.setItem(KEY, iso); else localStorage.removeItem(KEY); } catch { /* ignore */ }
}

export function syncUrl(iso) {
  try {
    const u = new URL(window.location.href);
    if (iso) u.searchParams.set("asof", iso); else u.searchParams.delete("asof");
    window.history.replaceState(window.history.state, "", u);
  } catch { /* ignore */ }
}
