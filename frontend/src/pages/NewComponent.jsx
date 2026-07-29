// NewComponent.jsx — native "New Component Batch" flow.
// Mirrors the old GAS "New Wash Batch" layout the operators know (source-tag
// rows with a running total, details, and a live Lot ID preview), generalized
// to ANY component type via the dropdown at the top. Add a type row in the DB
// and it shows up here — prefix, unit, and produced-vs-received all come from
// the registry. Posts to the generic POST /components.
import { useState, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../App";
import { useAuth } from "../contexts/AuthContext";
import AppHeader from "./AppHeader";
import "./Dashboard.css";
import "./NewComponent.css";

// Custom dropdown — a native <select>'s option list ignores CSS font-size in
// most browsers, so we render our own large, readable list we fully control.
function TypeSelect({ options, value, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const selected = options.find(o => o.key === value);

  useEffect(() => {
    function onDoc(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <div className="nc-select" ref={ref}>
      <button type="button" className="nc-select-btn" onClick={() => setOpen(o => !o)}
              aria-haspopup="listbox" aria-expanded={open}>
        <span>{selected ? selected.display_name : "Select a component type…"}</span>
        <span className="nc-select-caret">▾</span>
      </button>
      {open && (
        <ul className="nc-select-list" role="listbox">
          {options.map(o => (
            <li key={o.key} role="option" aria-selected={o.key === value}
                className={`nc-select-opt ${o.key === value ? "sel" : ""}`}
                onClick={() => { onChange(o.key); setOpen(false); }}>
              {o.display_name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const MAX_INPUTS = 7;
const blankInput = () => ({ uid: "", strain_name: "", weight: "" });

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function mmddToday() {
  const d = new Date();
  return String(d.getMonth() + 1).padStart(2, "0") + String(d.getDate()).padStart(2, "0");
}
function strainCodeOf(strain, isMixed) {
  if (isMixed) return "MIXED";
  const clean = (strain || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  return clean ? clean.slice(0, 6) : "";
}

export default function NewComponent() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [types, setTypes] = useState([]);
  const [loadErr, setLoadErr] = useState("");
  const [typeKey, setTypeKey] = useState("");

  // Source tags (fresh frozen / received package UIDs feeding this lot)
  const [inputs, setInputs] = useState([blankInput()]);

  // Details
  const [isMixed, setIsMixed] = useState(false);
  const [primaryStrain, setPrimaryStrain] = useState("");
  const [date, setDate] = useState(todayISO());
  const [storage, setStorage] = useState("");

  // Received-only (3rd party)
  const [supplier, setSupplier] = useState("");
  const [manifest, setManifest] = useState("");
  const [coaRef, setCoaRef] = useState("");

  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/components/types`).then(r => r.json());
        const list = res.types || [];
        setTypes(list);
        const active = list.filter(t => !t.archived);
        if (active.length) setTypeKey(active[0].key);
      } catch {
        setLoadErr("Failed to load component types — check connection.");
      }
    })();
  }, []);

  const selected = useMemo(() => types.find(t => t.key === typeKey) || null, [types, typeKey]);
  const produced = selected ? !!selected.is_produced_inhouse : true;
  const unit = selected?.unit_of_measure || "g";
  const prefix = selected?.uid_prefix || "";

  const totalWeight = useMemo(
    () => inputs.reduce((s, r) => s + (parseFloat(r.weight) || 0), 0),
    [inputs]
  );

  // Primary strain auto-fills from the first source tag unless the operator overrides it
  const effectivePrimary = isMixed ? "" : (primaryStrain.trim() || inputs[0]?.strain_name?.trim() || "");
  const strainCode = strainCodeOf(effectivePrimary, isMixed);
  const lotPreview = `${prefix || "———"}-${strainCode || "——————"}-${mmddToday()}-__`;

  function updateInput(i, field, val) {
    setInputs(prev => prev.map((row, idx) => idx === i ? { ...row, [field]: val } : row));
  }
  function addInputRow() { setInputs(prev => prev.length >= MAX_INPUTS ? prev : [...prev, blankInput()]); }
  function removeInputRow(i) { setInputs(prev => prev.length === 1 ? prev : prev.filter((_, idx) => idx !== i)); }

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (!selected) { setError("Pick a component type."); return; }

    const filled = inputs.filter(r => r.uid.trim() || r.weight !== "" || r.strain_name.trim());
    if (filled.length === 0) { setError("Add at least one source tag."); return; }
    for (const r of filled) {
      if (!r.uid.trim()) { setError("Every source row needs a METRC tag UID — the source tag is never optional."); return; }
      if (r.weight === "" || !(parseFloat(r.weight) > 0)) { setError("Every source tag needs a weight — quantity is required."); return; }
    }
    if (produced && !isMixed && !effectivePrimary) {
      setError("Enter the strain, or mark this a mixed-strain run.");
      return;
    }
    if (!produced && !supplier.trim()) { setError("Received components need a supplier."); return; }

    const cleanInputs = filled.map(r => ({
      fresh_frozen_uid: r.uid.trim(),
      strain_name: r.strain_name.trim() || null,
      input_weight_g: parseFloat(r.weight),
    }));

    const payload = {
      component_type: selected.key,
      strain: isMixed ? null : (effectivePrimary || null),
      is_mixed: isMixed,
      initial_qty: totalWeight,
      // A received lot carries its supplier's tag as its own METRC UID; a
      // produced lot's tag is assigned later (at packaging), so it's null now.
      metrc_uid: produced ? null : (cleanInputs[0]?.fresh_frozen_uid || null),
      storage_location: storage.trim() || null,
      created_by: user?.email || null,
      description: description.trim() || null,
      inputs: cleanInputs,
      supplier: produced ? null : (supplier.trim() || null),
      manifest_number: produced ? null : (manifest.trim() || null),
      coa_ref: produced ? null : (coaRef.trim() || null),
      type_data: {
        date: date || null,
        ...(produced ? { wet_weight_g: totalWeight } : {}),
      },
    };

    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/components`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.message || data.detail || "Failed to create component lot");
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
          {/* Component type — custom dropdown (native option lists can't be
              enlarged). display_name already says "(3rd Party)"; archived hidden. */}
          <div className="nc-field">
            <span className="nc-label">Component Type</span>
            <TypeSelect
              options={types.filter(t => !t.archived)}
              value={typeKey}
              onChange={setTypeKey}
            />
            {selected && (
              <span className="nc-hint">
                Lot codes: <b>{prefix}-…</b> · measured in <b>{unit}</b> ·{" "}
                {produced ? "produced in-house" : "received from supplier"}
              </span>
            )}
          </div>

          {/* ── Source tags ── */}
          <div className="nc-panel">
            <div className="nc-panel-title">Source Materials</div>
            <p className="nc-card-intro">
              Enter each <b>Source Tag UID</b> going into this batch (up to {MAX_INPUTS}).
              Each source tag needs a strain name and a weight — <b>the tag and weight are required.</b>
            </p>

            <div className="nc-src-head">
              <span>Source Tag UID *</span>
              <span>Strain Name{produced && !isMixed ? " *" : ""}</span>
              <span>Weight ({unit}) *</span>
              <span />
            </div>
            {inputs.map((row, i) => (
              <div className="nc-src-row" key={i}>
                <input className="nc-input mono" type="text" placeholder="1A4060300005D6A000006811"
                       value={row.uid} onChange={e => updateInput(i, "uid", e.target.value)} />
                <input className="nc-input" type="text" placeholder="e.g. Demon Timez"
                       value={row.strain_name} onChange={e => updateInput(i, "strain_name", e.target.value)} />
                <input className="nc-input" type="number" step="any" min="0" placeholder="4000"
                       value={row.weight} onChange={e => updateInput(i, "weight", e.target.value)} />
                <button type="button" className="nc-row-del" onClick={() => removeInputRow(i)}
                        disabled={inputs.length === 1} title="Remove">×</button>
              </div>
            ))}
            <button type="button" className="nc-add" onClick={addInputRow} disabled={inputs.length >= MAX_INPUTS}>
              + Add another UID
            </button>

            <div className="nc-total">
              <span className="nc-total-label">Total Weight</span>
              <span className="nc-total-num">{totalWeight.toLocaleString()} {unit}</span>
            </div>
          </div>

          {/* ── Details ── */}
          <div className="nc-panel">
            <div className="nc-panel-title">Details</div>
            {produced && (
              <label className="nc-check">
                <input type="checkbox" checked={isMixed} onChange={e => setIsMixed(e.target.checked)} />
                <span>Mixed-strain run — check if combining multiple strains in one batch</span>
              </label>
            )}
            <label className="nc-field">
              <span className="nc-label">
                Primary Strain{produced && !isMixed ? " *" : ""}{" "}
                <em>{isMixed ? "" : "auto-filled from the first source tag"}</em>
              </span>
              <input className="nc-input" type="text" disabled={isMixed}
                     placeholder={isMixed ? "Mixed strains" : (inputs[0]?.strain_name || "e.g. Demon Timez")}
                     value={isMixed ? "" : primaryStrain}
                     onChange={e => setPrimaryStrain(e.target.value)} />
            </label>
            <div className="nc-row">
              <label className="nc-field nc-grow">
                <span className="nc-label">Date</span>
                <input className="nc-input" type="date" value={date} onChange={e => setDate(e.target.value)} />
              </label>
              <label className="nc-field nc-grow">
                <span className="nc-label">Storage Location <em>optional</em></span>
                <input className="nc-input" type="text" placeholder="e.g. Freezer 1 — Shelf 2"
                       value={storage} onChange={e => setStorage(e.target.value)} />
              </label>
            </div>
          </div>

          {/* ── Supplier & compliance (received types) ── */}
          {!produced && (
            <div className="nc-panel">
              <div className="nc-panel-title">Supplier &amp; Compliance</div>
              <div className="nc-row">
                <label className="nc-field nc-grow">
                  <span className="nc-label">Supplier</span>
                  <input className="nc-input" type="text" placeholder="Licensed supplier name"
                         value={supplier} onChange={e => setSupplier(e.target.value)} />
                </label>
                <label className="nc-field nc-grow">
                  <span className="nc-label">Manifest # <em>optional</em></span>
                  <input className="nc-input" type="text" value={manifest}
                         onChange={e => setManifest(e.target.value)} />
                </label>
              </div>
              <label className="nc-field">
                <span className="nc-label">COA Reference <em>optional</em></span>
                <input className="nc-input" type="text" value={coaRef}
                       onChange={e => setCoaRef(e.target.value)} />
              </label>
            </div>
          )}

          {/* ── Lot ID preview ── */}
          <div className="nc-preview">
            <div className="nc-preview-head">
              <span className="nc-preview-label">Generated Lot ID</span>
              <span className="nc-preview-tag">Preview only</span>
            </div>
            <div className="nc-preview-id mono">{lotPreview}</div>
            <div className="nc-preview-sub">
              Sequence number assigned on submit · format: {prefix || "PREFIX"}-{"{STRAIN}"}-{"{MMDD}"}-{"{SEQ}"}
            </div>
          </div>

          {/* Notes */}
          <label className="nc-field">
            <span className="nc-label">Notes <em>optional</em></span>
            <textarea className="nc-input nc-textarea" rows={2} value={description}
                      placeholder="Anything worth recording about this lot…"
                      onChange={e => setDescription(e.target.value)} />
          </label>

          {error && <div className="nc-error">{error}</div>}

          <div className="nc-actions">
            <button type="button" className="nc-cancel" onClick={() => navigate("/components")}>Cancel</button>
            <button type="submit" className="nc-submit" disabled={submitting || !selected}>
              {submitting ? "Creating…" : "Create Component Lot"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
