// PunchDashboard.jsx — the real Punch Tools batch dashboard.
// Port of GAS's index.html / serverGetDashboard, landing at "/" now that
// login is wired up. Styled to match the original GAS look on purpose —
// see PunchDashboard.css — rather than the newer Components/LotDetail
// design system, so floor staff see something familiar.
//
// Read-only in this first pass — status changes, batch creation, and UID
// import still live on the GAS app until those endpoints get their own
// migration pass.
import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../App";
import "./PunchDashboard.css";
import AppHeader from "./AppHeader";

// ── Finished goods vs. everything else ─────────────────────────────────
// Two different reasons a row shouldn't show up on the Batches dashboard:
//
// 1. COMPONENT_STATUSES — rows whose real operational home is now the
//    Components dashboard (Postgres — sessions, ledger, allocations).
//    "ice extraction" is today's live value; "components" is added
//    pre-emptively for when that status gets renamed on the Sheet side
//    (per plan: all METRC-source-material rows converge on one
//    "Components" status so nothing new needs to change here when that
//    rename happens — just delete "ice extraction" once the migration
//    is done and confirmed).
//
// 2. FINISHED_STATUSES — rows that are done and already shipped. These
//    should already be excluded server-side (sheets_client.INACTIVE_STATUSES),
//    but filtering them here too is cheap insurance against any mismatch
//    between the two lists — redundant-safe, never wrong to exclude twice.
//    NOTE: matches Config.gs's spelling exactly ("Distru", not "Distro").
//    Both statuses are now hidden — "passed but not avail" was originally
//    kept visible (it used to mean "still needs to move to the menu"),
//    but that's been reversed: skip it here too.
const COMPONENT_STATUSES = new Set(["ice extraction", "components"]);
const FINISHED_STATUSES = new Set(["avail in distru/on menu", "passed but not avail in distru"]);

function isHiddenFromBatches(batch) {
  const s = (batch.status || "").toLowerCase().trim();
  if (COMPONENT_STATUSES.has(s)) return true;
  if (FINISHED_STATUSES.has(s)) return true;
  // Rows like "@conversion" (bulk METRC-source conversions, e.g. Nano THC
  // Bulk) aren't real finished-good batches either — they don't have a
  // status yet to key off, so this catches them by batchID shape instead.
  // Once these get folded into the "Components" status this becomes
  // redundant with the check above, but doesn't hurt to keep both.
  if ((batch.batchID || "").trim().startsWith("@")) return true;
  return false;
}

const STAT_LABELS = {
  inProduction:    "In Production",
  needLabels:      "Need Labels",
  readyForTesting: "Ready for Testing",
  awaitingResults: "Awaiting Results",
};

// Mirrors Config.gs's STAT_GROUPS exactly (lowercased for matching).
// Needed here to recompute counts client-side after the component/
// finished rows are filtered out — the backend's `stats` object was
// tallied over ALL sheet rows, so it still includes those in its counts.
// If Config.gs's groupings change, update here too — there's no single
// shared source of truth between GAS and this app yet.
const STAT_GROUPS = {
  inProduction: [
    "in production", "ready for packaging", "packaging complete",
    "submitted for rnd", "passed rnd", "remake",
  ],
  needLabels: ["need labels", "labels made"],
  readyForTesting: ["ready for testing"],
  awaitingResults: ["submitted for compliance", "delayed in testing", "testing cancelled"],
};

// Status family → dot color, driven off the same STAT_GROUPS above so
// the table's pill colors stay in sync with the stat-card buckets rather
// than drifting via a second, separately-maintained list of strings.
export function statusDotClass(status) {
  const s = (status || "").toLowerCase().trim();
  if (STAT_GROUPS.inProduction.includes(s)) return "dot-orange";
  if (STAT_GROUPS.needLabels.includes(s)) return "dot-red";
  if (STAT_GROUPS.readyForTesting.includes(s)) return "dot-blue";
  if (STAT_GROUPS.awaitingResults.includes(s)) return "dot-purple";
  if (s === "failed") return "dot-red";
  return "dot-gray"; // complete/archived/avail-in-distro and anything unmapped
}

