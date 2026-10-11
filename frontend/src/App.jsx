import { useEffect } from "react";
import { BrowserRouter, Routes, Route, NavLink, Link, useLocation } from "react-router-dom";
import { DataProvider, useData } from "./DataContext.jsx";
import { STATUS, STATE_NAMES } from "./data.js";
import { Clockbar, DataNotices, ServiceDown, Skeleton } from "./Clock.jsx";
import { fmtAsOf, syncUrl } from "./clock.js";
import Home from "./pages/Home.jsx";
import SecondOpinion from "./pages/SecondOpinion.jsx";
import Email from "./pages/Email.jsx";

function Logo() {
  return (
    <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#2f5d4a" />
      <g fill="none" stroke="#fff" strokeWidth="1.6">
        <ellipse cx="16" cy="16" rx="11" ry="8.5" />
        <ellipse cx="16.8" cy="15.5" rx="7" ry="5.2" />
        <ellipse cx="17.4" cy="15.2" rx="3.2" ry="2.4" fill="#fff" />
      </g>
    </svg>
  );
}

function FacilityPicker() {
  const { data, facId, setFacId } = useData();
  if (!data) return null;
  if (data.facilities.length > 4) {  // many offices from the backend: use a dropdown, grouped by state
    const states = [...new Set(data.facilities.map(f => f.state || ""))].sort();
    return (
      <select className="picker-select" value={facId || ""} onChange={e => setFacId(e.target.value)} aria-label="Facility">
        {states.map(st => (
          <optgroup key={st} label={STATE_NAMES[st] || st || "Other"}>
            {data.facilities.filter(f => (f.state || "") === st).sort((a, b) => a.name.localeCompare(b.name))
              .map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
          </optgroup>
        ))}
      </select>
    );
  }
  return (
    <div className="picker" role="radiogroup" aria-label="Facility">
      {data.facilities.map(f => {
        const s = STATUS[f.status] || STATUS.normal;
        return (
          <button key={f.id} role="radio" aria-checked={facId === f.id}
            className={facId === f.id ? "on" : ""} onClick={() => setFacId(f.id)}>
            <span className="sq" style={{ background: s.color }} aria-hidden="true" />
            {f.short}
          </button>
        );
      })}
    </div>
  );
}

function DataBadge() {
  const { data, tz } = useData();
  if (!data) return null;
  const updated = data.generated_at ? new Date(data.generated_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "";
  const label = data.mode === "live" ? `Live NWS data · updated ${updated}`
    : data.mode === "recent" ? `Recent NWS record · as of ${fmtAsOf(data.as_of, tz)}`
    : `Archived NWS record · as of ${fmtAsOf(data.as_of, tz)}`;
  const cached = data.data_source?.cached && data.data_source.cache_retrieved_at
    ? new Date(data.data_source.cache_retrieved_at).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : null;
  return (
    <div className="badges">
      <span className={`data-badge ${data.mode}`}>
        <span className="dot" aria-hidden="true" />{label}
      </span>
      {data.data_source?.cached && <span className="data-tag">cached copy retrieved{cached ? ` ${cached}` : ""}</span>}
    </div>
  );
}

// Keeps ?asof= in the address bar after moving between pages, so a reload lands on the same moment
function UrlSync() {
  const { asOf, data } = useData();
  const { pathname } = useLocation();
  // wait for the first load: before that, "no moment applied yet" must not erase the ?asof= we were opened with
  useEffect(() => { if (data) syncUrl(asOf); }, [asOf, data, pathname]);
  return null;
}

function Body() {
  const { data, fatal, loading } = useData();
  if (fatal) return <ServiceDown />;
  if (!data) return <Skeleton />;
  return (
    <div className={loading ? "is-loading" : ""} aria-busy={loading}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/second-opinion" element={<SecondOpinion />} />
        <Route path="/email" element={<Email />} />
        <Route path="*" element={<Home />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <DataProvider>
      <BrowserRouter>
        <header className="topbar">
          <div className="topbar-left">
            <Link to="/" className="brand"><Logo />clearsight</Link>
          </div>
          <DataBadge />
          <nav className="topnav">
            <NavLink to="/" end>Overview</NavLink>
            <NavLink to="/second-opinion">Second opinion</NavLink>
            <NavLink to="/email">Email</NavLink>
          </nav>
        </header>
        <UrlSync />
        <Clockbar />
        <DataNotices />
        <Body />
      </BrowserRouter>
    </DataProvider>
  );
}
