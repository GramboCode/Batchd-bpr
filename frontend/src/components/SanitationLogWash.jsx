// SanitationLogWash.jsx — Section 5 sanitation entry form for wash BPRs
//
// Drop-in component for the BatchD BPR app. Renders the seven wash
// equipment/surface rows with the fields §17210(c) requires (Date AND
// Time on every row), and submits them to POST /hash/{uid}/sanitation,
// which writes through to the sheet's WASH_S5_* named ranges.
//
// WIRING (two lines wherever the Post-Run Sanitation phase renders):
//   import SanitationLogWash from './SanitationLogWash';
//   <SanitationLogWash uid={uid} apiBase={BPR_API} operatorName={currentOperator} />
//
// Props:
//   uid          — the hash lot ID / BPR uid (e.g. "HASH-GOVOAS-0711-01")
//   apiBase      — e.g. "https://batchd-bpr-production.up.railway.app"
//   operatorName — prefills Cleaned By (editable per row)
//
// Design notes:
// - Equipment list mirrors the sheet's fixed 7 rows; Method/Solution and
//   Target ppm are template content, shown read-only here for reference.
// - A row left completely blank is skipped (not every run touches every
//   surface). A partially-filled row blocks submission — the backend
//   enforces the same rule, but catching it client-side is kinder.
// - "Now" buttons stamp the current time into start/end — the fastest
//   honest way to satisfy the concurrent-recording requirement.

import { useState } from 'react';

const EQUIPMENT_ROWS = [
  { row: 1, name: 'Ice Water Washer(s)',      method: 'Hot water → ISO-alcohol or chlorine sanitizer EOD', targetPpm: '200 ppm' },
  { row: 2, name: 'Bubble Bags',              method: 'RO water rinse → air dry completely',               targetPpm: 'N/A — water' },
  { row: 3, name: 'Freeze Dryer Trays',       method: 'ISO-Alcohol wipe — inspect for residue',            targetPpm: 'ISO-Alcohol' },
  { row: 4, name: 'Collection Trays & Tools', method: 'ISO-Alcohol wipe',                                  targetPpm: 'ISO-Alcohol' },
  { row: 5, name: 'Sift Screens',             method: 'ISO-Alcohol wipe — between strains',                targetPpm: 'ISO-Alcohol' },
  { row: 6, name: 'Production tabletops',     method: '70–99% ISO-Alcohol',                                targetPpm: '200 ppm' },
  { row: 7, name: 'Scale / weighing surface', method: 'New parchment paper',                               targetPpm: 'N/A' },
];

const emptyEntry = () => ({
  date: new Date().toLocaleDateString('en-US'),  // today, editable
  clean_start: '',
  clean_end: '',
  ppm: '',
  strips_used: '',
  passed: '',
  cleaned_by: '',
  dry_before_use: '',
});

function nowHHMM() {
  const d = new Date();
  return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
}

// A row counts as "touched" if the operator entered anything beyond the
// prefilled date — fully untouched rows are legitimately skippable.
function rowTouched(e) {
  return !!(e.clean_start || e.clean_end || e.ppm || e.passed || e.cleaned_by || e.dry_before_use || e.strips_used);
}

function rowComplete(e) {
  return !!(e.date && e.clean_start && e.clean_end && e.cleaned_by);
}

