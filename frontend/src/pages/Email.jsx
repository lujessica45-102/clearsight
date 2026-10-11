import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useData } from "../DataContext.jsx";
import { STATUS, instructionFor, API } from "../data.js";

export default function Email() {
  const { facility, employees } = useData();
  const affected = useMemo(() => employees.filter(e => e.affected), [employees]);
  const [picked, setPicked] = useState(new Set());
  const [copied, setCopied] = useState(false);

  // Everyone affected is selected by default whenever the facility changes
  useEffect(() => { setPicked(new Set(affected.map(e => e.id))); }, [affected]);

  if (!facility) return <p className="loading">Loading…</p>;
  const s = STATUS[facility.status] || STATUS.normal;
  const recipients = affected.filter(e => picked.has(e.id));
  const toggle = id => setPicked(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const { subject, body } = facility.email;
  const mailto = `mailto:?bcc=${encodeURIComponent(recipients.map(e => e.email).join(","))}` +
    `&subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
      setCopied(true); setTimeout(() => setCopied(false), 1800);
    } catch { /* clipboard blocked */ }
  }

  return (
    <main className="page">
      <header className="page-head">
        <h1 className="serif">I need an email</h1>
        <p className="muted">
          Recommended message for {facility.name} ·{" "}
          <span className="sq" style={{ background: s.color }} aria-hidden="true" /> {s.label}
        </p>
      </header>

      <div className="split">
        <section className="col">
          <h2 className="label">Example email</h2>
          <div className="email">
            <div className="email-row"><span>To</span><span>{recipients.length} affected employee{recipients.length === 1 ? "" : "s"} (BCC)</span></div>
            <div className="email-row"><span>Subject</span><strong>{subject}</strong></div>
            <pre className="email-body">{body}</pre>
          </div>
          <div className="actions">
            <a className="btn btn-primary" href={mailto}>Open in email app</a>
            <button className="btn" onClick={copy}>{copied ? "Copied" : "Copy text"}</button>
          </div>
        </section>

        <section className="col">
          <h2 className="label">Who to email ({recipients.length} of {affected.length} selected)</h2>
          <table className="people">
            <thead><tr><th aria-label="Include" /><th>Employee</th><th>What they should do</th></tr></thead>
            <tbody>
              {affected.map(e => (
                <tr key={e.id} className={picked.has(e.id) ? "" : "off"}>
                  <td><input type="checkbox" checked={picked.has(e.id)} onChange={() => toggle(e.id)} aria-label={`Include ${e.name}`} /></td>
                  <td>
                    <div className="person">{e.name}{e.essential && <span className="tag">Essential</span>}</div>
                    <div className="muted small">{e.role} · {e.email}</div>
                  </td>
                  <td>{instructionFor(e, facility)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="footnote">
            {employees.length - affected.length} unaffected employee{employees.length - affected.length === 1 ? "" : "s"} not listed.
            Each decision is saved to the <a href={`${API}/vault`} target="_blank" rel="noreferrer">evidence vault on Akamai</a>.
          </p>
        </section>
      </div>

      <nav className="page-buttons">
        <Link className="btn" to="/second-opinion">← Second opinion</Link>
        <Link className="btn" to="/">Overview</Link>
      </nav>
    </main>
  );
}
