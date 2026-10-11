import { Link } from "react-router-dom";
import { useData } from "../DataContext.jsx";
import { SEVERITY } from "../data.js";
import PastDecisions from "./PastDecisions.jsx";

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

// The team's rule engine (closure/engine.py), written out in plain language
const SHORT_POSTURE = { normal: "Open as normal", delayed_arrival: "Delayed arrival", early_dismissal: "Early dismissal", telework: "Telework / unscheduled leave", closure: "Full closure" };

function explainRule(r, m) {
  const n = m.workforce, pct = r.value, people = v => `${Math.round((v / 100) * n)} of ${n} staff`;
  switch (r.id) {
    case "R1": return {
      q: "Is a life-threatening warning over the office?",
      found: r.fired ? `Yes. A level-${r.value} warning (hurricane, storm surge or extreme wind) covers the building.` : r.value ? `No. The strongest warning here is level ${r.value} of 5.` : "No warning covers the building.",
      why: "Nobody should commute into, or sit in, a building under a catastrophic warning.",
      basis: "National Weather Service warning type" };
    case "R2": return {
      q: "Does a serious warning cover the office during work hours?",
      found: r.fired ? (r.value != null ? `Yes, for about ${r.value} hours of the workday.` : "Yes, with no announced end time.") : "No.",
      why: "A short warning justifies a delay; a long one makes the commute unreasonable.",
      basis: "National Weather Service warning type · 4-hour cut-off is our assumption" };
    case "R6": return {
      q: "Is a tornado or severe thunderstorm warning active right now?",
      found: r.fired ? `Yes (${r.value}).` : "No.",
      why: "These pass within an hour, so people shelter in place instead of closing.",
      basis: "National Weather Service warning type" };
    case "R3": return {
      q: `Do at least ${r.threshold}% of staff have a dangerous commute?`,
      found: `${pct}% do (${people(pct)}).` + (r.fired ? ` That is ${Math.round(pct - r.threshold)} points over the line.` : ""),
      why: "If too many people can't travel safely, the office can't run.",
      basis: "Service-center threshold (our assumption, not USDA policy)" };
    case "R4": return {
      q: `Do at least ${r.threshold}% of staff have a risky commute that won't clear soon?`,
      found: `${pct}% do.` + (r.fired ? ` ${Math.round(pct - r.threshold)} points over the line.` : ""),
      why: "Letting exposed staff telework or take leave keeps them off the road without closing.",
      basis: "Service-center threshold (our assumption, not USDA policy)" };
    case "R5": return {
      q: `Will a risky commute (${r.threshold}%+ of staff) clear within 4 hours of opening?`,
      found: r.fired ? `Yes, ${pct}% are affected but it clears soon.` : `No. ${pct}% are affected, but the hazard does not clear within 4 hours.`,
      why: "A short-lived hazard is best handled by opening late.",
      basis: "Service-center threshold (our assumption, not USDA policy)" };
    case "R7": return {
      q: "Are roads near the office closed?",
      found: r.fired == null ? "Not checked: no road-closure data for this storm." : r.fired ? `Yes (${r.value}).` : "No closures reported.",
      why: "Closed roads can strand people even outside the warning area.",
      basis: "State 511 road feed" };
    default: return { q: r.name, found: String(r.value), why: r.why_this_threshold, basis: r.basis };
  }
}

const RULE_TITLE = { R1: "Life-threatening warning over the office", R2: "Serious warning during work hours", R3: "Too many dangerous commutes",
  R4: "Many risky commutes", R5: "Short-lived commute hazard", R6: "Tornado or severe storm warning", R7: "Road closures" };

function RuleApplied({ rules, binding, metrics }) {
  const r = rules.find(x => x.id === binding);
  if (!r) return <p className="rule-text serif">No rule triggered: open as normal.</p>;
  const x = explainRule(r, metrics);
  const unit = ["R3", "R4", "R5"].includes(r.id) ? "%" : "";
  const val = r.id === "R1" ? `Level ${r.value}` : r.value == null ? "No end time" : `${r.value}${unit}`;
  const line = r.id === "R1" ? `Level ${r.threshold}` : r.threshold == null ? "—" : `${r.threshold}${unit}`;
  return (
    <>
      <p className="rule-text serif">{RULE_TITLE[r.id]}</p>
      <div className="rule-stats">
        <div><span>Found</span><strong>{val}</strong></div>
        <div><span>Line</span><strong>{line}</strong></div>
        <div><span>Leads to</span><strong>{SHORT_POSTURE[r.posture_if_fired] || "—"}</strong></div>
      </div>
      <p className="muted small">Source: {x.basis}</p>
    </>
  );
}

