// BatchDetail.jsx — single batch view. Port of GAS's batch.html, matching
// its two-column layout: left = Batch Info + Lab Results (+ MRID beneath when
// present), right = Status selector + document/BPR actions.
// Editable now: mfg/pkg date, final + target qty, testing lab (direct sheet
// writes), and status (routed through GAS so updateBatchStatus's side effects
// still run — see tracker.py's PATCH /tracker/batch/{uid}). Still GAS-only:
// lab sample IDs, retail-ID-made, and the push-to-testing actions.
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { API_BASE } from "../App";
import "./PunchDashboard.css";
import AppHeader, { EXTERNAL_LINKS } from "./AppHeader";
import { statusColor, statusPillStyle } from "./PunchDashboard";

// A wash/hash-lot batch is identifiable two ways: batch ID carries the
// HASH- prefix, or the item name says "wash". Ported straight from
// batch.html's isWashBatch() — checking both matters because either
// alone is a single point of failure if someone edits a product name.
//
// In practice this branch should rarely fire here: hash-lot rows carry
// status "Ice Extraction" and are already filtered off the Batches
// dashboard (see PunchDashboard.jsx's COMPONENT_STATUSES), so nobody
// should land on this page for one through normal navigation. Kept
// correct anyway in case someone opens a hash lot's UID directly.
function isWashBatch(b) {
  const id = (b.batchID || "").toUpperCase();
  const name = (b.item || "").toLowerCase();
  return id.indexOf("HASH-") === 0 || name.indexOf("wash") !== -1;
}

// Builds the same param set batch.html's openBPR() sends. The wash
// branch matters for correctness, not just parity: METRC UIDs aren't
// unique for wash batches (one tag can cover several hash lots), so the
// backend's primary key for those has to be the lot code (batchID), not
// the METRC tag — sending the tag as `uid` there would open an
// ambiguous or wrong BPR record. Finished-goods batches are 1:1, so
// those keep uid = METRC UID as before.
function buildBprUrl(b) {
  const wash = isWashBatch(b);
  const params = new URLSearchParams({
    uid: wash ? (b.batchID || "") : (b.metrcUID || ""),
    // Fallback-lookup field only, never the primary identifier for a
    // wash batch. Note: "metricUid" (not "metrcUid") is the actual key
    // name batch.html sends — matching it exactly here since that's
    // presumably what any consuming code expects, typo and all.
    metricUid: wash ? (b.metrcUID || "") : "",
    product: b.item || "",
    batchId: b.batchID || "",
    mfgDate: b.mfgDate || "",
    category: wash ? "rosin_wash" : (b.category || ""),
    // bprType is what detect_product_family keys off first — without it
    // for a wash batch, the backend falls through to rosin_press (the
    // exact bug that caused a duplicate record before).
    bprType: wash ? "wash" : "",
  });
  return `/bpr?${params.toString()}`;
}

// Mirrors tracker.py's LABS and STATUS_LIST (same order as Config.gs). Kept
// as local constants for now rather than a fetch — small, static, and the
// backend validates status on write anyway, so a drift here fails safe
// (rejected with "Invalid status") rather than writing a bad value.
const LAB_OPTIONS = ["Encore", "Infinite", "Landau"];
const STATUS_OPTIONS = [
  "In Production", "Ready for Packaging", "Packaging Complete",
  "Submitted for RND", "Passed RND", "Remake",
  "Need Labels", "Labels Made", "Ready for Testing",
  "Submitted for Compliance", "Delayed in Testing", "Testing Cancelled",
  "Compliance Passed", "Failed", "Compliance Review",
  "Passed BUT NOT Avail in Distru", "Avail in Distru/On Menu", "Archived",
];

// R&D test-type options — verbatim from GAS batch.html's #pushRNDType select.
const RND_TYPES = [
  "R&D - Potency only",
  "R&D - Pesticides only",
  "R&D - Microbials only",
  "R&D - Potency, Pesticides, & Solvents",
];

// Statuses that mean "already submitted to a lab" — gates whether the
// Remove Testing Submission button shows (mirrors GAS's updateRemoveTestingBtn).
const IN_TESTING = new Set([
  "submitted for rnd", "submitted for compliance",
  "ready for testing", "delayed in testing",
]);

