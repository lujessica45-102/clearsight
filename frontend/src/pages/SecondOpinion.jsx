import { Link } from "react-router-dom";
import { useData } from "../DataContext.jsx";
import { SEVERITY } from "../data.js";

// The decision rules the agent follows, as a yes/no tree.
// Each question leads to another question or to a final decision.
const TREE = {
  q1:  { q: "Is there an active National Weather Service warning for this area?", yes: "q2", no: "open" },
  q2:  { q: "Is the office inside the warning area?", yes: "q3", no: "q2b" },
  q3:  { short: "check the commute timing", q: "Does the danger overlap the morning commute or work hours?", yes: "closed", no: "late" },
  q2b: { short: "check if commutes cross the warning area", q: "Do employees' commutes cross the warning area?", yes: "q4", no: "open" },
  q4:  { short: "count affected employees", q: "Are more than half of the office's employees affected?", yes: "late", no: "openTw" },
};
const OUTCOMES = {
  closed: "Close the office",
  late:   "Open late",
  openTw: "Stay open; affected staff telework",
  open:   "Open as normal",
};

function DecisionPath({ path, decision, sevColor }) {
  const byId = Object.fromEntries(path.map(p => [p.id, p]));
  const steps = [];
  let node = "q1";
  while (TREE[node] && byId[node]) {
    const st = byId[node], def = TREE[node];
    const taken = st.answer === "yes" ? def.yes : def.no;
    const other = st.answer === "yes" ? def.no : def.yes;
    steps.push({ ...st, q: def.q, otherAnswer: st.answer === "yes" ? "No" : "Yes", otherLabel: OUTCOMES[other] || (TREE[other] ? `go on to ${TREE[other].short}` : "ask another question") });
    node = taken;
  }

  return (
    <ol className="dpath">
      {steps.map((st, i) => (
        <li className="dstep" key={st.id}>
          <div className="dstep-rail"><span className="dstep-num">{i + 1}</span></div>
          <div className="dstep-card">
            <div className="dstep-head">
              <p className="dstep-q">{st.q}</p>
              <span className={`ans ${st.answer}`}>{st.answer === "yes" ? "Yes" : "No"}</span>
            </div>
            <p className="dstep-found"><span className="found-label">Found:</span> {st.found}</p>
            <p className="dstep-src">Source: {st.source}</p>
          </div>
          <div className="dstep-alt" aria-label="The path not taken">
            <span className="alt-line" aria-hidden="true" />
            <span>If <strong>{st.otherAnswer}</strong>: {st.otherLabel}</span>
          </div>
        </li>
      ))}
      <li className="dstep dstep-end">
        <div className="dstep-rail"><span className="dstep-num end" style={{ background: sevColor }}>✓</span></div>
        <div className="dstep-card result" style={{ "--sev": sevColor }}>
          <p className="found-label">Recommendation</p>
          <p className="dresult serif">{decision}</p>
        </div>
      </li>
    </ol>
  );
}

function Checked({ path, checkedAt, confidence }) {
  return (
    <div className="checked">
      <p className="checked-head">The agent checked {path.length} things at {checkedAt}</p>
      <ul>
        {path.map(p => (
          <li key={p.id}><span className="tick" aria-hidden="true">✓</span>{p.source}</li>
        ))}
      </ul>
      <p className="checked-conf">Confidence: <strong>{confidence}</strong></p>
    </div>
  );
}

function Severity({ level }) {
  const s = SEVERITY[level] || SEVERITY.yellow;
  return (
    <p className="sev">
      <span className="sq" style={{ background: s.color }} aria-hidden="true" />
      Severity: <strong>{s.label}</strong>
    </p>
  );
}

const fmt = h => {
  const hr = Math.floor(h), m = Math.round((h - hr) * 60);
  const am = hr < 12 ? "AM" : "PM", h12 = hr % 12 === 0 ? 12 : hr % 12;
  return m ? `${h12}:${String(m).padStart(2, "0")} ${am}` : `${h12} ${am}`;
};

