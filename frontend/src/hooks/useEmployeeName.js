// useEmployeeName — one operator identity shared across the whole BPR flow.
//
// The BPR pages are opened from a QR link with NO login, so identity is the
// name the operator types once. Previously every PhaseCard / SessionLogPhase
// kept its OWN name state seeded from localStorage at mount, so setting the
// name in one section never reached the other sections already on screen —
// the operator had to re-enter it at the top of every section.
//
// This hook fixes that: all mounted instances share one value. Setting it
// writes localStorage AND broadcasts a window event so every other instance
// updates immediately (and a native `storage` event keeps other tabs in sync).
import { useState, useEffect, useCallback } from "react";

const KEY = "bpr_employee_name";
const EVENT = "bpr-employee-name-changed";

export default function useEmployeeName() {
  const [name, setName] = useState(() => localStorage.getItem(KEY) || "");

  useEffect(() => {
    const onCustom = (e) => setName(e.detail ?? localStorage.getItem(KEY) ?? "");
    const onStorage = (e) => { if (e.key === KEY) setName(e.newValue || ""); };
    window.addEventListener(EVENT, onCustom);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(EVENT, onCustom);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const setEmployeeName = useCallback((next) => {
    const v = (next || "").trim();
    if (v) localStorage.setItem(KEY, v);
    else localStorage.removeItem(KEY);
    setName(v);
    window.dispatchEvent(new CustomEvent(EVENT, { detail: v }));
  }, []);

  return [name, setEmployeeName];
}
