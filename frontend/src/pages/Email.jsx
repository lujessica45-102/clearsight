import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useData } from "../DataContext.jsx";
import { STATUS, API } from "../data.js";
import { Waiting } from "./SecondOpinion.jsx";

export default function Email() {
  const { facility, employees } = useData();
  const [active, setActive] = useState(0);
  const [picked, setPicked] = useState(new Set());
  const [copied, setCopied] = useState(false);
  const [shuffling, setShuffling] = useState(false);

  // One card per included group (plus the AI's all-staff draft when it exists)
  const deck = useMemo(() => {
    const n = facility?.notify;
    if (!n) return facility?.email ? [{ id: "all", label: "All affected staff", count: employees.length, members: employees.map(e => e.id), email: facility.email }] : [];
    const cards = n.included.map(g => ({ ...g }));
    if (n.allStaff) cards.unshift({ id: "all_staff", label: "All staff (AI draft)", count: employees.length, members: employees.map(e => e.id), email: n.allStaff });
    return cards;
  }, [facility, employees]);

  useEffect(() => { setActive(0); }, [facility?.id]);
  const card = deck[Math.min(active, deck.length - 1)];
  const members = useMemo(() => (card ? employees.filter(e => card.members.includes(e.id)) : []), [card, employees]);
  useEffect(() => { setPicked(new Set(members.map(e => e.id))); }, [members]);

  if (!facility) return <p className="loading">Loading…</p>;
  if (!card) return <Waiting facility={facility} title="I need an email" />;
  const s = STATUS[facility.status] || STATUS.normal;
  const recipients = members.filter(e => picked.has(e.id));
  const toggle = id => setPicked(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const go = i => setActive((i + deck.length) % deck.length);
  const shuffle = () => { setShuffling(true); setTimeout(() => { go(active + 1); setShuffling(false); }, 260); };

  const { subject, body } = card.email;
  const real = recipients.filter(e => !e.email.endsWith(".invalid"));
  const mailto = `mailto:?bcc=${encodeURIComponent(real.map(e => e.email).join(","))}&subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  async function copy() {
    try { await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`); setCopied(true); setTimeout(() => setCopied(false), 1800); } catch { /* blocked */ }
  }

  return (
    <main className="page">
      <header className="page-head">
        <h1 className="serif">I need an email</h1>
        <p className="muted">
          {deck.length} tailored message{deck.length === 1 ? "" : "s"} for {facility.name} ·{" "}
          <span className="sq" style={{ background: s.color }} aria-hidden="true" /> {s.label}
        </p>
      </header>

      <div className="split">
        <section className="col">
          <div className="deck-head">
            <h2 className="label">Emails, one per group</h2>
            <span className="muted small">{active + 1} of {deck.length}</span>
          </div>

          <div className="deck-tabs" role="tablist">
            {deck.map((c, i) => (
              <button key={c.id} role="tab" aria-selected={i === active} className={`deck-tab ${i === active ? "on" : ""}`} onClick={() => go(i)}>
                {c.label.replace(" (overlay)", "")} <span className="pill">{c.count}</span>
              </button>
            ))}
          </div>

          <div className={`deck ${shuffling ? "shuffling" : ""}`} style={{ "--n": Math.min(deck.length - 1, 3) }}>
            {deck.map((c, i) => {
              const pos = (i - active + deck.length) % deck.length;
              if (pos > 3) return null;
              return (
                <article key={c.id} className={`email deck-card ${pos === 0 ? "top" : ""}`} style={{ "--pos": pos, zIndex: 10 - pos }}
                  aria-hidden={pos !== 0} onClick={() => pos !== 0 && go(i)}>
                  <div className="email-row"><span>To</span><span>{pos === 0 ? recipients.length : c.count} · {c.label.replace(" (overlay)", "")} (BCC)</span></div>
                  <div className="email-row"><span>Subject</span><strong>{c.email.subject}</strong></div>
                  <pre className="email-body">{c.email.body}</pre>
                </article>
              );
            })}
          </div>

          <div className="actions">
            <button className="btn" onClick={() => go(active - 1)} aria-label="Previous email">←</button>
            <button className="btn" onClick={shuffle}>Shuffle to next</button>
            <button className="btn" onClick={() => go(active + 1)} aria-label="Next email">→</button>
            <span className="actions-gap" />
            <a className="btn btn-primary" href={mailto}>Open in email app</a>
            <button className="btn" onClick={copy}>{copied ? "Copied" : "Copy text"}</button>
          </div>
        </section>

        <section className="col">
          <h2 className="label">Who gets this email ({recipients.length} of {members.length} selected)</h2>
          <table className="people">
            <thead><tr><th aria-label="Include" /><th>Employee</th></tr></thead>
            <tbody>
              {members.map(e => (
                <tr key={e.id} className={picked.has(e.id) ? "" : "off"}>
                  <td><input type="checkbox" checked={picked.has(e.id)} onChange={() => toggle(e.id)} aria-label={`Include ${e.name}`} /></td>
                  <td>
                    <div className="person">{e.name}{e.essential && <span className="tag">Essential</span>}{e.risk === "high" && <span className="tag risk">High-risk commute</span>}</div>
                    <div className="muted small">{e.role}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="footnote">
            Employees are synthetic demo data. Each decision is saved to the <a href={`${API}/vault`} target="_blank" rel="noreferrer">evidence vault on Akamai</a>.
          </p>
        </section>
      </div>

      {facility.notify && <NotificationPackage n={facility.notify} onPick={id => go(deck.findIndex(c => c.id === id))} activeId={card.id} />}

      <nav className="page-buttons">
        <Link className="btn" to="/second-opinion">← Second opinion</Link>
        <Link className="btn" to="/">Overview</Link>
      </nav>
    </main>
  );
}

// Who is included and excluded, and why: from the communications agent (or a rule-based draft before it runs)
function NotificationPackage({ n, onPick, activeId }) {
  return (
    <section className="box npkg">
      <div className="npkg-head">
        <h2 className="label">Notification package</h2>
        <span className={`data-badge ${n.source === "ai" ? "live" : ""}`}><span className="dot" aria-hidden="true" />
          {n.source === "ai" ? "Prepared by the communications agent (Strands + Bedrock)" : "Rule-based draft: AI agent not run yet"}</span>
      </div>

      <div className="npkg-grid">
        <div>
          <h3 className="label">Included ({n.included.length} groups)</h3>
          <div className="npkg-wrap">
            <table className="npkg-table">
              <thead><tr><th>Group</th><th>Why they're included</th><th>Their instruction</th></tr></thead>
              <tbody>
                {n.included.map(g => (
                  <tr key={g.id} className={g.id === activeId ? "on" : ""} onClick={() => onPick(g.id)} title="Show this group's email">
                    <td><strong>{g.label}</strong><div><span className="pill">{g.count ?? "?"} {g.count === 1 ? "person" : "people"}</span></div></td>
                    <td>{g.why}</td>
                    <td>{g.instruction}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <h3 className="label">Not included ({n.excluded.length})</h3>
          {n.excluded.length === 0 ? <p className="muted">Nobody is left out.</p> : (
            <ul className="list">{n.excluded.map(g => <li key={g.id}><strong>{g.label}</strong> ({g.count ?? "?"}): {g.why}</li>)}</ul>
          )}
          {n.specific?.length > 0 && <>
            <h3 className="label" style={{ marginTop: 18 }}>Individual instructions</h3>
            <ul className="list">{n.specific.map((x, i) => <li key={i}><strong>{x.applies_to}:</strong> {x.instruction}</li>)}</ul>
          </>}
        </div>
      </div>

      <p className="prose small-prose" style={{ marginTop: 18 }}>{n.channelSummary}</p>

      {(n.followUps?.length > 0 || n.audit) && (
        <div className="npkg-grid" style={{ marginTop: 18 }}>
          {n.followUps?.length > 0 && <div><h3 className="label">Follow-up</h3><ul className="list">{n.followUps.map((f, i) => <li key={i}>{f}</li>)}</ul></div>}
          {n.audit && <div><h3 className="label">Audit note</h3><p className="small-prose">{n.audit}</p>
            {n.record && <p className="footnote">Saved to the decision log · SHA-256 {n.record.sha256?.slice(0, 12)}…</p>}</div>}
        </div>
      )}
    </section>
  );
}
