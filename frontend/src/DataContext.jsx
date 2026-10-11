import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { getCurrent, getMoments, ApiError } from "./data.js";
import { browserTz, readInitialAsOf, storeAsOf, syncUrl } from "./clock.js";

const Ctx = createContext(null);

// Loads the data for one moment (live, or an as-of time) and remembers which facility is selected, for every page.
// The newest request always wins, and a time the server rejects leaves the previous data on screen.
export function DataProvider({ children }) {
  const [data, setData] = useState(null);
  const [asOf, setAsOf] = useState(null);                 // the moment currently shown (null = live)
  const [initialAsOf] = useState(readInitialAsOf);    // the moment we were opened with (URL, or a reload)
  const [pending, setPending] = useState(() => ({ target: initialAsOf })); // a request in flight
  const [clockError, setClockError] = useState(null);     // the server refused a time
  const [serviceError, setServiceError] = useState(null); // the backend couldn't be reached
  const [moments, setMoments] = useState([]);
  const [facId, setFacId] = useState(() => {
    try { return localStorage.getItem("facility"); } catch { return null; }
  });
  const latest = useRef(0);
  const booted = useRef(false); // true once the first load has finished, whatever its outcome

  const load = useCallback(async function run(target, notice = null) {
    const mine = ++latest.current;
    setPending({ target });
    setClockError(notice);
    try {
      const d = await getCurrent(target);
      if (mine !== latest.current) return;
      booted.current = true;
      setData(d); setAsOf(target); setServiceError(null);
      storeAsOf(target); syncUrl(target);
      setFacId(id => (d.facilities.some(f => f.id === id) ? id : d.facilities[0]?.id ?? null));
    } catch (e) {
      if (mine !== latest.current) return;
      if (e instanceof ApiError && e.status === 400) {
        if (!booted.current && target && notice === null) {
          // the very first load used a time the server refused (e.g. an old bookmark): fall back to live and say why
          run(null, e.message);
          return;
        }
        booted.current = true;
        setClockError(e.message);
      } else {
        setServiceError(e.message || "Can't reach the data service.");
      }
    } finally {
      if (mine === latest.current) setPending(null);
    }
  }, []);

  useEffect(() => { load(initialAsOf); getMoments().then(setMoments); }, [load, initialAsOf]);

  useEffect(() => {
    try { if (facId) localStorage.setItem("facility", facId); } catch { /* ignore */ }
  }, [facId]);

  const facility = data?.facilities.find(f => f.id === facId) || null;
  const employees = data ? data.employees.filter(e => e.facility === facId) : [];
  const tz = facility?.timezone || facility?.engine?.engine_facility?.timezone || browserTz();
  const fatal = !data && serviceError;

  const value = {
    data, facility, employees, facId, setFacId, tz, moments,
    asOf, loading: !!pending, loadingFor: pending ? pending.target : undefined,
    clockError, clearClockError: () => setClockError(null),
    serviceError, fatal, retry: () => load(asOf ?? initialAsOf),
    applyAsOf: iso => load(iso),            // iso = UTC instant, or null for live
    goLive: () => load(null),
    jumpTo: m => { if (m.facility_ids?.[0]) setFacId(m.facility_ids[0]); load(m.asof); },
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useData = () => useContext(Ctx);
