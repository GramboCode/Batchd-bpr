// EquipmentSanitationPanel.jsx — Section 4 (equipment check-in) + Section 5
// (sanitation log) entry for the CELL-MAPPED standardized BPRs.
//
// The non-wash counterpart to SanitationLogWash: same per-row "Now"-button flow
// and §17210(c) validation, but the row labels come from bprSectionRows.js
// (per product family) and it posts to the cell-map endpoints:
//   Section 4 → POST /bpr/{uid}/equipment    (EQUIP{n}_CHECKEDBY / _TIME)
//   Section 5 → POST /bpr/{uid}/sanitation    (SAN{n}_*)
//
// Renders NOTHING for families with no config entry (wash / session / unmapped),
// so it's safe to drop into every BPRForm unconditionally.
//
// Props:
//   uid          — BPR uid / batch id
//   apiBase      — API_BASE from App
//   family       — product_family (keys bprSectionRows.js)
//   operatorName — prefills Checked By / Cleaned By (editable per row)

import { useState } from "react";
import { BPR_SECTION_ROWS } from "../lib/bprSectionRows";
import useEmployeeName from "../hooks/useEmployeeName";

function nowHHMM() {
  const d = new Date();
  return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = typeof data.detail === "string" ? data.detail : data.detail?.message || "Submission failed";
    throw new Error(msg);
  }
  return data;
}