export default function PunchDashboard() {
  const navigate = useNavigate();
  const [data, setData]             = useState(null); // full /tracker/dashboard payload
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState("");
  const [statFilter, setStatFilter] = useState(null); // toggled stat card key, or null
  const [statusFilter, setStatusFilter] = useState("all");
  const [labFilter, setLabFilter]   = useState("all");
  const [search, setSearch]         = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/tracker/dashboard`);
      const json = await res.json();
      if (!json.success) throw new Error(json.error || "Dashboard load failed");
      setData(json);
    } catch (e) {
      setError(e.message || "Failed to load dashboard — check connection.");
    } finally {
      setLoading(false);
    }
  }

  // Finished goods only — everything isHiddenFromBatches() flags (in-
  // progress components, already-distributed items, conversion rows)
  // belongs on the Components dashboard or nowhere active at all.
  const finishedGoods = useMemo(
    () => (data?.batches || []).filter(b => !isHiddenFromBatches(b)),
    [data]
  );

  const failedBatches = data?.failedBatches || [];

  // Recomputed from the filtered list rather than trusting the backend's
  // `stats` object, since that was tallied before components were excluded.
  const stats = useMemo(() => {
    const out = { inProduction: 0, needLabels: 0, readyForTesting: 0, awaitingResults: 0 };
    finishedGoods.forEach(b => {
      const s = (b.status || "").toLowerCase().trim();
      for (const [key, group] of Object.entries(STAT_GROUPS)) {
        if (group.includes(s)) { out[key]++; break; }
      }
    });
    return out;
  }, [finishedGoods]);

  const filtered = useMemo(() => {
    let out = finishedGoods;
    if (statFilter && STAT_GROUPS[statFilter]) {
      out = out.filter(b => STAT_GROUPS[statFilter].includes((b.status || "").toLowerCase().trim()));
    }
    if (statusFilter !== "all") {
      out = out.filter(b => b.status === statusFilter);
    }
    if (labFilter !== "all") {
      out = out.filter(b => b.lab === labFilter);
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      out = out.filter(b =>
        (b.batchID || "").toLowerCase().includes(q) ||
        (b.item || "").toLowerCase().includes(q) ||
        (b.metrcUID || "").toLowerCase().includes(q)
      );
    }
    return out;
  }, [finishedGoods, statFilter, statusFilter, labFilter, search]);

  if (loading) return (
    <>
      <AppHeader />
      <div className="pd-shell"><div className="pd-loading">Loading batches…</div></div>
    </>
  );

  if (error) return (
    <>
      <AppHeader />
      <div className="pd-shell">
        <div className="pd-error">{error}</div>
        <button className="pd-select" style={{ marginTop: 12, cursor: "pointer" }} onClick={load}>Retry</button>
      </div>
    </>
  );

  return (
    <>
      <AppHeader />
      <div className="pd-shell">
        <div className="pd-header">
          <div className="pd-kicker">BatchD · Punch Tools</div>
          <h1 className="pd-title">Batch Dashboard</h1>
          <div className="pd-subtitle">UID Tracker — Punch Edibles &amp; Extracts</div>
        </div>

        <div className="pd-stats">
          {Object.entries(STAT_LABELS).map(([key, label]) => (
            <button
              key={key}
              className={`pd-stat-card ${statFilter === key ? "active" : ""}`}
              onClick={() => setStatFilter(statFilter === key ? null : key)}
            >
              <div className="pd-stat-label">{label}</div>
              <div className={`pd-stat-value ${key}`}>{stats[key]}</div>
            </button>
          ))}
          <button
            className={`pd-stat-card ${statFilter === "unassignedUIDs" ? "active" : ""}`}
            disabled // unassigned UIDs aren't in the batches array to filter by — count only, for now
            style={{ cursor: "default", opacity: 0.9 }}
          >
            <div className="pd-stat-label">Unassigned UIDs</div>
            <div className="pd-stat-value unassignedUIDs">{data?.stats?.unassignedUIDs ?? 0}</div>
          </button>
        </div>

        {failedBatches.length > 0 && (
          <div className="pd-failed-banner">
            <span className="pd-failed-icon">⚠️</span>
            <div className="pd-failed-text">
              <span className="pd-failed-title">Failed Batches</span>
              {failedBatches.map(b => `${b.batchID || b.metrcUID} — ${b.item}`).join(" · ")}
            </div>
            <div className="pd-failed-count">{failedBatches.length}</div>
          </div>
        )}

        <div className="pd-filters">
          <input
            className="pd-search"
            type="text"
            placeholder="Search by product, batch ID, or METRC tag…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <select className="pd-select" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="all">All Statuses</option>
            {(data?.statuses || []).map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select className="pd-select" value={labFilter} onChange={e => setLabFilter(e.target.value)}>
            <option value="all">All Labs</option>
            {(data?.labs || []).map(l => <option key={l} value={l}>{l}</option>)}
          </select>
        </div>

        <div className="pd-table-wrap">
          <table className="pd-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Batch ID</th>
                <th>Lab</th>
                <th>Mfg Date</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={6} className="pd-empty">No batches match the current filters.</td></tr>
              )}
              {filtered.map(b => (
                <tr
                  key={b.metrcUID || b.batchID}
                  className="pd-row"
                  style={{ cursor: "pointer" }}
                  onClick={() => navigate(`/batch/${encodeURIComponent(b.metrcUID)}`)}
                >
                  <td>
                    <span className="pd-product">{b.item || "—"}</span>
                    {b.metrcUID && <span className="pd-uid-sub">{b.metrcUID}</span>}
                  </td>
                  <td className="pd-mono">{b.batchID || "—"}</td>
                  <td className="pd-dim">{b.lab || "—"}</td>
                  <td className="pd-dim">{b.mfgDate || "—"}</td>
                  <td>
                    <span className={`pd-status-pill ${statusDotClass(b.status)}`}>
                      <span className="pd-status-dot" />
                      {b.status || "—"}
                    </span>
                  </td>
                  <td className="pd-arrow">→</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
