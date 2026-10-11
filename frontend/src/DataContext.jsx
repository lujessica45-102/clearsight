import { createContext, useContext, useEffect, useState } from "react";
import { getCurrent } from "./data.js";

const Ctx = createContext(null);

// Loads data once and remembers which facility is selected, for every page
export function DataProvider({ children }) {
  const [data, setData] = useState(null);
  const [facId, setFacId] = useState(() => {
    try { return localStorage.getItem("facility"); } catch { return null; }
  });

  useEffect(() => {
    getCurrent().then(d => {
      setData(d);
      setFacId(id => (d.facilities.some(f => f.id === id) ? id : d.facilities[0].id));
    });
  }, []);

  useEffect(() => {
    try { if (facId) localStorage.setItem("facility", facId); } catch { /* ignore */ }
  }, [facId]);

  const facility = data?.facilities.find(f => f.id === facId) || null;
  const employees = data ? data.employees.filter(e => e.facility === facId) : [];
  return <Ctx.Provider value={{ data, facility, employees, facId, setFacId }}>{children}</Ctx.Provider>;
}

export const useData = () => useContext(Ctx);
