import { BrowserRouter, Routes, Route, NavLink, Link } from "react-router-dom";
import { DataProvider, useData } from "./DataContext.jsx";
import { STATUS } from "./data.js";
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

export default function App() {
  return (
    <DataProvider>
      <BrowserRouter>
        <header className="topbar">
          <div className="topbar-left">
            <Link to="/" className="brand"><Logo />clearsight</Link>
            <FacilityPicker />
          </div>
          <nav className="topnav">
            <NavLink to="/" end>Overview</NavLink>
            <NavLink to="/second-opinion">Second opinion</NavLink>
            <NavLink to="/email">Email</NavLink>
          </nav>
        </header>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/second-opinion" element={<SecondOpinion />} />
          <Route path="/email" element={<Email />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </BrowserRouter>
    </DataProvider>
  );
}
