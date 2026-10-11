// "Past decisions in similar conditions": the team's rule engine run at every archived moment of two real storms,
// hash-chained and stored in Akamai Object Storage (backend/history.py --upload), read back via /api/history.
import { useEffect, useMemo, useState } from "react";
import SAVED from "../history.json";
import { API, STATUS } from "../data.js";

const STATUS_OF = { closure: "closed", telework: "telework", delayed_arrival: "delay", early_dismissal: "delay", normal: "normal" };
const SHORT = { closure: "Full closure", telework: "Telework / leave", delayed_arrival: "Delayed arrival", early_dismissal: "Early dismissal", normal: "Open as normal" };
const ORDER = ["closure", "early_dismissal", "telework", "delayed_arrival", "normal"];
const color = p => STATUS[STATUS_OF[p]].color;
const short = s => (s ? `${s.slice(0, 8)}…` : "—");

export default function PastDecisions({ facilityId, hazard: hazardNow, posture: postureNow, storm = "michael_2018", moment = 2 }) {
  const [hist, setHist] = useState(SAVED);
  const [live, setLive] = useState(false);
  const [hover, setHover] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/history`).then(r => (r.ok ? r.json() : Promise.reject())).then(d => { setHist(d); setLive(true); }).catch(() => {});
  }, []);

  const recs = hist.records;
  const current = recs.find(r => r.facility_id === facilityId && r.storm === storm && r.moment === moment);
  const hazard = current?.hazard || hazardNow || "No warning over the office";
  const similar = useMemo(() => recs.filter(r => r.hazard === hazard && r !== current), [recs, hazard, current]);
  const today = current || { case_id: "today", posture: postureNow || null };

  const counts = ORDER.map(p => ({ p, n: similar.filter(r => r.posture === p).length })).filter(x => x.n);
  const top = counts.slice().sort((a, b) => b.n - a.n)[0];
  const same = similar.filter(r => r.posture === today.posture).length;

  // Dot strip: one column per archived moment, one dot per similar past case (beeswarm stacked)
  const storms = [...new Set(recs.map(r => r.storm))];
  const cols = storms.flatMap(s => [...new Set(recs.filter(r => r.storm === s).map(r => r.moment))].map(m => ({ s, m,
    label: recs.find(r => r.storm === s && r.moment === m).moment_label })));
  const W = 760, colW = W / cols.length, R = 6, GAP = 15, PER_ROW = Math.max(1, Math.floor((colW - 16) / GAP));
  const placed = [];
  cols.forEach((c, ci) => {
    const here = [...similar.filter(r => r.storm === c.s && r.moment === c.m), ...(current && current.storm === c.s && current.moment === c.m ? [current] : [])]
      .sort((a, b) => ORDER.indexOf(a.posture) - ORDER.indexOf(b.posture));
    here.forEach((r, k) => placed.push({ r, x: ci * colW + colW / 2 + ((k % PER_ROW) - (Math.min(here.length, PER_ROW) - 1) / 2) * GAP, row: Math.floor(k / PER_ROW) }));
  });
  const rows = Math.max(1, ...placed.map(d => d.row + 1));
  const H = 40 + rows * GAP + 44;
  const y = row => H - 56 - row * GAP;

  // Chain: the current record and the three stored just before it
  const anchor = current || similar[similar.length - 1];
  const idx = anchor ? recs.indexOf(anchor) : -1;
  const chain = idx >= 0 ? recs.slice(Math.max(0, idx - 3), idx + 1) : [];
  const store = hist.storage;

  return (
    <section className="box past" id="past">
      <div className="past-head">
        <h2 className="label">Past decisions in similar conditions</h2>
        <span className={`data-badge ${live ? "live" : ""}`}><span className="dot" aria-hidden="true" />
          {live ? "Live from Akamai Object Storage" : "Saved copy of the Akamai vault"}</span>
      </div>

      <div className="past-top">
        <div>
          <p className="past-kicker">Same hazard over the office: <strong>{hazard}</strong></p>
          {similar.length ? (
            <p className="past-stat serif"><span>{top.n} of {similar.length}</span> past cases → {SHORT[top.p]}</p>
          ) : <p className="past-stat serif">No past cases match yet</p>}
          <p className="muted small">
            {similar.length && today.posture ? (same === similar.length ? "Today's call matches every past case." : `Today's call (${SHORT[today.posture]}) matches ${same} of ${similar.length}.`) : ""}
          </p>
        </div>
        {similar.length > 0 && (
          <div className="past-bar" role="img" aria-label={counts.map(c => `${SHORT[c.p]} ${c.n}`).join(", ")}>
            {counts.map(c => <span key={c.p} style={{ flex: c.n, background: color(c.p) }} title={`${SHORT[c.p]}: ${c.n}`} />)}
          </div>
        )}
      </div>

      <div className="past-chart">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Dot plot of similar past decisions by storm moment">
          {cols.map((c, ci) => (
            <g key={ci}>
              {ci > 0 && cols[ci - 1].s !== c.s && <line x1={ci * colW} x2={ci * colW} y1={4} y2={H - 4} className="past-divider" />}
              <text x={ci * colW + colW / 2} y={H - 22} textAnchor="middle" className="past-tick">
                <tspan x={ci * colW + colW / 2}>{(c.label.match(/(\w{3} \d+),/) || [])[1]}</tspan>
                <tspan x={ci * colW + colW / 2} dy="13">{(c.label.match(/, ([\d:]+ [AP]M)/) || [])[1]}</tspan>
              </text>
            </g>
          ))}
          {storms.map(s => {
            const first = cols.findIndex(c => c.s === s), n = cols.filter(c => c.s === s).length;
            const none = !placed.some(d => d.r.storm === s);
            return (
              <g key={s}>
                <text x={(first + n / 2) * colW} y={14} textAnchor="middle" className="past-storm">{recs.find(r => r.storm === s).storm_name}</text>
                {none && <text x={(first + n / 2) * colW} y={y(0) + 4} textAnchor="middle" className="past-tick">No {hazard} cases in this storm</text>}
              </g>
            );
          })}
          {placed.map(({ r, x, row }) => {
            const me = r === current;
            return (
              <g key={r.case_id} onMouseEnter={() => setHover({ r, x, y: y(row) })} onMouseLeave={() => setHover(null)}>
                <circle cx={x} cy={y(row)} r={GAP / 2} fill="transparent" />
                <circle cx={x} cy={y(row)} r={me ? R + 1 : R} fill={color(r.posture)} stroke={me ? "#1d2a24" : "#fff"} strokeWidth={me ? 2.5 : 2} />
              </g>
            );
          })}
        </svg>
        {hover && (
          <div className="past-tip" style={{ left: `${(hover.x / W) * 100}%`, top: hover.y }}>
            <strong>{hover.r === current ? "Today: " : ""}{hover.r.facility_name}</strong>
            <span>{hover.r.moment_label} · {hover.r.storm_name}</span>
            <span><i style={{ background: color(hover.r.posture) }} /> {SHORT[hover.r.posture]}{hover.r.binding_rule ? ` · rule ${hover.r.binding_rule}` : ""}</span>
            <span>{hover.r.exposed_pct}% of staff exposed</span>
            <span className="mono">sha256 {short(hover.r.sha256)}</span>
          </div>
        )}
        <div className="past-legend">
          {ORDER.filter(p => similar.some(r => r.posture === p) || today.posture === p).map(p => (
            <span key={p}><i style={{ background: color(p) }} /> {SHORT[p]}</span>
          ))}
          <span><i className="ring" /> Today's decision</span>
        </div>
      </div>

      <h3 className="label" style={{ marginTop: 18 }}>How each decision is stored</h3>
      <div className="chain">
        {chain.map((r, i) => (
          <div key={r.case_id} className={`chain-block ${r === current ? "me" : ""}`}>
            <span className="chain-name">{r === current ? "Today · " : ""}{r.facility_name}</span>
            <span><i style={{ background: color(r.posture) }} /> {SHORT[r.posture]}</span>
            <span className="mono">#{short(r.sha256)}</span>
            <span className="mono muted">prev {short(r.prev_sha256)}</span>
            {i < chain.length - 1 && <span className="chain-arrow" aria-hidden="true">→</span>}
          </div>
        ))}
      </div>
      <p className="footnote">
        Every record is fingerprinted with SHA-256 and linked to the one before it, so changing any past decision breaks the chain.
        {store ? ` Stored in Akamai Object Storage: ${store.bucket}/${store.prefix}` : " Upload to Akamai Object Storage with python -m backend.history --upload."}
        {" "}{hist.count} decisions from the team's rule engine on two real archived storms; employees are synthetic.
      </p>
    </section>
  );
}
