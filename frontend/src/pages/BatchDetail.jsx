// BatchDetail.jsx — single batch view, read-only for now.
// Port of GAS's batch.html / serverGetBatch. Status changes, field edits
// (quantity, retail ID made, etc.) stay on the GAS app until tracker.py
// grows write endpoints — this first pass proves the read path only,
// same phased approach as the dashboard itself.
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { API_BASE } from "../App";
import "./PunchDashboard.css";
import AppHeader, { EXTERNAL_LINKS } from "./AppHeader";
import { statusDotClass } from "./PunchDashboard";

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

export default function BatchDetail() {
  const { uid } = useParams();
  const navigate = useNavigate();
  const [batch, setBatch] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(`${API_BASE}/tracker/batch/${encodeURIComponent(uid)}`);
        const json = await res.json();
        if (!json.success) throw new Error(json.error || "Batch not found");
        setBatch(json.batch);
      } catch (e) {
        setError(e.message || "Failed to load batch — check connection.");
      } finally {
        setLoading(false);
      }
    })();
  }, [uid]);

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
            <span className={`pd-status-pill ${statusDotClass(b.status)}`}>
              <span className="pd-status-dot" />
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
        <div className="pd-readonly-note">
          Status changes, quantity, and other field edits still happen on the Legacy GAS Dashboard for now.
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
          <div className="pd-fact">
            <div className="pd-fact-label">Mfg Date</div>
            <div className="pd-fact-value">{b.mfgDate || "—"}</div>
          </div>
          <div className="pd-fact">
            <div className="pd-fact-label">Quantity</div>
            <div className="pd-fact-value">{b.quantity ? `${b.quantity} ${b.uom || ""}` : "—"}</div>
          </div>
          <div className="pd-fact">
            <div className="pd-fact-label">Target Quantity</div>
            <div className="pd-fact-value">{b.targetQty ? `${b.targetQty} ${b.uom || ""}` : "—"}</div>
          </div>
          <div className="pd-fact">
            <div className="pd-fact-label">Lab</div>
            <div className="pd-fact-value">{b.lab || "—"}</div>
          </div>
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
