import { useState } from "react";
import { useData } from "./DataContext.jsx";
import { HAZARD_ICONS } from "./data.js";
import { DAY, HOUR, checkAsOf, fmtAsOf, isoToWall, nudge, tzAbbr, wallToIso } from "./clock.js";

// The time control: shows which moment the whole page is about and lets you change it in a couple of clicks.
export function Clockbar() {
  const { asOf, tz, loading, clockError, clearClockError, moments, jumpTo, goLive, applyAsOf } = useData();
  const live = !asOf;
  // remount the form (and drop any half-typed value) whenever the applied moment or the time zone changes
  return (
    <section className={`clockbar ${live ? "" : "travel"}`} aria-label="Time">
      <ClockForm key={`${asOf}|${tz}`} {...{ asOf, tz, live, loading, clockError, clearClockError, moments, jumpTo, goLive, applyAsOf }} />
    </section>
  );
}

function ClockForm({ asOf, tz, live, loading, clockError, clearClockError, moments, jumpTo, goLive, applyAsOf }) {
  const [draft, setDraft] = useState(null);
  const [localError, setLocalError] = useState(null);
  const [nowIso] = useState(() => new Date().toISOString()); // the newest time the picker allows
  const wall = draft ?? isoToWall(asOf || nowIso, tz);
  const error = localError || clockError;

  const apply = iso => {
    const problem = checkAsOf(iso);
    if (problem) { setLocalError(problem); return; }
    setLocalError(null); clearClockError();
    applyAsOf(iso);
  };
  const step = ms => apply(nudge(asOf, ms));
  const submit = e => {
    e.preventDefault();
    const iso = wallToIso(wall, tz);
    if (!iso) { setLocalError("Pick a date and time first."); return; }
    apply(iso);
  };

  const groups = [...new Set(moments.map(m => m.region || "Other"))];
  const currentMoment = moments.find(m => m.asof === asOf);

  return (
    <>
      <div className="clock-now">
        <span className="clock-label">Time</span>
        <strong className="serif clock-value">
          {live ? <><span className="live-dot" aria-hidden="true" />Live · now</> : fmtAsOf(asOf, tz)}
        </strong>
        {!live && <button type="button" className="clock-live" onClick={goLive} disabled={loading}>← Back to live</button>}
      </div>

      <div className="clock-steps" role="group" aria-label="Move the time">
        <button type="button" className="btn btn-sm" onClick={() => step(-DAY)} disabled={loading}>−1 day</button>
        <button type="button" className="btn btn-sm" onClick={() => step(-HOUR)} disabled={loading}>−1 hour</button>
        <button type="button" className="btn btn-sm" onClick={() => step(HOUR)} disabled={loading || live}>+1 hour</button>
        <button type="button" className="btn btn-sm" onClick={() => step(DAY)} disabled={loading || live}>+1 day</button>
      </div>

      <form className="clock-set" onSubmit={submit} noValidate>
        <label htmlFor="asof-input" className="clock-label">Set time ({tzAbbr(tz, asOf)})</label>
        <input id="asof-input" type="datetime-local" className="clock-input" value={wall} max={isoToWall(nowIso, tz)}
          onChange={e => { setDraft(e.target.value); setLocalError(null); clearClockError(); }} />
        <button type="submit" className="btn btn-sm btn-primary" disabled={loading}>Go</button>
      </form>

      {moments.length > 0 && (
        <div className="clock-jump">
          <label htmlFor="moment-select" className="clock-label">Jump to</label>
          <select id="moment-select" className="picker-select" value={currentMoment?.id || ""} disabled={loading}
            onChange={e => { const m = moments.find(x => x.id === e.target.value); if (m) jumpTo(m); }}>
            <option value="" disabled>a moment…</option>
            {groups.map(g => (
              <optgroup key={g} label={g}>
                {moments.filter(m => (m.region || "Other") === g).map(m => (
                  <option key={m.id} value={m.id}>{HAZARD_ICONS[m.hazard] || ""} {m.label}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
      )}

      {error && <p className="clock-error" role="alert">{error}</p>}
    </>
  );
}

// ---- messages under the clock: what kind of data this is, and what went wrong ----
export function DataNotices() {
  const { data, tz, loading, loadingFor, serviceError } = useData();
  const target = loadingFor ?? null;
  return (
    <>
      {loading && (
        <div className="loadbar" role="status" aria-live="polite">
          <span className="loadbar-line" aria-hidden="true" />
          {target
            ? `Fetching real NWS data for ${fmtAsOf(target, tz)}… archive queries can take ~10 seconds.`
            : "Fetching live NWS data…"}
        </div>
      )}
      {data?.errors?.length > 0 && (
        <div className="banner warn" role="alert">
          <strong>Some data could not be retrieved.</strong> Missing data is not the same as "no alerts".
          <ul>{data.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
        </div>
      )}
      {serviceError && data && (
        <div className="banner warn" role="alert">
          {serviceError} Showing the last data we received; try again in a moment.
        </div>
      )}
      {data && data.mode !== "live" && (
        <div className="notice" role="note">
          {data.disclaimer || `Real National Weather Service records from the past, shown as of ${fmtAsOf(data.as_of, tz)}. This is not a live alert.`}
          {data.data_source?.notes?.length > 0 && (
            <details className="notice-more">
              <summary>About this data</summary>
              <ul>{data.data_source.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
            </details>
          )}
        </div>
      )}
      {data?.clock?.source === "env" && (
        <p className="notice" role="note">The server's clock is set by CLEARSIGHT_NOW, so "live" means the moment it was set to, not the real time.</p>
      )}
    </>
  );
}

export function ServiceDown() {
  const { serviceError, retry, loading } = useData();
  return (
    <main className="page">
      <section className="box service-down" role="alert">
        <h1 className="serif">Can't reach the data service</h1>
        <p className="muted">{serviceError}</p>
        <p className="prose">Nothing is shown rather than showing made-up weather. Check that the backend is running, then try again.</p>
        <button type="button" className="btn btn-primary" onClick={retry} disabled={loading}>{loading ? "Trying…" : "Retry"}</button>
      </section>
    </main>
  );
}

export function Skeleton() {
  return (
    <main className="home" aria-hidden="true">
      <aside className="home-side">
        <div className="box skel" style={{ height: 70 }} />
        <div className="box skel" style={{ height: 150 }} />
        <div className="box skel" style={{ height: 210 }} />
      </aside>
      <section className="home-main">
        <div className="box skel" style={{ height: 560 }} />
      </section>
    </main>
  );
}
