// ComponentInputPanel.jsx — Section 2 cannabis input for BPRs that draw down a
// component lot (NANO SKUs pull nano_isolate, rosin presses pull ice_water_hash).
// The operator picks an available lot from live inventory and records the weight;
// the backend decrements that lot's ledger and writes it into the sheet's
// Section 2 cannabis table. Mirrors the wash→press handoff, generalized.
import { useState, useEffect, useCallback } from "react";
import { API_BASE } from "../App";
import "./ComponentInputPanel.css";

const TYPE_LABELS = {
  nano_isolate:   "Nano Isolate",
  ice_water_hash: "Ice Water Hash",
  solventless_hash: "Solventless Hash",
};

export default function ComponentInputPanel({ uid, componentType, initialConsumed = [] }) {
  const [available, setAvailable] = useState([]);
  const [consumed, setConsumed] = useState(initialConsumed);
  const [lotCode, setLotCode] = useState("");
  const [weight, setWeight] = useState("");
  const [operator, setOperator] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  const typeLabel = TYPE_LABELS[componentType] || componentType;

  const loadAvailable = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_BASE}/components/available?component_type=${encodeURIComponent(componentType)}`
      ).then(r => r.json());
      setAvailable(res.lots || []);
    } catch {
      setError("Couldn't load available lots.");
    } finally {
      setLoaded(true);
    }
  }, [componentType]);

  useEffect(() => { loadAvailable(); }, [loadAvailable]);

  const picked = available.find(l => l.lot_code === lotCode) || null;

  async function record() {
    setError("");
    if (!lotCode)          { setError("Pick a lot."); return; }
    if (!weight || parseFloat(weight) <= 0) { setError("Enter a weight."); return; }
    if (picked && parseFloat(weight) > parseFloat(picked.current_qty)) {
      setError(`Only ${picked.current_qty} ${picked.unit} remain in ${lotCode}.`);
      return;
    }
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE}/bpr/${encodeURIComponent(uid)}/consume-component`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lot_code: lotCode,
          weight_g: parseFloat(weight),
          recorded_by: operator.trim() || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.message || data.detail || "Failed to record input");
      setConsumed(prev => [...prev, data.consumption]);
      setLotCode(""); setWeight("");
      await loadAvailable();
    } catch (e) {
      setError(e.message || "Failed to record input.");
    } finally {
      setBusy(false);
    }
  }

  async function undo(id) {
    setError("");
    setBusy(true);
    try {
      const res = await fetch(
        `${API_BASE}/bpr/${encodeURIComponent(uid)}/consume-component/${id}`,
        { method: "DELETE" }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to undo");
      }
      setConsumed(prev => prev.filter(c => c.id !== id));
      await loadAvailable();
    } catch (e) {
      setError(e.message || "Failed to undo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="cip">
      <div className="cip-head">
        <span className="cip-kicker">Section 2 · Cannabis Input</span>
        <h2 className="cip-title">{typeLabel} Lot</h2>
        <p className="cip-sub">
          Pick the {typeLabel.toLowerCase()} lot going into this batch. Recording it
          decrements inventory and logs it as a Section 2 cannabis source.
        </p>
      </div>

      {/* Already recorded */}
      {consumed.length > 0 && (
        <div className="cip-recorded">
          {consumed.map(c => (
            <div className="cip-chip" key={c.id}>
              <span className="cip-chip-lot">{c.lot_code}</span>
              <span className="cip-chip-wt">{parseFloat(c.weight_g)} {c.unit}</span>
              <button className="cip-chip-x" onClick={() => undo(c.id)} disabled={busy}
                      title="Undo this input">×</button>
            </div>
          ))}
        </div>
      )}

      {/* Picker */}
      <div className="cip-picker">
        <label className="cip-field cip-grow">
          <span className="cip-label">Available Lot</span>
          <select className="cip-input" value={lotCode}
                  onChange={e => setLotCode(e.target.value)} disabled={busy}>
            <option value="">
              {loaded && available.length === 0 ? "No available lots" : "Select a lot…"}
            </option>
            {available.map(l => (
              <option key={l.lot_code} value={l.lot_code}>
                {l.lot_code} — {l.strain || "mixed"} · {parseFloat(l.current_qty)} {l.unit} on hand
              </option>
            ))}
          </select>
        </label>
        <label className="cip-field">
          <span className="cip-label">Weight ({picked?.unit || "g"})</span>
          <input className="cip-input cip-wt" type="number" step="any" min="0"
                 value={weight} onChange={e => setWeight(e.target.value)}
                 placeholder="0" disabled={busy || !lotCode} />
        </label>
        <label className="cip-field">
          <span className="cip-label">Weighed By</span>
          <input className="cip-input" type="text" value={operator}
                 onChange={e => setOperator(e.target.value)}
                 placeholder="Initials" disabled={busy} />
        </label>
        <button className="cip-record" onClick={record} disabled={busy || !lotCode}>
          {busy ? "…" : "Record"}
        </button>
      </div>

      {picked && (
        <div className="cip-hint">
          METRC UID: <b>{picked.metrc_uid || "—"}</b> · remaining after this:{" "}
          <b>{Math.max(0, parseFloat(picked.current_qty) - (parseFloat(weight) || 0)).toFixed(1)} {picked.unit}</b>
        </div>
      )}
      {error && <div className="cip-error">{error}</div>}
    </section>
  );
}