export default function SanitationLogWash({ uid, apiBase, operatorName = '' }) {
  const [entries, setEntries] = useState(
    EQUIPMENT_ROWS.map(() => ({ ...emptyEntry(), cleaned_by: '' }))
  );
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);   // { ok, message }

  const update = (idx, field, value) => {
    setEntries(prev => prev.map((e, i) => (i === idx ? { ...e, [field]: value } : e)));
    setResult(null);
  };

  const touched    = entries.filter(rowTouched);
  const incomplete = entries
    .map((e, i) => (rowTouched(e) && !rowComplete(e) ? EQUIPMENT_ROWS[i].row : null))
    .filter(Boolean);
  const canSubmit = touched.length > 0 && incomplete.length === 0 && !submitting;

  const submit = async () => {
    setSubmitting(true);
    setResult(null);
    try {
      const payload = {
        entries: entries
          .map((e, i) => ({ row: EQUIPMENT_ROWS[i].row, ...e }))
          .filter(e => rowTouched(e)),
      };
      const res = await fetch(`${apiBase}/hash/${encodeURIComponent(uid)}/sanitation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : (data.detail?.message || 'Submission failed'));
      setResult({ ok: true, message: `${data.rows_written} row(s) written to the BPR sheet` });
    } catch (err) {
      setResult({ ok: false, message: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ fontSize: 13, color: '#4A5068', lineHeight: 1.5 }}>
        §17210(c): every cleaned surface needs <strong>date, start time, and end time</strong> —
        recorded as you go, not backfilled. Leave a row fully blank only if that
        surface wasn't part of this run.
      </div>

      {EQUIPMENT_ROWS.map((eq, i) => {
        const e = entries[i];
        const isTouched = rowTouched(e);
        const isIncomplete = isTouched && !rowComplete(e);
        return (
          <div key={eq.row} style={{
            border: `1.5px solid ${isIncomplete ? '#E8192C' : '#E2E6EF'}`,
            borderRadius: 8, padding: 12,
            background: isTouched ? '#fff' : '#FAFBFD',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, flexWrap: 'wrap', gap: 4 }}>
              <strong style={{ fontSize: 14 }}>{eq.row}. {eq.name}</strong>
              <span style={{ fontSize: 12, color: '#8890A8' }}>{eq.method} · Target: {eq.targetPpm}</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 8 }}>
              <label style={lbl}>Date
                <input style={inp} value={e.date} onChange={ev => update(i, 'date', ev.target.value)} placeholder="MM/DD/YYYY" />
              </label>
              <label style={lbl}>Clean Start
                <div style={{ display: 'flex', gap: 4 }}>
                  <input style={inp} value={e.clean_start} onChange={ev => update(i, 'clean_start', ev.target.value)} placeholder="HH:MM" />
                  <button type="button" style={nowBtn} onClick={() => update(i, 'clean_start', nowHHMM())}>Now</button>
                </div>
              </label>
              <label style={lbl}>Clean End
                <div style={{ display: 'flex', gap: 4 }}>
                  <input style={inp} value={e.clean_end} onChange={ev => update(i, 'clean_end', ev.target.value)} placeholder="HH:MM" />
                  <button type="button" style={nowBtn} onClick={() => update(i, 'clean_end', nowHHMM())}>Now</button>
                </div>
              </label>
              <label style={lbl}>ppm Tested
                <input style={inp} value={e.ppm} onChange={ev => update(i, 'ppm', ev.target.value)} placeholder="e.g. 200" />
              </label>
              <label style={lbl}>Strips Used?
                <select style={inp} value={e.strips_used} onChange={ev => update(i, 'strips_used', ev.target.value)}>
                  <option value=""></option><option>Yes</option><option>No</option>
                </select>
              </label>
              <label style={lbl}>Pass?
                <select style={inp} value={e.passed} onChange={ev => update(i, 'passed', ev.target.value)}>
                  <option value=""></option><option>Yes</option><option>No</option>
                </select>
              </label>
              <label style={lbl}>Cleaned By
                <input style={inp} value={e.cleaned_by} onChange={ev => update(i, 'cleaned_by', ev.target.value)}
                       placeholder={operatorName || 'Name'} 
                       onFocus={() => { if (!e.cleaned_by && operatorName) update(i, 'cleaned_by', operatorName); }} />
              </label>
              <label style={lbl}>Dry Before Use?
                <select style={inp} value={e.dry_before_use} onChange={ev => update(i, 'dry_before_use', ev.target.value)}>
                  <option value=""></option><option>Yes</option><option>No</option>
                </select>
              </label>
            </div>

            {isIncomplete && (
              <div style={{ marginTop: 6, fontSize: 12, color: '#E8192C' }}>
                Date, Clean Start, Clean End, and Cleaned By are all required on a touched row.
              </div>
            )}
          </div>
        );
      })}

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button type="button" onClick={submit} disabled={!canSubmit} style={{
          padding: '10px 20px', borderRadius: 7, border: 'none',
          background: canSubmit ? '#E8192C' : '#D0D5E3',
          color: '#fff', fontWeight: 800, cursor: canSubmit ? 'pointer' : 'not-allowed',
          textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: 13,
        }}>
          {submitting ? 'Submitting…' : `Submit Sanitation Log (${touched.length} row${touched.length === 1 ? '' : 's'})`}
        </button>
        {result && (
          <span style={{ fontSize: 13, color: result.ok ? '#0A7A3E' : '#E8192C' }}>
            {result.ok ? '✓ ' : '✕ '}{result.message}
          </span>
        )}
      </div>
    </div>
  );
}

const lbl = { display: 'flex', flexDirection: 'column', gap: 3, fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#4A5068' };
const inp = { padding: '7px 9px', border: '1.5px solid #D0D5E3', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' };
const nowBtn = { padding: '4px 8px', border: '1.5px solid #D0D5E3', borderRadius: 6, background: '#F0F2F7', fontSize: 11, cursor: 'pointer', fontWeight: 700 };