// ── Section 4 — Equipment Check-In ───────────────────────────────────────────
function EquipmentBlock({ uid, apiBase, rows, operatorName }) {
  const [entries, setEntries] = useState(rows.map(() => ({ checked_by: "", time: "" })));
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const update = (i, field, value) => {
    setEntries((prev) => prev.map((e, idx) => (idx === i ? { ...e, [field]: value } : e)));
    setResult(null);
  };

  const touched = entries.filter((e) => e.checked_by);
  const canSubmit = touched.length > 0 && !submitting;

  const submit = async () => {
    setSubmitting(true);
    setResult(null);
    try {
      const payload = {
        entries: entries
          .map((e, i) => ({ row: rows[i].row, checked_by: e.checked_by, time: e.time || nowHHMM() }))
          .filter((e) => e.checked_by),
      };
      const data = await postJSON(`${apiBase}/bpr/${encodeURIComponent(uid)}/equipment`, payload);
      setResult({ ok: true, message: `${data.rows_written} item(s) checked in on the BPR sheet` });
    } catch (err) {
      setResult({ ok: false, message: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={hint}>
        §17221: confirm each equipment item is present and clean before the run. Enter
        your initials and the time on every item you verified.
      </div>
      {rows.map((eq, i) => (
        <div key={eq.row} style={{ ...rowBox, background: entries[i].checked_by ? "#fff" : "#FAFBFD" }}>
          <strong style={{ fontSize: 14, flex: "1 1 220px" }}>{eq.row}. {eq.name}</strong>
          <label style={lbl}>Checked By
            <input style={inp} value={entries[i].checked_by}
              onChange={(ev) => update(i, "checked_by", ev.target.value)}
              placeholder={operatorName || "Initials"}
              onFocus={() => { if (!entries[i].checked_by && operatorName) update(i, "checked_by", operatorName); }} />
          </label>
          <label style={lbl}>Time
            <div style={{ display: "flex", gap: 4 }}>
              <input style={inp} value={entries[i].time} onChange={(ev) => update(i, "time", ev.target.value)} placeholder="HH:MM" />
              <button type="button" style={nowBtn} onClick={() => update(i, "time", nowHHMM())}>Now</button>
            </div>
          </label>
        </div>
      ))}
      <SubmitRow label={`Submit Equipment Check-In (${touched.length})`} canSubmit={canSubmit} submitting={submitting} onClick={submit} result={result} />
    </div>
  );
}

// ── Section 5 — Sanitation Log ───────────────────────────────────────────────
const emptySan = () => ({ date: new Date().toLocaleDateString("en-US"), clean_start: "", clean_end: "", ppm: "", strips_used: "", passed: "", cleaned_by: "", dry_before_use: "" });
const sanTouched = (e) => !!(e.clean_start || e.clean_end || e.ppm || e.passed || e.cleaned_by || e.dry_before_use || e.strips_used);
const sanComplete = (e) => !!(e.date && e.clean_start && e.clean_end && e.cleaned_by);

function SanitationBlock({ uid, apiBase, rows, operatorName }) {
  const [entries, setEntries] = useState(rows.map(() => emptySan()));
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const update = (i, field, value) => {
    setEntries((prev) => prev.map((e, idx) => (idx === i ? { ...e, [field]: value } : e)));
    setResult(null);
  };

  const touched = entries.filter(sanTouched);
  const incomplete = entries.map((e, i) => (sanTouched(e) && !sanComplete(e) ? rows[i].row : null)).filter(Boolean);
  const canSubmit = touched.length > 0 && incomplete.length === 0 && !submitting;

  const submit = async () => {
    setSubmitting(true);
    setResult(null);
    try {
      const payload = { entries: entries.map((e, i) => ({ row: rows[i].row, ...e })).filter(sanTouched) };
      const data = await postJSON(`${apiBase}/bpr/${encodeURIComponent(uid)}/sanitation`, payload);
      setResult({ ok: true, message: `${data.rows_written} row(s) written to the BPR sheet` });
    } catch (err) {
      setResult({ ok: false, message: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={hint}>
        §17210(c): every cleaned surface needs <strong>date, start time, and end time</strong> —
        recorded as you go, not backfilled. Leave a row fully blank only if that surface wasn't part of this run.
      </div>
      {rows.map((sr, i) => {
        const e = entries[i];
        const isTouched = sanTouched(e);
        const isIncomplete = isTouched && !sanComplete(e);
        return (
          <div key={sr.row} style={{ ...cardBox, borderColor: isIncomplete ? "#E8192C" : "#E2E6EF", background: isTouched ? "#fff" : "#FAFBFD" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, flexWrap: "wrap", gap: 4 }}>
              <strong style={{ fontSize: 14 }}>{sr.row}. {sr.name}</strong>
              {(sr.method || sr.target) && <span style={{ fontSize: 12, color: "#8890A8" }}>{sr.method}{sr.target ? ` · Target: ${sr.target}` : ""}</span>}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 8 }}>
              <label style={lbl}>Date<input style={inp} value={e.date} onChange={(ev) => update(i, "date", ev.target.value)} placeholder="MM/DD/YYYY" /></label>
              <label style={lbl}>Clean Start
                <div style={{ display: "flex", gap: 4 }}>
                  <input style={inp} value={e.clean_start} onChange={(ev) => update(i, "clean_start", ev.target.value)} placeholder="HH:MM" />
                  <button type="button" style={nowBtn} onClick={() => update(i, "clean_start", nowHHMM())}>Now</button>
                </div>
              </label>
              <label style={lbl}>Clean End
                <div style={{ display: "flex", gap: 4 }}>
                  <input style={inp} value={e.clean_end} onChange={(ev) => update(i, "clean_end", ev.target.value)} placeholder="HH:MM" />
                  <button type="button" style={nowBtn} onClick={() => update(i, "clean_end", nowHHMM())}>Now</button>
                </div>
              </label>
              <label style={lbl}>ppm Tested<input style={inp} value={e.ppm} onChange={(ev) => update(i, "ppm", ev.target.value)} placeholder="e.g. 200" /></label>
              <label style={lbl}>Strips Used?
                <select style={inp} value={e.strips_used} onChange={(ev) => update(i, "strips_used", ev.target.value)}><option value=""></option><option>Yes</option><option>No</option></select>
              </label>
              <label style={lbl}>Pass?
                <select style={inp} value={e.passed} onChange={(ev) => update(i, "passed", ev.target.value)}><option value=""></option><option>Yes</option><option>No</option></select>
              </label>
              <label style={lbl}>Cleaned By
                <input style={inp} value={e.cleaned_by} onChange={(ev) => update(i, "cleaned_by", ev.target.value)}
                  placeholder={operatorName || "Name"}
                  onFocus={() => { if (!e.cleaned_by && operatorName) update(i, "cleaned_by", operatorName); }} />
              </label>
              <label style={lbl}>Dry Before Use?
                <select style={inp} value={e.dry_before_use} onChange={(ev) => update(i, "dry_before_use", ev.target.value)}><option value=""></option><option>Yes</option><option>No</option></select>
              </label>
            </div>
            {isIncomplete && <div style={{ marginTop: 6, fontSize: 12, color: "#E8192C" }}>Date, Clean Start, Clean End, and Cleaned By are all required on a touched row.</div>}
          </div>
        );
      })}
      <SubmitRow label={`Submit Sanitation Log (${touched.length})`} canSubmit={canSubmit} submitting={submitting} onClick={submit} result={result} />
    </div>
  );
}

function SubmitRow({ label, canSubmit, submitting, onClick, result }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
      <button type="button" onClick={onClick} disabled={!canSubmit} style={{
        padding: "10px 20px", borderRadius: 7, border: "none",
        background: canSubmit ? "#E8192C" : "#D0D5E3", color: "#fff", fontWeight: 800,
        cursor: canSubmit ? "pointer" : "not-allowed", textTransform: "uppercase", letterSpacing: "0.05em", fontSize: 13,
      }}>
        {submitting ? "Submitting…" : label}
      </button>
      {result && <span style={{ fontSize: 13, color: result.ok ? "#0A7A3E" : "#E8192C" }}>{result.ok ? "✓ " : "✕ "}{result.message}</span>}
    </div>
  );
}

// ── Panel wrapper — two collapsible sections, collapsed by default ───────────
function Collapsible({ title, subtitle, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ border: "1.5px solid #E2E6EF", borderRadius: 10, overflow: "hidden" }}>
      <button type="button" onClick={() => setOpen((o) => !o)} style={{
        width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "14px 16px", background: "#F0F2F7", border: "none", cursor: "pointer", textAlign: "left",
      }}>
        <span><strong style={{ fontSize: 15 }}>{title}</strong><span style={{ fontSize: 12, color: "#8890A8", marginLeft: 8 }}>{subtitle}</span></span>
        <span style={{ fontSize: 18, color: "#8890A8" }}>{open ? "−" : "+"}</span>
      </button>
      {open && <div style={{ padding: 16 }}>{children}</div>}
    </div>
  );
}

export default function EquipmentSanitationPanel({ uid, apiBase, family, operatorName = "" }) {
  const [sharedName] = useEmployeeName();   // same identity the phase cards use
  const cfg = BPR_SECTION_ROWS[family];
  if (!cfg || !uid) return null;   // wash/session/unmapped families use no panel

  const who = operatorName || sharedName;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 16 }}>
      <Collapsible title="Section 4 — Equipment & Processing Lines" subtitle={`${cfg.equipment.length} items · §17221`}>
        <EquipmentBlock uid={uid} apiBase={apiBase} rows={cfg.equipment} operatorName={who} />
      </Collapsible>
      <Collapsible title="Section 5 — Equipment & Surface Sanitation Log" subtitle={`${cfg.sanitation.length} surfaces · §17210(c)`}>
        <SanitationBlock uid={uid} apiBase={apiBase} rows={cfg.sanitation} operatorName={who} />
      </Collapsible>
    </div>
  );
}

// ── shared styles (mirrors SanitationLogWash) ────────────────────────────────
const lbl = { display: "flex", flexDirection: "column", gap: 3, fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#4A5068" };
const inp = { padding: "7px 9px", border: "1.5px solid #D0D5E3", borderRadius: 6, fontSize: 13, width: "100%", boxSizing: "border-box" };
const nowBtn = { padding: "4px 8px", border: "1.5px solid #D0D5E3", borderRadius: 6, background: "#F0F2F7", fontSize: 11, cursor: "pointer", fontWeight: 700 };
const hint = { fontSize: 13, color: "#4A5068", lineHeight: 1.5 };
const rowBox = { display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end", border: "1.5px solid #E2E6EF", borderRadius: 8, padding: 12 };
const cardBox = { border: "1.5px solid #E2E6EF", borderRadius: 8, padding: 12 };
