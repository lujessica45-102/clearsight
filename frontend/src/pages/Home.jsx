import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { MapContainer, TileLayer, LayersControl, Polygon, CircleMarker, Tooltip } from "react-leaflet";
import { contours } from "d3-contour";
import { useData } from "../DataContext.jsx";
import { HAZARD_ICONS, STATUS, affectedText } from "../data.js";

// Light -> dark red, one hue (checked: ordered, distinct, readable)
const BANDS = ["#f29a8f", "#e5675b", "#c93a31", "#9b2320", "#6e1414"];
const LEVELS = [0.12, 0.3, 0.5, 0.7, 0.88]; // share of peak density for each contour line
const GRID = 140;                            // contour grid resolution
const SIGMA = 0.012;                         // spread of each employee, in degrees (~1.3 km)

export default function Home() {
  const { data, facility, setFacId } = useData();
  if (!data || !facility) return <p className="loading">Loading…</p>;
  // Live data gives each office its own alert (or none); the sample scenario shares one
  const a = facility.alert === undefined ? data.alert
    : facility.alert || { type: "default", title: "No active warnings", area: facility.name, expires: "—", source: "National Weather Service" };
  const s = STATUS[facility.status] || STATUS.normal;
  const noAlert = a.title === "No active warnings";

  return (
    <>
      <main className="home">
        <aside className="home-side">
          <FacilityMenu data={data} facility={facility} setFacId={setFacId} />
          <section className={`block box ${noAlert ? "calm-box" : "alert-box"}`}>
            <p className="kicker"><span aria-hidden="true">{noAlert ? "✓" : (HAZARD_ICONS[a.type] || HAZARD_ICONS.default)}</span> {noAlert ? "No active alerts" : "Active alert"}</p>
            <h1 className="serif">{a.title}</h1>
            <p className="muted">{noAlert ? "The National Weather Service has no active warnings for this office." : `${a.area} · until ${a.expires}`}</p>
            <p className="muted small">Source: {a.source}</p>
          </section>

          <section className="block box">
            <p className="kicker">This facility</p>
            <h2 className="serif">{facility.name}</h2>
            <p className="sev"><span className="sq" style={{ background: s.color }} aria-hidden="true" />Status: <strong>{s.label}</strong></p>
            {facility.affected == null
              ? <p className="muted small">{facility.address}</p>
              : <p className="stat"><strong>{facility.affected}</strong> of {facility.total} employees affected</p>}
            <ul className="list">{facility.bullets.map((b, i) => <li key={i}>{b}</li>)}</ul>
          </section>
        </aside>

        <section className="home-main">
          <TopoMap data={data} facility={facility} />
          <section className="box">
            <h2 className="label">All facilities</h2>
            <table className="facility-table">
            <thead><tr><th>Facility</th><th>Status</th><th>Affected</th></tr></thead>
            <tbody>
              {data.facilities.map(f => {
                const fs = STATUS[f.status] || STATUS.normal;
                return (
                  <tr key={f.id} className={f.id === facility.id ? "on" : ""} onClick={() => setFacId(f.id)}>
                    <td>{f.name}</td>
                    <td><span className="sq" style={{ background: fs.color }} aria-hidden="true" /> {fs.label}</td>
                    <td>{affectedText(f)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </section>
        </section>
      </main>

      <nav className="page-buttons">
        <Link className="btn" to="/second-opinion">Second opinion →</Link>
        <Link className="btn btn-primary" to="/email">Email →</Link>
      </nav>
    </>
  );
}

// ---- Topographic "heat": density contours of affected employees' home areas ----
function insideRing([x, y], ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
const insidePoly = (pt, poly) => insideRing(pt, poly[0]) && !poly.slice(1).some(h => insideRing(pt, h));

function buildContours(points) {
  if (points.length === 0) return [];
  const pad = SIGMA * 4;
  const lats = points.map(p => p.lat), lons = points.map(p => p.lon);
  const s = Math.min(...lats) - pad, n = Math.max(...lats) + pad;
  const w = Math.min(...lons) - pad * 1.3, e = Math.max(...lons) + pad * 1.3;
  const dx = (e - w) / GRID, dy = (n - s) / GRID;

  const values = new Float64Array(GRID * GRID);
  for (let y = 0; y < GRID; y++) {
    const lat = n - (y + 0.5) * dy;
    for (let x = 0; x < GRID; x++) {
      const lon = w + (x + 0.5) * dx;
      let v = 0;
      for (const p of points) {
        const ddx = (lon - p.lon) / 1.3, ddy = lat - p.lat;
        v += Math.exp(-(ddx * ddx + ddy * ddy) / (2 * SIGMA * SIGMA));
      }
      values[y * GRID + x] = v;
    }
  }
  let max = 0;
  for (const v of values) if (v > max) max = v;

  const toLatLon = ([x, y]) => [n - y * dy, w + x * dx];
  return contours().size([GRID, GRID]).thresholds(LEVELS.map(t => t * max))(values)
    .map((c, i) => {
      const polys = c.coordinates.map(poly => poly.map(ring => ring.map(toLatLon)));
      const count = points.filter(p => polys.some(poly => insidePoly([p.lat, p.lon], poly))).length;
      return { level: i, color: BANDS[i], positions: polys, count };
    })
    .filter(b => b.positions.length > 0);
}

function TopoMap({ data, facility }) {
  const affected = useMemo(
    () => data.employees.filter(e => e.facility === facility.id && e.affected),
    [data.employees, facility.id]
  );
  const bands = useMemo(() => buildContours(affected), [affected]);

  const poly = facility.alertPolygon !== undefined ? facility.alertPolygon
    : facility.alert === undefined ? data.alert.polygon : null;
  const bounds = [
    [facility.lat, facility.lon],
    ...affected.map(e => [e.lat, e.lon]),
    ...(poly || []).map(([lon, lat]) => [lat, lon]),
  ];
  if (bounds.length === 1) bounds.push([facility.lat + 0.12, facility.lon + 0.16], [facility.lat - 0.12, facility.lon - 0.16]);

  return (
    <div className="map-wrap box">
      <MapContainer key={facility.id} className="map" bounds={bounds} boundsOptions={{ padding: [30, 30] }} scrollWheelZoom>
        {/* Map styles: none of these need an API key */}
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="Topographic">
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
              attribution="Tiles &copy; Esri, HERE, Garmin, USGS, &copy; OpenStreetMap contributors" />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Streets">
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution="&copy; OpenStreetMap contributors" />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Satellite">
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution="Tiles &copy; Esri, Maxar, Earthstar Geographics" />
          </LayersControl.BaseLayer>
        </LayersControl>

        {poly && (
          <Polygon positions={poly.map(([lon, lat]) => [lat, lon])}
            pathOptions={{ color: "#1b1f24", weight: 1.5, dashArray: "6 5", fill: false }}>
            <Tooltip sticky>NWS warning area</Tooltip>
          </Polygon>
        )}

        {bands.map(b => (
          <Polygon key={b.level} positions={b.positions}
            pathOptions={{ color: BANDS[Math.min(b.level + 1, BANDS.length - 1)], weight: 1.25, fillColor: b.color, fillOpacity: 0.28 }}
            eventHandlers={{
              mouseover: e => e.target.setStyle({ weight: 2.5, fillOpacity: 0.45 }),
              mouseout:  e => e.target.setStyle({ weight: 1.25, fillOpacity: 0.28 }),
            }}>
            <Tooltip sticky>
              <strong>{b.count} affected employee{b.count === 1 ? "" : "s"}</strong> in this zone
              <div className="tt-muted">Concentration level {b.level + 1} of {BANDS.length}</div>
            </Tooltip>
          </Polygon>
        ))}

        {data.facilities.map(f => {
          const fs = STATUS[f.status] || STATUS.normal;
          const sel = f.id === facility.id;
          return (
            <CircleMarker key={f.id} center={[f.lat, f.lon]} radius={sel ? 9 : 6}
              pathOptions={{ color: "#ffffff", weight: 3, fillColor: sel ? "#1b1f24" : "#7a818c", fillOpacity: 1 }}>
              <Tooltip permanent={sel} direction="right" offset={[10, 0]}>
                <strong>{f.name}</strong>
                {!sel ? null : <div className="tt-muted">{fs.label} · {affectedText(f)} affected</div>}
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>

      <div className="legend">
        <span>Concentration of affected employees</span>
        <span className="ramp">
          <span className="small">Low</span>
          {BANDS.map(c => <span key={c} className="ramp-step" style={{ background: c }} />)}
          <span className="small">High</span>
        </span>
        <span className="legend-item"><span className="key-dash" /> NWS warning area</span>
        <span className="legend-item"><span className="key-dot" /> Facility</span>
      </div>
    </div>
  );
}

// ---- Facility dropdown (top left of the Overview page) ----
function alertFor(f, data) {
  // Live data: each office has its own alert (or none). Sample data: one shared alert.
  if (f.alert === undefined) return data.alert;
  return f.alert;
}

function FacilityMenu({ data, facility, setFacId }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const ref = useRef(null);

  useEffect(() => {
    const close = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const esc = e => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", esc); };
  }, []);

  const s = STATUS[facility.status] || STATUS.normal;
  const current = alertFor(facility, data);
  const list = data.facilities.filter(f => f.name.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="fmenu" ref={ref}>
      <p className="kicker">Facility</p>
      <button className="fmenu-btn" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(o => !o)}>
        <span className="sq" style={{ background: s.color }} aria-hidden="true" />
        <span className="fmenu-name">{facility.name}</span>
        <span className="fmenu-chev" aria-hidden="true">{open ? "▴" : "▾"}</span>
      </button>
      <p className="fmenu-sub">{current ? current.title : "No active warnings"} · {data.facilities.length} facilities</p>

      {open && (
        <div className="fmenu-pop">
          {data.facilities.length > 6 && (
            <input className="fmenu-search" placeholder="Search facilities…" value={q} autoFocus
              onChange={e => setQ(e.target.value)} aria-label="Search facilities" />
          )}
          <ul role="listbox" aria-label="Facilities">
            {list.map(f => {
              const fs = STATUS[f.status] || STATUS.normal;
              const al = alertFor(f, data);
              return (
                <li key={f.id}>
                  <button role="option" aria-selected={f.id === facility.id}
                    className={f.id === facility.id ? "on" : ""}
                    onClick={() => { setFacId(f.id); setOpen(false); setQ(""); }}>
                    <span className="sq" style={{ background: fs.color }} aria-hidden="true" />
                    <span className="fmenu-item">
                      <span className="fmenu-item-name">{f.name}</span>
                      <span className={`fmenu-item-alert ${al ? "has" : ""}`}>
                        {al ? `${HAZARD_ICONS[al.type] || HAZARD_ICONS.default} ${al.title}` : "No active warnings"}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
            {list.length === 0 && <li className="muted small fmenu-empty">No matches</li>}
          </ul>
        </div>
      )}
    </div>
  );
}
