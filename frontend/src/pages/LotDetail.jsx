// LotDetail.jsx — single component lot: record, inputs, and the ledger.
// The bank-statement view: every gram in and out as an immutable row,
// with a running balance — the audit trail made visible.
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { API_BASE } from "../App";
import "./Dashboard.css";

const TXN_LABELS = {
  production:    { label: "Production",    sign: "+" },
  receipt:       { label: "Receipt",       sign: "+" },
  consumption:   { label: "Consumption",   sign: "−" },
  waste:         { label: "Waste",         sign: "−" },
  adjustment:    { label: "Adjustment",    sign: "±" },
  metrc_package: { label: "METRC Package", sign: "−" },
};

export default function LotDetail() {
  const { lotCode } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/components/${encodeURIComponent(lotCode)}`);
        if (!res.ok) throw new Error(res.status === 404 ? "Lot not found" : "Failed to load lot");
        setData(await res.json());
      } catch (e) {
        setError(e.message);
      }
    })();
  }, [lotCode]);

  if (error) return (
    <div className="dash-shell">
      <button className="chip" onClick={() => navigate("/")}>← Back to inventory</button>
      <div className="dash-error">{error}</div>
    </div>
  );
  if (!data) return <div className="dash-shell"><div className="dash-loading">Loading lot…</div></div>;

  const { lot, inputs, transactions, current_qty } = data;
  const td = lot.type_data || {};

  // Running balance, oldest → newest
  let running = 0;
  const ledger = (transactions || []).map(t => {
    running += parseFloat(t.qty_delta) || 0;
    return { ...t, balance: running };
  });

  function fmtDate(ts) {
    return ts ? new Date(ts).toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit"
    }) : "—";
  }

  return (
    <>
      <AppHeader />
      <div className="dash-shell">
        <button className="chip" onClick={() => navigate("/")}>← Back to inventory</button>

      <header className="dash-header" style={{ marginTop: 14 }}>
        <div>
          <div className="dash-kicker">{lot.component_type}</div>
          <h1 className="dash-title mono">{lot.lot_code}</h1>
          <div className="lot-sub">
            {lot.strain || "—"} · <span className={`status-pill st-${lot.status}`}>{lot.status}</span>
            {lot.metrc_uid && <span className="dim"> · METRC {lot.metrc_uid}</span>}
          </div>
        </div>
        <div className="dash-totals">
          <div className="dash-total-chip">
            <span className="dash-total-num">
              {(parseFloat(current_qty) || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })}
            </span>
            <span className="dash-total-unit">{lot.unit} on hand</span>
          </div>
        </div>
      </header>

      <div className="lot-facts">
        {lot.storage_location && <div className="fact"><span>Storage</span>{lot.storage_location}</div>}
        {td.wet_weight_g != null && <div className="fact"><span>Wet in</span>{Number(td.wet_weight_g).toLocaleString()} g</div>}
        {td.dry_weight_g != null && <div className="fact"><span>Dry</span>{Number(td.dry_weight_g).toLocaleString()} g</div>}
        {td.sift_weight_g != null && <div className="fact"><span>Sift yield</span>{Number(td.sift_weight_g).toLocaleString()} g</div>}
        {td.yield_pct != null && <div className="fact"><span>Yield</span>{td.yield_pct}%</div>}
        {lot.supplier && <div className="fact"><span>Supplier</span>{lot.supplier}</div>}
        {lot.manifest_number && <div className="fact"><span>Manifest</span>{lot.manifest_number}</div>}
        <div className="fact"><span>Created</span>{fmtDate(lot.created_at)}</div>
        {lot.sheet_url && (
          <a className="fact fact-link" href={lot.sheet_url} target="_blank" rel="noreferrer">
            <span>BPR Sheet</span>Open ↗
          </a>
        )}
      </div>

      {inputs?.length > 0 && (
        <section className="lot-section">
          <h2 className="lot-h2">Source Materials</h2>
          <table className="dash-table">
            <thead><tr><th>Fresh Frozen UID</th><th>Strain</th><th className="num">Weight In</th></tr></thead>
            <tbody>
              {inputs.map(i => (
                <tr key={i.id}>
                  <td className="mono">{i.fresh_frozen_uid}</td>
                  <td>{i.strain_name || "—"}</td>
                  <td className="num mono">{i.input_weight_g != null ? `${Number(i.input_weight_g).toLocaleString()} g` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="lot-section">
        <h2 className="lot-h2">Transaction Ledger</h2>
        {ledger.length === 0 ? (
          <div className="dash-empty" style={{ padding: "14px 4px" }}>
            No transactions yet — inventory is born at the sift weigh-in (or receipt for 3rd-party lots).
          </div>
        ) : (
          <table className="dash-table">
            <thead>
              <tr>
                <th>When</th><th>Type</th><th className="num">Δ Qty</th>
                <th className="num">Balance</th><th>Reference</th><th>Note</th><th>By</th>
              </tr>
            </thead>
            <tbody>
              {ledger.map(t => {
                const delta = parseFloat(t.qty_delta) || 0;
                const meta = TXN_LABELS[t.txn_type] || { label: t.txn_type };
                return (
                  <tr key={t.id}>
                    <td className="dim">{fmtDate(t.created_at)}</td>
                    <td><span className={`txn-pill txn-${t.txn_type}`}>{meta.label}</span></td>
                    <td className={`num mono ${delta < 0 ? "delta-neg" : "delta-pos"}`}>
                      {delta > 0 ? "+" : ""}{delta.toLocaleString(undefined, { maximumFractionDigits: 2 })} {t.unit}
                    </td>
                    <td className="num mono strong">{t.balance.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                    <td className="dim">{t.reference_type ? `${t.reference_type}: ${t.reference_id || ""}` : "—"}</td>
                    <td className="dim">{t.note || "—"}</td>
                    <td className="dim">{t.performed_by || "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
    </>
  );
}
