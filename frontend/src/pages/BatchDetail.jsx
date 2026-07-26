// BatchDetail.jsx — single batch view. Port of GAS's batch.html.
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

// Seed the editable-field form from a loaded batch. One place so the load
// effect and every post-save refresh stay in sync.
function formFromBatch(b) {
  return {
    target_qty: b.targetQty ?? "",
    quantity:   b.quantity ?? "",
    mfg_date:   b.mfgDate ?? "",
    lab:        b.lab ?? "",
  };
}

export default function BatchDetail() {
  const { uid } = useParams();
  const navigate = useNavigate();
  const [batch, setBatch] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // ── Edit state ──
  const [form, setForm] = useState({ target_qty: "", quantity: "", mfg_date: "", lab: "" });
  const [saving, setSaving] = useState("");        // which field is mid-save ("status", "lab", …)
  const [msg, setMsg] = useState({ text: "", ok: true }); // transient save feedback
  const [pendingStatus, setPendingStatus] = useState(null); // selected-but-unsaved status

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

  return (
    <>
      <AppHeader />
      <div className="pd-shell">
        <button className="pd-back-link" onClick={() => navigate("/")}>← Back to Batches</button>

        <div className="pd-detail-header">
          <div className="pd-kicker">{b.category || "—"}</div>
          <h1 className="pd-detail-title">{b.item || "—"}</h1>
          <div className="pd-detail-sub">
            <span className="pd-mono">{b.batchID || "—"}</span>
            <span className="pd-status-pill" style={statusPillStyle(b.status)}>
              <span className="pd-status-dot" style={{ background: statusColor(b.status) }} />
              {b.status || "—"}
            </span>
          </div>
        </div>

        <div className="pd-actions">
          <a className="pd-action-btn primary" href={bprUrl}>
            Open BPR
          </a>
          {/* folderURL is the one that matters — it's where all of this
              batch's actual records live (COA PDFs, labels, batch record).
              batchSheetURL was the old pre-folder-system approach, kept
              around for a while for backward compat but now confirmed
              dead — removed from the sheet's active columns entirely to
              free up space, so there's nothing to conditionally render here anymore. */}
          {b.folderURL && (
            <a className="pd-action-btn" href={b.folderURL} target="_blank" rel="noreferrer">
              📁 Batch Folder ↗
            </a>
          )}
          {b.labResultsURL && (
            <a className="pd-action-btn" href={b.labResultsURL} target="_blank" rel="noreferrer">
              Lab Results ↗
            </a>
          )}
          {b.rndPDF && (
            <a className="pd-action-btn" href={b.rndPDF} target="_blank" rel="noreferrer">
              R&amp;D PDF ↗
            </a>
          )}
          {/* Query param guessed from the wash link's ?page=wash pattern —
              unconfirmed against the live deployment. If this 404s or lands
              on the bare dashboard instead of this batch, check what param
              batch.html actually reads (BATCH_UID is hardcoded via template
              substitution in the .gs-served HTML, not obviously a URL param —
              worth checking doGet()'s routing before trusting this link). */}
          <a className="pd-action-btn" href={`${EXTERNAL_LINKS.punchTools}?page=batch&uid=${encodeURIComponent(b.metrcUID)}`}
             target="_blank" rel="noreferrer">
            Edit in Legacy GAS Dashboard ↗
          </a>
        </div>
        {/* ── Editable batch info — writes back to UID_TRACKER ── */}
        <div className="pd-edit-card">
          <div className="pd-edit-card-head">
            <span>Batch Info</span>
            {msg.text && (
              <span className={`pd-save-msg ${msg.ok ? "ok" : "err"}`}>{msg.text}</span>
            )}
          </div>
          <div className="pd-edit-grid">
            <div className="pd-edit-field">
              <label className="pd-fact-label">Mfg / Pkg Date</label>
              <div className="pd-edit-control">
                <input
                  className="pd-edit-input" type="text" placeholder="mm/dd/yyyy"
                  value={form.mfg_date}
                  onChange={e => setForm(f => ({ ...f, mfg_date: e.target.value }))}
                />
                <button
                  className="pd-edit-save"
                  disabled={saving === "mfg_date" || form.mfg_date === (b.mfgDate ?? "")}
                  onClick={() => patchBatch({ mfg_date: form.mfg_date }, "mfg_date")}
                >{saving === "mfg_date" ? "…" : "Save"}</button>
              </div>
            </div>

            <div className="pd-edit-field">
              <label className="pd-fact-label">Final Confirmed Qty</label>
              <div className="pd-edit-control">
                <input
                  className="pd-edit-input" type="text" inputMode="decimal"
                  value={form.quantity}
                  onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
                />
                <button
                  className="pd-edit-save"
                  disabled={saving === "quantity" || String(form.quantity) === String(b.quantity ?? "")}
                  onClick={() => patchBatch({ quantity: form.quantity }, "quantity")}
                >{saving === "quantity" ? "…" : "Save"}</button>
              </div>
            </div>

            <div className="pd-edit-field">
              <label className="pd-fact-label">Target Quantity</label>
              <div className="pd-edit-control">
                <input
                  className="pd-edit-input" type="text" inputMode="decimal"
                  value={form.target_qty}
                  onChange={e => setForm(f => ({ ...f, target_qty: e.target.value }))}
                />
                <button
                  className="pd-edit-save"
                  disabled={saving === "target_qty" || String(form.target_qty) === String(b.targetQty ?? "")}
                  onClick={() => patchBatch({ target_qty: form.target_qty }, "target_qty")}
                >{saving === "target_qty" ? "…" : "Save"}</button>
              </div>
            </div>

            <div className="pd-edit-field">
              <label className="pd-fact-label">Testing Lab</label>
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
          </div>
        </div>

        {/* ── Status selector — routed through GAS so updateBatchStatus's
            side effects still run (see tracker.py _gas_set_batch_status). ── */}
        <div className="pd-edit-card">
          <div className="pd-edit-card-head"><span>Status</span></div>
          <div className="pd-status-selector">
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

        <div className="pd-facts">
          <div className="pd-fact">
            <div className="pd-fact-label">METRC UID</div>
            <div className="pd-fact-value pd-mono" style={{ fontSize: "0.78rem" }}>{b.metrcUID || "—"}</div>
          </div>
          <div className="pd-fact">
            <div className="pd-fact-label">Strain</div>
            <div className="pd-fact-value">{b.itemStrain || "—"}</div>
          </div>
          {/* Mfg Date, Quantity, Target Quantity, and Lab moved to the
              editable Batch Info card above — kept out of this read-only grid
              to avoid showing each value twice. */}
          <div className="pd-fact">
            <div className="pd-fact-label">Test Date</div>
            <div className="pd-fact-value">{b.testDate || "—"}</div>
          </div>
          <div className="pd-fact">
            <div className="pd-fact-label">Lab Sample ID (R&amp;D)</div>
            <div className="pd-fact-value">{b.labSampleIDRND || "—"}</div>
          </div>
          <div className="pd-fact">
            <div className="pd-fact-label">Lab Sample ID (COA)</div>
            <div className="pd-fact-value">{b.labSampleIDCOA || "—"}</div>
          </div>
          <div className="pd-fact">
            <div className="pd-fact-label">Retail ID Made</div>
            <div className="pd-fact-value">{b.retailIDMade ? "Yes" : "No"}</div>
          </div>
          <div className="pd-fact">
            <div className="pd-fact-label">METRC Synced</div>
            <div className="pd-fact-value">{b.metrcSynced ? "Yes" : "No"}</div>
          </div>
          <div className="pd-fact">
            <div className="pd-fact-label">Created</div>
            <div className="pd-fact-value">{b.createdAt || "—"}</div>
          </div>
          <div className="pd-fact">
            <div className="pd-fact-label">Last Updated</div>
            <div className="pd-fact-value">{b.lastUpdated || "—"}</div>
          </div>
        </div>

        {b.mridLabel && (
          <div className="pd-fact" style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <div className="pd-fact-label">MRID Label</div>
              <button
                className="pd-action-btn"
                style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                onClick={() => navigator.clipboard.writeText(b.mridLabel)}
              >
                Copy
              </button>
            </div>
            <div className="pd-mono" style={{ fontSize: "0.78rem", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
              {b.mridLabel}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
