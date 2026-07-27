// NewComponent.jsx — native "New Component Batch" flow.
// Replaces the GAS ?page=wash page: one form that creates ANY component lot
// (ice water hash, solventless hash, nano isolate, 3rd-party distillate/badder,
// future types) by POSTing to /components. The type registry drives the form —
// produced-in-house types ask for strain + yield + input materials; received
// types ask for supplier + manifest + COA. Add a type row in the DB and it
// shows up here with zero frontend changes.
import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../App";
import { useAuth } from "../contexts/AuthContext";
import AppHeader from "./AppHeader";
import "./Dashboard.css";
import "./NewComponent.css";

const blankInput = () => ({ fresh_frozen_uid: "", strain_name: "", input_weight_g: "" });

export default function NewComponent() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [types, setTypes] = useState([]);
  const [loadErr, setLoadErr] = useState("");
  const [typeKey, setTypeKey] = useState("");

  // Shared fields
  const [strain, setStrain] = useState("");
  const [isMixed, setIsMixed] = useState(false);
  const [initialQty, setInitialQty] = useState("");
  const [storage, setStorage] = useState("");
  const [description, setDescription] = useState("");
  const [metrcUid, setMetrcUid] = useState("");

  // Received-only fields
  const [supplier, setSupplier] = useState("");
  const [manifest, setManifest] = useState("");
  const [coaRef, setCoaRef] = useState("");

  // Produced-only: input materials (fresh frozen UIDs feeding the lot)
  const [inputs, setInputs] = useState([blankInput()]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/components/types`).then(r => r.json());
        const list = res.types || [];
        setTypes(list);
        if (list.length) setTypeKey(list[0].key);
      } catch {
        setLoadErr("Failed to load component types — check connection.");
      }
    })();
  }, []);

  const selected = useMemo(
    () => types.find(t => t.key === typeKey) || null,
    [types, typeKey]
  );
  const produced = selected ? !!selected.is_produced_inhouse : true;
  const unit = selected?.unit_of_measure || "g";

  function updateInput(i, field, val) {
    setInputs(prev => prev.map((row, idx) => idx === i ? { ...row, [field]: val } : row));
  }
  function addInputRow()  { setInputs(prev => [...prev, blankInput()]); }
  function removeInputRow(i) { setInputs(prev => prev.filter((_, idx) => idx !== i)); }

  async function submit(e) {
    e.preventDefault();
    setError("");

    if (!selected) { setError("Pick a component type."); return; }
    if (produced && !isMixed && !strain.trim()) {
      setError("Enter a strain, or mark this lot as a mixed-strain run.");
      return;
    }
    if (!produced && !supplier.trim()) {
      setError("Received components need a supplier.");
      return;
    }

    // Only send input rows that have a UID
    const cleanInputs = inputs
      .filter(r => r.fresh_frozen_uid.trim())
      .map(r => ({
        fresh_frozen_uid: r.fresh_frozen_uid.trim(),
        strain_name: r.strain_name.trim() || null,
        input_weight_g: r.input_weight_g === "" ? null : parseFloat(r.input_weight_g),
      }));

    const payload = {
      component_type: selected.key,
      strain: isMixed ? null : (strain.trim() || null),
      is_mixed: isMixed,
      description: description.trim() || null,
      initial_qty: initialQty === "" ? null : parseFloat(initialQty),
      metrc_uid: metrcUid.trim() || null,
      storage_location: storage.trim() || null,
      created_by: user?.email || null,
      inputs: produced ? cleanInputs : [],
      // received-only
      supplier: produced ? null : (supplier.trim() || null),
      manifest_number: produced ? null : (manifest.trim() || null),
      coa_ref: produced ? null : (coaRef.trim() || null),
    };

    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/components`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create component lot");
      navigate(`/components/${encodeURIComponent(data.lot_code)}`);
    } catch (err) {
      setError(err.message || "Failed to create component lot.");
      setSubmitting(false);
    }
  }

  if (loadErr) {
    return (
      <>
        <AppHeader />
        <div className="dash-shell"><div className="dash-error">{loadErr}</div></div>
      </>
    );
  }

  return (
    <>
      <AppHeader />
      <div className="dash-shell nc-shell">
        <header className="dash-header">
          <div>
            <div className="dash-kicker">BatchD · Punch Tools</div>
            <h1 className="dash-title">New Component Batch</h1>
            <p className="lot-sub">
              Create a component lot — ice water hash, solventless hash, nano isolate,
              or a received 3rd-party input. It lands in inventory and can be drawn
              down by product BPRs.
            </p>
          </div>
          <div className="dash-header-right">
            <button className="nc-cancel" onClick={() => navigate("/components")}>Cancel</button>
          </div>
        </header>

        <form className="nc-form" onSubmit={submit}>
          {/* Type picker */}
          <label className="nc-field">
            <span className="nc-label">Component Type</span>
            <select className="nc-input" value={typeKey}
                    onChange={e => setTypeKey(e.target.value)}>
              {types.map(t => (
                <option key={t.key} value={t.key}>
                  {t.display_name}{t.is_produced_inhouse ? "" : " (3rd party)"}
                </option>
              ))}
            </select>
            {selected && (
              <span className="nc-hint">
                Lot codes: <b>{selected.uid_prefix}-…</b> · measured in <b>{unit}</b> ·{" "}
                {produced ? "produced in-house" : "received from supplier"}
              </span>
            )}
          </label>

          {/* Strain / mixed — both flows carry a strain, produced flows can be mixed */}
          <div className="nc-row">
            <label className="nc-field nc-grow">
              <span className="nc-label">Strain {produced && !isMixed ? "" : "(optional)"}</span>
              <input className="nc-input" type="text" value={strain}
                     disabled={isMixed}
                     placeholder={isMixed ? "Mixed strains" : "e.g. Blue Dream"}
                     onChange={e => setStrain(e.target.value)} />
            </label>
            {produced && (
              <label className="nc-check">
                <input type="checkbox" checked={isMixed}
                       onChange={e => setIsMixed(e.target.checked)} />
                <span>Mixed-strain run</span>
              </label>
            )}
          </div>

          {/* Quantity + storage */}
          <div className="nc-row">
            <label className="nc-field nc-grow">
              <span className="nc-label">
                {produced ? "Yield / Starting Qty" : "Received Qty"} ({unit}) <em>optional</em>
              </span>
              <input className="nc-input" type="number" step="any" min="0" value={initialQty}
                     placeholder={produced ? "Leave blank until weighed" : "e.g. 500"}
                     onChange={e => setInitialQty(e.target.value)} />
            </label>
            <label className="nc-field nc-grow">
              <span className="nc-label">Storage Location <em>optional</em></span>
              <input className="nc-input" type="text" value={storage}
                     placeholder="e.g. Freezer B, Shelf 2"
                     onChange={e => setStorage(e.target.value)} />
            </label>
          </div>

          {/* Received-only supplier block */}
          {!produced && (
            <div className="nc-panel">
              <div className="nc-panel-title">Supplier & Compliance</div>
              <div className="nc-row">
                <label className="nc-field nc-grow">
                  <span className="nc-label">Supplier</span>
                  <input className="nc-input" type="text" value={supplier}
                         placeholder="Licensed supplier name"
                         onChange={e => setSupplier(e.target.value)} />
                </label>
                <label className="nc-field nc-grow">
                  <span className="nc-label">Manifest # <em>optional</em></span>
                  <input className="nc-input" type="text" value={manifest}
                         onChange={e => setManifest(e.target.value)} />
                </label>
              </div>
              <div className="nc-row">
                <label className="nc-field nc-grow">
                  <span className="nc-label">METRC UID <em>optional</em></span>
                  <input className="nc-input" type="text" value={metrcUid}
                         onChange={e => setMetrcUid(e.target.value)} />
                </label>
                <label className="nc-field nc-grow">
                  <span className="nc-label">COA Reference <em>optional</em></span>
                  <input className="nc-input" type="text" value={coaRef}
                         onChange={e => setCoaRef(e.target.value)} />
                </label>
              </div>
            </div>
          )}

          {/* Produced-only input materials */}
          {produced && (
            <div className="nc-panel">
              <div className="nc-panel-title">
                Input Materials <em>optional — fresh frozen / source package UIDs</em>
              </div>
              {inputs.map((row, i) => (
                <div className="nc-input-row" key={i}>
                  <input className="nc-input" type="text" placeholder="Source UID / METRC tag"
                         value={row.fresh_frozen_uid}
                         onChange={e => updateInput(i, "fresh_frozen_uid", e.target.value)} />
                  <input className="nc-input" type="text" placeholder="Strain (optional)"
                         value={row.strain_name}
                         onChange={e => updateInput(i, "strain_name", e.target.value)} />
                  <input className="nc-input nc-narrow" type="number" step="any" min="0"
                         placeholder={`Wt (${unit})`}
                         value={row.input_weight_g}
                         onChange={e => updateInput(i, "input_weight_g", e.target.value)} />
                  <button type="button" className="nc-row-del"
                          onClick={() => removeInputRow(i)}
                          disabled={inputs.length === 1}>×</button>
                </div>
              ))}
              <button type="button" className="nc-add" onClick={addInputRow}>+ Add input</button>
            </div>
          )}

          {/* Notes */}
          <label className="nc-field">
            <span className="nc-label">Notes <em>optional</em></span>
            <textarea className="nc-input nc-textarea" rows={2} value={description}
                      placeholder="Anything worth recording about this lot…"
                      onChange={e => setDescription(e.target.value)} />
          </label>

          {error && <div className="nc-error">{error}</div>}

          <div className="nc-actions">
            <button type="button" className="nc-cancel" onClick={() => navigate("/components")}>
              Cancel
            </button>
            <button type="submit" className="nc-submit" disabled={submitting || !selected}>
              {submitting ? "Creating…" : "Create Component Lot"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