function EngineRules({ rules, binding, metrics, decision, sevColor }) {
  const key = rules.filter(r => r.fired || r.id === binding).sort((a, b) => (a.id === binding ? -1 : b.id === binding ? 1 : 0));
  const rest = rules.filter(r => !key.includes(r));
  return (
    <ol className="dpath">
      {key.length === 0 && (
        <li className="dstep">
          <div className="dstep-rail"><span className="dstep-num">✓</span></div>
          <div className="dstep-card"><p className="dstep-q">No warning covers the office and no commute is exposed.</p></div>
          <div />
        </li>
      )}
      {key.map(r => {
        const x = explainRule(r, metrics);
        const decided = r.id === binding;
        return (
          <li className={`dstep ${decided ? "decided" : ""}`} key={r.id}>
            <div className="dstep-rail"><span className="dstep-num">{r.id}</span></div>
            <div className="dstep-card">
              <div className="dstep-head">
                <p className="dstep-q">{x.q}</p>
                <span className={`ans ${decided ? "yes" : "yes"}`}>{decided ? "Decided it" : "Yes"}</span>
              </div>
              <p className="dstep-found">{x.found} {decided && x.why}</p>
            </div>
            <div className="dstep-alt" aria-label="What this rule leads to">
              <span className="alt-line" aria-hidden="true" />
              <span>{r.posture_if_fired ? <>→ <strong>{SHORT_POSTURE[r.posture_if_fired]}</strong></> : "→ shelter in place"}</span>
            </div>
          </li>
        );
      })}
      <li className="dstep dstep-end">
        <div className="dstep-rail"><span className="dstep-num end" style={{ background: sevColor }}>✓</span></div>
        <div className="dstep-card result" style={{ "--sev": sevColor }}>
          <p className="found-label">Recommendation</p>
          <p className="dresult serif">{decision}</p>
          <p className="muted small" style={{ marginTop: 6 }}>
            Also checked, no: {rest.filter(r => r.fired === false).map(r => explainRule(r, metrics).q.replace(/\?$/, "").toLowerCase()).join("; ")}.
            {rest.some(r => r.fired == null) && <> Not checked (no data): {rest.filter(r => r.fired == null).map(r => explainRule(r, metrics).q.replace(/\?$/, "").toLowerCase()).join("; ")}.</>}
          </p>
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
          <h2 className="label">{op.sectorsLabel || "Relevant sectors"}</h2>
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
          <p className="footnote">{op.sectorsNote || "Numbered by chain of command: 01 is the highest level."}</p>
        </section>
      </div>

      {why && (
        <section className="box how" id="how">
          <h2 className="label">How the agent reached this decision</h2>
          <p className="muted how-intro">{why.rules
            ? "Only the checks that mattered. The strictest \"yes\" sets the recommendation."
            : "The agent follows the same yes/no rules every time. Here is the exact path it took, what it found at each step, and what would have happened if the answer had been different."}</p>

          {why.rules
            ? <EngineRules rules={why.rules} binding={why.binding} metrics={why.metrics} decision={op.decision} sevColor={(SEVERITY[op.severity] || SEVERITY.yellow).color} />
            : <DecisionPath path={why.path} decision={op.decision} sevColor={(SEVERITY[op.severity] || SEVERITY.yellow).color} />}

          <div className="how-bottom">
            <div>
              {why.timeline ? <>
                <h3 className="label">The morning, hour by hour</h3>
                <Timeline rows={why.timeline} />
              </> : <>
                <h3 className="label">What would change this call</h3>
                <ul className="flip">
                  {why.wouldChange.map((w, i) => (
                    <li key={i}>
                      <span className="flip-if">If {w.if.charAt(0).toLowerCase() + w.if.slice(1)}</span>
                      <span className={`flip-arrow ${w.up ? "up" : "down"}`} aria-hidden="true">{w.up ? "↑" : "↓"}</span>
                      <span className="flip-then">{w.then}</span>
                    </li>
                  ))}
                </ul>
              </>}
            </div>
            <div className="rule">
              <h3 className="label">The rule we applied</h3>
              <RuleApplied rules={why.rules} binding={why.binding} metrics={why.metrics} />
              {why.record && <p className="rule-record">Record {why.record.id} · SHA-256 {why.record.sha?.slice(0, 10)}… · {why.record.verified ? "✓ untampered" : "✗ not verified"}</p>}
            </div>
          </div>
        </section>
      )}

      {why?.rules && <PastDecisions facilityId={facility.id} />}

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
