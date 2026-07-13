// Dashboard.jsx — Components inventory dashboard
// The Railway-migration payoff page: reads v_component_inventory through
// GET /components/inventory (milliseconds from Postgres) instead of the
// old GAS SpreadsheetApp crawl. Read-only in v1 — creation stays in the
// wash page and future type-specific flows.
import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../App";
import "./Dashboard.css";
import AppHeader from "./AppHeader";

export default function Dashboard() {
  const navigate = useNavigate();
  const [lots, setLots] = useState([]);
  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [invRes, typesRes] = await Promise.all([
          fetch(`${API_BASE}/components/inventory`).then(r => r.json()),
          fetch(`${API_BASE}/components/types`).then(r => r.json()),
        ]);
        setLots(invRes.lots || []);
        setTypes(typesRes.types || []);
      } catch (e) {
        setError("Failed to load inventory — check connection.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // ── Status labels: the registry's status_workflow is the source of
  //    truth for pretty names ("washing" → "Ice Extraction"). Handles both
  //    string arrays and {key,label} arrays. ─────────────────────────────
  const statusLabels = useMemo(() => {
    const map = {};
    types.forEach(t => {
      (t.status_workflow || []).forEach(item => {
        if (typeof item === "object" && item.key) map[`${t.key}:${item.key}`] = item.label || item.key;
        else if (typeof item === "string") map[`${t.key}:${item}`] = item;
      });
    });
    return map;
  }, [types]);

  const typeNames = useMemo(() => {
    const map = {};
    types.forEach(t => { map[t.key] = t.display_name; });
    return map;
  }, [types]);

  function labelFor(lot) {
    return statusLabels[`${lot.component_type}:${lot.status}`] || lot.status;
  }

  // Only offer filter chips for types that actually have lots
  const typesWithLots = useMemo(() => {
    const present = new Set(lots.map(l => l.component_type));
    return types.filter(t => present.has(t.key));
  }, [lots, types]);

  // Statuses present within the current type filter
  const statusesPresent = useMemo(() => {
    const pool = typeFilter === "all" ? lots : lots.filter(l => l.component_type === typeFilter);
    return [...new Set(pool.map(l => l.status))];
  }, [lots, typeFilter]);

  const filtered = useMemo(() => {
    let out = lots;
    if (typeFilter !== "all")   out = out.filter(l => l.component_type === typeFilter);
    if (statusFilter !== "all") out = out.filter(l => l.status === statusFilter);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      out = out.filter(l =>
        (l.lot_code || "").toLowerCase().includes(q) ||
        (l.strain || "").toLowerCase().includes(q) ||
        (l.metrc_uid || "").toLowerCase().includes(q)
      );
    }
    return out;
  }, [lots, typeFilter, statusFilter, search]);

  // Header stat: total available inventory in the current view, by unit
  const totals = useMemo(() => {
    const byUnit = {};
    filtered.forEach(l => {
      const qty = parseFloat(l.current_qty) || 0;
      if (qty > 0) byUnit[l.unit] = (byUnit[l.unit] || 0) + qty;
    });
    return byUnit;
  }, [filtered]);

  function ageDays(createdAt) {
    if (!createdAt) return null;
    return Math.floor((Date.now() - new Date(createdAt).getTime()) / 86400000);
  }

  if (loading) return <div className="dash-shell"><div className="dash-loading">Loading inventory…</div></div>;
  if (error)   return <div className="dash-shell"><div className="dash-error">{error}</div></div>;

  return (
    <>
      <AppHeader />
      <div className="dash-shell">
        <header className="dash-header">
          <div>
            <div className="dash-kicker">BatchD · Punch Tools</div>
            <h1 className="dash-title">Components Inventory</h1>
        </div>
        <div className="dash-totals">
          {Object.entries(totals).map(([unit, qty]) => (
            <div key={unit} className="dash-total-chip">
              <span className="dash-total-num">{qty.toLocaleString(undefined, { maximumFractionDigits: 1 })}</span>
              <span className="dash-total-unit">{unit} on hand</span>
            </div>
          ))}
          <div className="dash-total-chip">
            <span className="dash-total-num">{filtered.length}</span>
            <span className="dash-total-unit">lot{filtered.length !== 1 ? "s" : ""}</span>
          </div>
        </div>
      </header>

      <div className="dash-filters">
        <div className="chip-row">
          <button className={`chip ${typeFilter === "all" ? "chip-on" : ""}`}
                  onClick={() => { setTypeFilter("all"); setStatusFilter("all"); }}>
            All types
          </button>
          {typesWithLots.map(t => (
            <button key={t.key}
                    className={`chip ${typeFilter === t.key ? "chip-on" : ""}`}
                    onClick={() => { setTypeFilter(t.key); setStatusFilter("all"); }}>
              {t.display_name}
            </button>
          ))}
        </div>
        <div className="chip-row">
          <button className={`chip chip-sm ${statusFilter === "all" ? "chip-on" : ""}`}
                  onClick={() => setStatusFilter("all")}>
            Any status
          </button>
          {statusesPresent.map(s => (
            <button key={s}
                    className={`chip chip-sm ${statusFilter === s ? "chip-on" : ""}`}
                    onClick={() => setStatusFilter(s)}>
              {typeFilter !== "all"
                ? (statusLabels[`${typeFilter}:${s}`] || s)
                : s}
            </button>
          ))}
        </div>
        <input className="dash-search" type="text"
               placeholder="Search lot code, strain, or METRC tag…"
               value={search} onChange={e => setSearch(e.target.value)} />
      </div>

      <div className="dash-table-wrap">
        <table className="dash-table">
          <thead>
            <tr>
              <th>Lot Code</th>
              <th>Type</th>
              <th>Status</th>
              <th className="num">On Hand</th>
              <th>Strain</th>
              <th>METRC UID</th>
              <th className="num">Age</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={7} className="dash-empty">No lots match the current filters.</td></tr>
            )}
            {filtered.map(lot => {
              const qty = parseFloat(lot.current_qty) || 0;
              const age = ageDays(lot.created_at);
              return (
                <tr key={lot.id} className="dash-row"
                    onClick={() => navigate(`/components/${encodeURIComponent(lot.lot_code)}`)}>
                  <td className="mono strong">{lot.lot_code}</td>
                  <td>{typeNames[lot.component_type] || lot.component_type}</td>
                  <td><span className={`status-pill st-${lot.status}`}>{labelFor(lot)}</span></td>
                  <td className={`num mono ${qty <= 0 ? "qty-zero" : ""}`}>
                    {qty.toLocaleString(undefined, { maximumFractionDigits: 1 })} {lot.unit}
                  </td>
                  <td>{lot.strain || "—"}</td>
                  <td className="mono dim">{lot.metrc_uid || "—"}</td>
                  <td className="num dim">{age !== null ? `${age}d` : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
    </>
  );
}