// Seed the editable-field form from a loaded batch. One place so the load
// effect and every post-save refresh stay in sync.
function formFromBatch(b) {
  return {
    target_qty: b.targetQty ?? "",
    quantity:   b.quantity ?? "",
    mfg_date:   b.mfgDate ?? "",
    lab:        b.lab ?? "",
    lab_sample_id_rnd: b.labSampleIDRND ?? "",
    lab_sample_id_coa: b.labSampleIDCOA ?? "",
  };
}

// yyyy-mm-dd (from the date input) → m/d/yyyy for the "creates tab" preview,
// matching GAS's updatePushPreview() so the previewed tab name lines up with
// what serverPushToTestingOrder actually creates.
function formatPreviewDate(iso) {
  const d = new Date(iso + "T00:00:00");
  if (isNaN(d.getTime())) return iso;
  return `${d.getMonth() + 1}/${d.getDate()}/${d.getFullYear()}`;
}

export default function BatchDetail() {
  const { uid } = useParams();
  const navigate = useNavigate();
  const [batch, setBatch] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // ── Edit state ──
  const [form, setForm] = useState({
    target_qty: "", quantity: "", mfg_date: "", lab: "",
    lab_sample_id_rnd: "", lab_sample_id_coa: "",
  });
  const [saving, setSaving] = useState("");        // which field is mid-save ("status", "lab", …)
  const [msg, setMsg] = useState({ text: "", ok: true }); // transient save feedback
  const [pendingStatus, setPendingStatus] = useState(null); // selected-but-unsaved status

  // ── Testing-push modal state ──
  const [pushType, setPushType] = useState(null);  // "RND" | "COMPLIANCE" — open push modal
  const [showRemove, setShowRemove] = useState(false);
  const [pushForm, setPushForm] = useState({ date: "", sampleSize: "", rndType: RND_TYPES[0] });
  const [pushBusy, setPushBusy] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(`${API_BASE}/tracker/batch/${encodeURIComponent(uid)}`);
        const json = await res.json();
        if (!json.success) throw new Error(json.error || "Batch not found");
        setBatch(json.batch);
        setForm(formFromBatch(json.batch));
      } catch (e) {
        setError(e.message || "Failed to load batch — check connection.");
      } finally {
        setLoading(false);
      }
    })();
  }, [uid]);

  // Single write path for every edit. Sends only the changed field(s); the
  // backend returns the fresh batch, which we drop straight back into state
  // so the header pill, facts, and form all re-render from the source of truth.
  async function patchBatch(payload, label) {
    setSaving(label);
    setMsg({ text: "", ok: true });
    try {
      const res = await fetch(`${API_BASE}/tracker/batch/${encodeURIComponent(uid)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (!json.success) throw new Error(json.error || "Save failed");
      setBatch(json.batch);
      setForm(formFromBatch(json.batch));
      setPendingStatus(null);
      setMsg({ text: "Saved ✓", ok: true });
      setTimeout(() => setMsg({ text: "", ok: true }), 2500);
    } catch (e) {
      setMsg({ text: e.message || "Save failed", ok: false });
    } finally {
      setSaving("");
    }
  }

  // Open the push modal — but only if a lab is set (GAS rejects a lab-less
  // push, so we catch it here for a clearer message before the round trip).
  function openPush(type) {
    if (!batch?.lab) {
      setMsg({ text: "Assign a testing lab before pushing to testing.", ok: false });
      return;
    }
    setPushForm({ date: "", sampleSize: "", rndType: RND_TYPES[0] });
    setPushType(type);
  }

  async function confirmPush() {
    if (!pushForm.date) { setMsg({ text: "Select a submission date.", ok: false }); return; }
    setPushBusy(true);
    try {
      const res = await fetch(`${API_BASE}/tracker/batch/${encodeURIComponent(uid)}/push-testing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          push_type: pushType,
          date: pushForm.date,
          sample_size: pushForm.sampleSize || null,
          rnd_type: pushType === "RND" ? pushForm.rndType : "Compliance",
        }),
      });
      const json = await res.json();
      if (!json.success) throw new Error(json.error || "Push failed");
      setBatch(json.batch);
      setForm(formFromBatch(json.batch));
      setPushType(null);
      setMsg({ text: `Pushed to testing${json.tabName ? ` — ${json.tabName}` : ""}`, ok: true });
    } catch (e) {
      setMsg({ text: e.message || "Push failed", ok: false });
    } finally {
      setPushBusy(false);
    }
  }

  async function confirmRemove() {
    setPushBusy(true);
    try {
      const res = await fetch(`${API_BASE}/tracker/batch/${encodeURIComponent(uid)}/remove-testing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const json = await res.json();
      if (!json.success) throw new Error(json.error || "Remove failed");
      setBatch(json.batch);
      setForm(formFromBatch(json.batch));
      setShowRemove(false);
      setMsg({ text: "Removed from testing — reverted to In Production", ok: true });
    } catch (e) {
      setMsg({ text: e.message || "Remove failed", ok: false });
    } finally {
      setPushBusy(false);
    }
  }

  if (loading) return (
    <>
      <AppHeader />
      <div className="pd-shell"><div className="pd-loading">Loading batch…</div></div>
    </>
  );

  if (error) return (
    <>
      <AppHeader />
      <div className="pd-shell">
        <button className="pd-back-link" onClick={() => navigate("/")}>← Back to Batches</button>
        <div className="pd-error">{error}</div>
      </div>
    </>
  );

  const b = batch;
  const bprUrl = buildBprUrl(b);

  // One editable numeric/text field (mfg date, final qty, target qty). Each
  // renders a label + input + Save that's disabled until the value changes.
  // key = the form/payload key; the "unchanged" comparison reads the matching
  // batch field so a fresh load never shows a stale enabled Save.
  const editField = (label, key, batchVal, opts = {}) => (
    <div className="bd-field">
      <div className="pd-fact-label">{label}</div>
      <div className="pd-edit-control">
        <input
          className="pd-edit-input" type="text"
          placeholder={opts.placeholder || ""}
          inputMode={opts.numeric ? "decimal" : undefined}
          value={form[key]}
          onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
        />
        <button
          className="pd-edit-save"
          disabled={saving === key || String(form[key]) === String(batchVal ?? "")}
          onClick={() => patchBatch({ [key]: form[key] }, key)}
        >{saving === key ? "…" : "Save"}</button>
      </div>
    </div>
  );

  return (
    <>
      <AppHeader />
      <div className="pd-shell">
        <button className="pd-back-link" onClick={() => navigate("/")}>← Back to Batches</button>

        {/* ── Hero ── */}
        <div className="bd-hero">
          <h1 className="bd-hero-title">{b.item || "—"}</h1>
          <div className="bd-hero-meta">
            <span className="bd-chip">{b.metrcUID || "—"}</span>
            <span className="bd-chip">{b.batchID || "—"}</span>
            <span className="pd-status-pill" style={statusPillStyle(b.status)}>
              <span className="pd-status-dot" style={{ background: statusColor(b.status) }} />
              {b.status || "—"}
            </span>
          </div>
        </div>

        {msg.text && <div className={`bd-flash ${msg.ok ? "ok" : "err"}`}>{msg.text}</div>}

        {/* ── Two-column content ── */}
        <div className="bd-grid">

          {/* LEFT COLUMN */}
          <div className="bd-col">

            {/* Batch Info */}
            <div className="bd-card">
              <div className="bd-card-head">
                <h3>Batch Info</h3>
                <div className="bd-timestamps">
                  <div><span className="bd-ts-label">Created</span><span className="bd-ts-val">{b.createdAt || "—"}</span></div>
                  <div><span className="bd-ts-label">Updated</span><span className="bd-ts-val">{b.lastUpdated || "—"}</span></div>
                </div>
              </div>
              <div className="bd-card-body">
                <div className="bd-fields">
                  <div className="bd-field span-2">
                    <div className="pd-fact-label">Product Name</div>
                    <div className="bd-field-value large">{b.item || "—"}</div>
                  </div>
                  <div className="bd-field">
                    <div className="pd-fact-label">Batch ID</div>
                    <div className="bd-field-value pd-mono">{b.batchID || "—"}</div>
                  </div>
                  <div className="bd-field">
                    <div className="pd-fact-label">Category</div>
                    <div className="bd-field-value">{b.category || "—"}</div>
                  </div>

                  {editField("Mfg / Pkg Date", "mfg_date", b.mfgDate, { placeholder: "mm/dd/yyyy" })}

                  <div className="bd-field">
                    <div className="pd-fact-label">Item Strain</div>
                    <div className="bd-field-value">{b.itemStrain || "—"}</div>
                  </div>

                  {editField("Final Confirmed Qty", "quantity", b.quantity, { numeric: true, placeholder: "e.g. 1150" })}
                  {editField("Target Quantity", "target_qty", b.targetQty, { numeric: true, placeholder: "e.g. 1150" })}

                  <div className="bd-field">
                    <div className="pd-fact-label">Unit of Measure</div>
                    <div className="bd-field-value">{b.uom || "—"}</div>
                  </div>

                  <div className="bd-field">
                    <div className="pd-fact-label">Testing Lab</div>
                    <div className="pd-edit-control">
                      {/* Lab saves on change, mirroring GAS's onchange="updateLab()". */}
                      <select
                        className="pd-edit-input" value={form.lab} disabled={saving === "lab"}
                        onChange={e => { const lab = e.target.value; setForm(f => ({ ...f, lab })); patchBatch({ lab }, "lab"); }}
                      >
                        <option value="">— none —</option>
                        {LAB_OPTIONS.map(l => <option key={l} value={l}>{l}</option>)}
                      </select>
                    </div>
                  </div>

                  <div className="bd-field">
                    <div className="pd-fact-label">Test Date</div>
                    <div className="bd-field-value pd-mono">{b.testDate || "—"}</div>
                  </div>

                  <div className="bd-field span-2">
                    <div className="pd-fact-label">METRC UID</div>
                    <div className="bd-field-value pd-mono" style={{ fontSize: "0.78rem" }}>{b.metrcUID || "—"}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Lab Results — sample IDs editable (direct writes) */}
            <div className="bd-card">
              <div className="bd-card-head"><h3>Lab Results</h3></div>
              <div className="bd-card-body">
                <div className="bd-fields">
                  {editField("R&D Sample ID", "lab_sample_id_rnd", b.labSampleIDRND, { placeholder: "e.g. ICC-260401-59-001" })}
                  {editField("COA Sample ID", "lab_sample_id_coa", b.labSampleIDCOA, { placeholder: "e.g. ICC-260401-59-001" })}
                </div>
                {b.labResultsURL && (
                  <a className="bd-results-link" href={b.labResultsURL} target="_blank" rel="noreferrer">
                    🔗 View Results ↗
                  </a>
                )}
              </div>
            </div>

            {/* MRID Label — beneath Lab Results, only when available (per GAS) */}
            {b.mridLabel && (
              <div className="bd-card">
                <div className="bd-card-head">
                  <h3>MRID Label</h3>
                  <button className="pd-edit-save" onClick={() => navigator.clipboard.writeText(b.mridLabel)}>
                    Copy
                  </button>
                </div>
                <div className="bd-card-body">
                  <div className="bd-label-box pd-mono">{b.mridLabel}</div>
                </div>
              </div>
            )}
          </div>

          {/* RIGHT COLUMN */}
          <div className="bd-col bd-col-right">

            {/* Status */}
            <div className="bd-card bd-card-accent">
              <div className="bd-card-head"><h3>Status</h3></div>
              <div className="bd-card-body">
                {/* Routed through GAS so updateBatchStatus's side effects
                    still run (see tracker.py's _gas_post / setBatchStatus). */}
                <div className="pd-status-selector bd-status-list">
                  {STATUS_OPTIONS.map(s => {
                    const active = (pendingStatus ?? b.status ?? "").toLowerCase() === s.toLowerCase();
                    return (
                      <button
                        key={s} type="button"
                        className={`pd-status-option ${active ? "selected" : ""}`}
                        onClick={() => setPendingStatus(s)}
                      >
                        <span className="pd-status-dot" style={{ background: statusColor(s) }} />
                        {s}
                      </button>
                    );
                  })}
                </div>
                <button
                  className="pd-action-btn primary pd-save-status"
                  disabled={!pendingStatus || pendingStatus === b.status || saving === "status"}
                  onClick={() => patchBatch({ status: pendingStatus }, "status")}
                >
                  {saving === "status" ? "Saving…" : "Save Status"}
                </button>
              </div>
            </div>

            {/* Testing — pushes routed through GAS (serverPushToTestingOrder /
                serverRemoveTestingSubmission write the testing sheet + Distro Log). */}
            <div className="bd-card">
              <div className="bd-card-head"><h3>Testing</h3></div>
              <div className="bd-card-body bd-tiles">
                <button className="bd-action-tile primary" onClick={() => openPush("RND")}>
                  <span className="bd-tile-title">Push R&amp;D Order</span>
                  <span className="bd-tile-desc">Select type + send to testing sheet</span>
                </button>
                <button className="bd-action-tile blue" onClick={() => openPush("COMPLIANCE")}>
                  <span className="bd-tile-title">Push Compliance Order</span>
                  <span className="bd-tile-desc">Full COA — send to testing sheet</span>
                </button>
                {IN_TESTING.has((b.status || "").toLowerCase()) && (
                  <button className="bd-action-tile danger" onClick={() => setShowRemove(true)}>
                    <span className="bd-tile-title">Remove Testing Submission</span>
                    <span className="bd-tile-desc">Reverts to In Production, removes from testing sheet</span>
                  </button>
                )}
              </div>
            </div>

            {/* Documents / actions — Open BPR + folder live here in the
                sidebar (relocatable per design). */}
            <div className="bd-card">
              <div className="bd-card-head"><h3>Documents</h3></div>
              <div className="bd-card-body bd-actions">
                <a className="pd-action-btn primary" href={bprUrl}>📋 Open BPR</a>
                {b.folderURL && (
                  <a className="pd-action-btn" href={b.folderURL} target="_blank" rel="noreferrer">
                    📁 Batch Folder ↗
                  </a>
                )}
                {b.rndPDF && (
                  <a className="pd-action-btn" href={b.rndPDF} target="_blank" rel="noreferrer">
                    R&amp;D PDF ↗
                  </a>
                )}
                <a className="pd-action-btn" href={`${EXTERNAL_LINKS.punchTools}?page=batch&uid=${encodeURIComponent(b.metrcUID)}`}
                   target="_blank" rel="noreferrer">
                  Edit in Legacy GAS ↗
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* ── Push to Testing modal ── */}
        {pushType && (
          <div className="bd-modal-overlay" onClick={() => !pushBusy && setPushType(null)}>
            <div className="bd-modal" onClick={e => e.stopPropagation()}>
              <h3 className="bd-modal-title">
                {pushType === "RND" ? "Push R&D Order" : "Push Compliance Order"}
              </h3>
              <p className="bd-modal-desc">
                Sends this batch to the testing order sheet and updates the Distro Log.
              </p>

              {pushType === "RND" && (
                <div className="bd-modal-field">
                  <label>R&D Test Type *</label>
                  <select
                    className="pd-edit-input"
                    value={pushForm.rndType}
                    onChange={e => setPushForm(f => ({ ...f, rndType: e.target.value }))}
                  >
                    {RND_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              )}

              <div className="bd-modal-field">
                <label>Submission Date *</label>
                <input
                  className="pd-edit-input" type="date"
                  value={pushForm.date}
                  onChange={e => setPushForm(f => ({ ...f, date: e.target.value }))}
                />
              </div>

              <div className="bd-modal-field">
                <label>Sample Size (units to send to lab)</label>
                <input
                  className="pd-edit-input" type="number" min="1" placeholder="e.g. 13"
                  value={pushForm.sampleSize}
                  onChange={e => setPushForm(f => ({ ...f, sampleSize: e.target.value }))}
                />
              </div>

              <div className="bd-modal-preview">
                <div className="bd-modal-preview-label">This creates tab:</div>
                <div className="bd-modal-preview-val">
                  {b.lab && pushForm.date
                    ? `${b.lab} ${formatPreviewDate(pushForm.date)}`
                    : (!b.lab ? "No lab assigned — set a lab first" : "—")}
                </div>
                <div className="bd-modal-preview-sub">Testing Order Sheet + Distro Log updated</div>
              </div>

              <div className="bd-modal-actions">
                <button className="pd-action-btn" disabled={pushBusy} onClick={() => setPushType(null)}>
                  Cancel
                </button>
                <button className="pd-action-btn primary" disabled={pushBusy} onClick={confirmPush}>
                  {pushBusy ? "Pushing…" : "Push to Testing Order"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── Remove Testing modal ── */}
        {showRemove && (
          <div className="bd-modal-overlay" onClick={() => !pushBusy && setShowRemove(false)}>
            <div className="bd-modal" onClick={e => e.stopPropagation()}>
              <h3 className="bd-modal-title">Remove Testing Submission</h3>
              <p className="bd-modal-desc">
                This removes the batch from the testing order sheet and reverts the
                status back to <strong>In Production</strong>.
              </p>
              <div className="bd-modal-actions">
                <button className="pd-action-btn" disabled={pushBusy} onClick={() => setShowRemove(false)}>
                  Cancel
                </button>
                <button className="pd-action-btn danger" disabled={pushBusy} onClick={confirmRemove}>
                  {pushBusy ? "Removing…" : "Remove Submission"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
