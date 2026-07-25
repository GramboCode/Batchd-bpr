// PunchDashboard.jsx — the actual Punch Tools batch dashboard.
// Port of GAS's index.html / serverGetDashboard, landing at "/" now that
// login is wired up. Read-only in this first pass — status changes,
// batch creation, and UID import stay on the GAS app until those
// endpoints get their own migration pass.
import { useState, useEffect, useMemo } from "react";
import { API_BASE } from "../App";
import "./Dashboard.css"; // reuse the shared shell/table/chip/status-pill styles
import AppHeader from "./AppHeader";

// Same five buckets serverGetDashboard grouped batches into — used here
// only for display labels; the counting itself happens on the backend.
const STAT_LABELS = {
  inProduction:    "In Production",
  needLabels:      "Need Labels",
  readyForTesting: "Ready for Testing",
  awaitingResults: "Awaiting Results",
  unassignedUIDs:  "Unassigned UIDs",
};

export default function PunchDashboard() {
  const [data, setData]           = useState(null); // full /tracker/dashboard payload
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState("");
  const [statFilter, setStatFilter] = useState(null); // which stat card is toggled on, or null
  const [search, setSearch]       = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/tracker/dashboard`);
      const json = await res.json();
      // Backend mirrors the GAS convention: {success:false, error} instead
      // of a raw 500, so a non-network failure still needs this check.
      if (!json.success) throw new Error(json.error || "Dashboard load failed");
      setData(json);
    } catch (e) {
      setError(e.message || "Failed to load dashboard — check connection.");
    } finally {
      setLoading(false);
    }
  }

  const batches = data?.batches || [];
  const stats   = data?.stats   || {};
  const failedBatches = data?.failedBatches || [];

  // Which status strings belong to the currently-toggled stat card, so
  // clicking "Need Labels" filters the table to just those rows. Mirrors
  // the same grouping the backend used to produce the counts — kept in
  // sync manually since the groupings themselves live server-side.
  const STAT_GROUPS = {
    inProduction:    ["in production", "washing", "drying", "sifting"],
    needLabels:      ["need labels", "ready for labels"],
    readyForTesting: ["ready for testing"],
    awaitingResults: ["awaiting results", "testing"],
  };

  const filtered = useMemo(() => {
    let out = batches;
    if (statFilter && STAT_GROUPS[statFilter]) {
      const group = STAT_GROUPS[statFilter];
      out = out.filter(b => group.includes((b.status || "").toLowerCase().trim()));
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batches, statFilter, search]);

  if (loading) return (
    <>
      <AppHeader />
      <div className="dash-shell"><div className="dash-loading">Loading batches…</div></div>
    </>
  );

  if (error) return (
    <>
      <AppHeader />
      <div className="dash-shell">
        <div className="dash-error">{error}</div>
        <button className="chip" style={{ marginTop: 12 }} onClick={load}>Retry</button>
      </div>
    </>
  );

  return (
    <>
      <AppHeader />
      <div className="dash-shell">
        <header className="dash-header">
          <div>
            <div className="dash-kicker">BatchD · Punch Tools</div>
            <h1 className="dash-title">Batches</h1>
          </div>
          <div className="dash-totals">
            <div className="dash-total-chip">
              <span className="dash-total-num">{batches.length}</span>
              <span className="dash-total-unit">active</span>
            </div>
          </div>
        </header>

        {/* ── Failed batch banner — only appears when there's something to see ── */}
        {failedBatches.length > 0 && (
          <div style={{
            background: "#FEE2E2", border: "1.5px solid #B91C1C", borderRadius: 10,
            padding: "14px 18px", marginBottom: 16,
          }}>
            <div style={{
              fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 800,
              fontSize: "0.9rem", textTransform: "uppercase", color: "#B91C1C",
              letterSpacing: "0.04em", marginBottom: 6,
            }}>
              {failedBatches.length} Failed Batch{failedBatches.length !== 1 ? "es" : ""}
            </div>
            <div style={{ fontSize: "0.84rem", color: "#7F1D1D" }}>
              {failedBatches.map(b => `${b.batchID || b.metrcUID} (${b.item})`).join(" · ")}
            </div>
          </div>
        )}

        {/* ── Stat cards — click to filter the table, click again to clear ── */}
        <div className="dash-filters">
          <div className="chip-row">
            <button className={`chip ${!statFilter ? "chip-on" : ""}`}
                    onClick={() => setStatFilter(null)}>
              All ({batches.length})
            </button>
            {Object.entries(STAT_LABELS).map(([key, label]) => (
              <button key={key}
                      className={`chip ${statFilter === key ? "chip-on" : ""}`}
                      onClick={() => setStatFilter(statFilter === key ? null : key)}>
                {label} ({stats[key] ?? 0})
              </button>
            ))}
          </div>
          <input className="dash-search" type="text"
                 placeholder="Search batch ID, product, or METRC tag…"
                 value={search} onChange={e => setSearch(e.target.value)} />
        </div>

        <div className="dash-table-wrap">
          <table className="dash-table">
            <thead>
              <tr>
                <th>Batch ID</th>
                <th>Product</th>
                <th>Category</th>
                <th>Status</th>
                <th>Mfg Date</th>
                <th>Lab</th>
                <th>Test Date</th>
                <th>METRC UID</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={8} className="dash-empty">No batches match the current filters.</td></tr>
              )}
              {filtered.map(b => (
                <tr key={b.metrcUID || b.batchID}>
                  <td className="mono strong">{b.batchID || "—"}</td>
                  <td>{b.item || "—"}</td>
                  <td>{b.category || "—"}</td>
                  <td><span className="status-pill">{b.status || "—"}</span></td>
                  <td className="dim">{b.mfgDate || "—"}</td>
                  <td className="dim">{b.lab || "—"}</td>
                  <td className="dim">{b.testDate || "—"}</td>
                  <td className="mono dim">{b.metrcUID || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