function Timeline({ rows }) {
  const START = 4, END = 12, pct = h => ((Math.min(Math.max(h, START), END) - START) / (END - START)) * 100;
  const ticks = [4, 6, 8, 10, 12];
  return (
    <div className="tl">
      {rows.map((r, i) => (
        <div className="tl-row" key={i}>
          <span className="tl-label">{r.label}</span>
          <div className="tl-lane">
            {ticks.map(t => <span key={t} className="tl-grid" style={{ left: `${pct(t)}%` }} />)}
            <span className={`tl-bar ${r.kind}`} style={{ left: `${pct(r.from)}%`, width: `${pct(r.to) - pct(r.from)}%` }}
              title={`${r.label}: ${fmt(r.from)} – ${fmt(r.to)}`}>
              {pct(r.to) - pct(r.from) >= 20 && <span className="tl-time">{fmt(r.from)}–{fmt(r.to)}</span>}
            </span>
            {pct(r.to) - pct(r.from) < 20 && (
              <span className="tl-time-out" style={{ left: `calc(${pct(r.to)}% + 6px)` }}>{fmt(r.from)}–{fmt(r.to)}</span>
            )}
          </div>
        </div>
      ))}
      <div className="tl-row tl-axis">
        <span />
        <div className="tl-lane">
          {ticks.map(t => <span key={t} className="tl-tick" style={{ left: `${pct(t)}%` }}>{fmt(t)}</span>)}
        </div>
      </div>
    </div>
  );
}

export default function SecondOpinion() {
  const { facility } = useData();
  if (!facility) return <p className="loading">Loading…</p>;
  const op = facility.opinion, why = facility.reasoning;
  if (!op) return <Waiting facility={facility} title="I need a second opinion" />;

  return (
    <main className="page">
      <header className="page-head">
        <h1 className="serif">I need a second opinion</h1>
        <p className="muted">{facility.name}</p>
      </header>

      <div className="split">
        <section className="col decision-col" style={{ "--sev": (SEVERITY[op.severity] || SEVERITY.yellow).color }}>
          <h2 className="label">Decision</h2>
          <p className="topline serif">{op.decision}</p>
          <Severity level={op.severity} />
          {why && <Checked path={why.path} checkedAt={why.checkedAt} confidence={why.confidence} />}
          <a className="jump" href="#how">See the full decision path ↓</a>
        </section>

        <section className="col">
          <h2 className="label">Relevant sectors</h2>
          <div className="sector-grid">
            {op.sectors.map((s, i) => (
              <article className="sector" key={i}>
                <p className="sector-num serif">{String(i + 1).padStart(2, "0")}</p>
                <h3>{s.name}</h3>
                <p className="role">{s.role}</p>
                <p className="sector-decision">{s.decision}</p>
                <Severity level={s.severity} />
                <ul className="list">{s.bullets.map((b, j) => <li key={j}>{b}</li>)}</ul>
              </article>
            ))}
          </div>
          <p className="footnote">Numbered by chain of command: 01 is the highest level.</p>
        </section>
      </div>

      {why && (
        <section className="box how" id="how">
          <h2 className="label">How the agent reached this decision</h2>
          <p className="muted how-intro">The agent follows the same yes/no rules every time. Here is the exact path it took, what it found at each step, and what would have happened if the answer had been different.</p>

          <DecisionPath path={why.path} decision={op.decision} sevColor={(SEVERITY[op.severity] || SEVERITY.yellow).color} />

          <div className="how-bottom">
            <div>
              <h3 className="label">The morning, hour by hour</h3>
              <Timeline rows={why.timeline} />
            </div>
            <div className="rule">
              <h3 className="label">The rule we applied</h3>
              <p className="rule-text serif">{why.rule}</p>
              <p className="muted small">Based on: {why.ruleSource}</p>
              <h3 className="label" style={{ marginTop: 18 }}>In plain words</h3>
              <p className="prose small-prose">{op.explanation}</p>
            </div>
          </div>
        </section>
      )}

      <nav className="page-buttons">
        <Link className="btn" to="/">← Overview</Link>
        <Link className="btn btn-primary" to="/email">Email →</Link>
      </nav>
    </main>
  );
}

// Shown when the backend has weather data but no decision logic yet
export function Waiting({ facility, title }) {
  const alerts = facility.alerts || [];
  return (
    <main className="page">
      <header className="page-head">
        <h1 className="serif">{title}</h1>
        <p className="muted">{facility.name}</p>
      </header>
      <section className="box">
        <h2 className="label">Waiting on decision logic</h2>
        <p className="prose">
          The backend is sending live weather for this office, but no closure decision yet.
          This page fills in automatically once the team's decision logic is connected.
        </p>
        <h3 className="label" style={{ marginTop: 20 }}>What the backend reports right now</h3>
        {alerts.length === 0 ? <p className="muted">No active National Weather Service alerts for this office.</p> : (
          <ul className="list">
            {alerts.map((al, i) => (
              <li key={i}><strong>{al.event}</strong> · {al.severity} · until {al.expires ? new Date(al.expires).toLocaleString([], { weekday: "short", hour: "numeric", minute: "2-digit" }) : "—"} · {al.sender}</li>
            ))}
          </ul>
        )}
        {facility.dataSources && <p className="footnote">Sources: {facility.dataSources.length} NWS requests · captured {new Date(facility.weatherCapturedAt).toLocaleString()}</p>}
      </section>
    </main>
  );
}
