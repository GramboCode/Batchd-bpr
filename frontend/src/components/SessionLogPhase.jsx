// SessionLogPhase.jsx
import { useState, useEffect } from "react";
import { API_BASE } from "../App";

const PHASE_CONFIG = {
  ice_water_wash: {
    kind: "wash",
    endpoint: "wash-session",
    listKey: "wash",
    label: "Wash Session",
  },
  freeze_drying: {
    kind: "freezedry",
    endpoint: "freezedry-session",
    listKey: "freeze_dry",
    label: "Freeze-Dry Session",
    upstreamEndpoint: "available-wash-sessions",
    upstreamLabel: "Wash Session",
  },
  sifting: {
    kind: "sift",
    endpoint: "sift-session",
    listKey: "sift",
    label: "Sift Session",
    upstreamEndpoint: "available-freezedry-sessions",
    upstreamLabel: "Freeze-Dry Session",
  },
};

export default function SessionLogPhase({
  phase, phaseIndex, hashLotId, isActive, isSigned, signoff,
  onToggleStep, onSignOff, onExpand, saving
}) {
  const config = PHASE_CONFIG[phase.id];
  const [employeeName, setEmployeeName] = useState(
    () => localStorage.getItem("bpr_employee_name") || ""
  );
  const [nameSet, setNameSet] = useState(!!localStorage.getItem("bpr_employee_name"));
  const [nameInput, setNameInput] = useState("");
  const [showNamePrompt, setShowNamePrompt] = useState(false);

  const [sessions, setSessions] = useState([]);
  const [upstream, setUpstream] = useState([]);
  const [recon, setRecon] = useState(null);
  const [lotInfo, setLotInfo] = useState(null);   // full lot detail — feeds prefill
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [signing, setSigning] = useState(false);

  useEffect(() => {
    if (isActive) loadData();
  }, [isActive]);

  async function loadData() {
    setLoading(true);
    try {
      // Fixed positions via padded Promise.all — no index arithmetic on
      // conditional pushes. Nulls fill the slots that don't apply.
      const [sessRes, reconRes, upstreamRes, lotRes] = await Promise.all([
        fetch(`${API_BASE}/hash/${hashLotId}/${config.endpoint}s`).then(r => r.json()),
        fetch(`${API_BASE}/hash/${hashLotId}/reconciliation`).then(r => r.json()),
        config.upstreamEndpoint
          ? fetch(`${API_BASE}/hash/${hashLotId}/${config.upstreamEndpoint}`).then(r => r.json())
          : Promise.resolve(null),
        // Lot detail (inputs + creation weights) only matters for the wash
        // form's prefill — skip the call for freeze-dry/sift phases.
        config.kind === "wash"
          ? fetch(`${API_BASE}/hash/${hashLotId}`).then(r => (r.ok ? r.json() : null)).catch(() => null)
          : Promise.resolve(null),
      ]);
      setSessions(sessRes.sessions || []);
      setRecon(reconRes);
      if (upstreamRes) setUpstream(upstreamRes.sessions || []);
      if (lotRes) setLotInfo(lotRes);
    } catch (e) {
      console.error("SessionLogPhase load failed", e);
    } finally {
      setLoading(false);
    }
  }

  function saveName() {
    const n = nameInput.trim();
    if (!n) return;
    localStorage.setItem("bpr_employee_name", n);
    setEmployeeName(n);
    setNameSet(true);
    setShowNamePrompt(false);
    setNameInput("");
  }

  async function handleAddSession(formData) {
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/hash/${hashLotId}/${config.endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...formData, operator_name: employeeName }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.message || data.detail || "Failed to log session");
      setShowAddForm(false);
      await loadData();
    } catch (e) {
      alert(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCloseSession(sessionId, closeData) {
    const closeEndpointMap = {
      wash: "wash-session",
      freezedry: "freezedry-session",
      sift: "sift-session",
    };
    try {
      const res = await fetch(`${API_BASE}/hash/${closeEndpointMap[config.kind]}/${sessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(closeData),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.message || data.detail || "Failed to close session");
      await loadData();
    } catch (e) {
      alert(e.message);
    }
  }

  // ── Phase close-out: roll up session data into a phase signoff ────────
  async function handleClosePhase() {
    if (!recon || signing) return;
    setSigning(true);
    try {
      // 1. Mark every step in this phase checked (session log replaces step-by-step tracking)
      for (let i = 0; i < phase.steps.length; i++) {
        await onToggleStep(i, true, employeeName);
      }

      // 2. Build summary CCP values from lot-level rollups
      const summaryCcpValues = {};
      const ccpLabels = phase.ccp_labels || {};
      (phase.ccps || []).forEach(idx => {
        summaryCcpValues[idx] = buildSummaryValue(idx);
      });

      const notes = buildSummaryNotes();
      await onSignOff(employeeName, notes, summaryCcpValues);
    } catch (e) {
      alert(e.message || "Failed to close phase");
    } finally {
      setSigning(false);
    }
  }

  function buildSummaryValue(ccpIndex) {
    if (!recon) return "";
    if (config.kind === "wash") {
      return `${recon.wash.count} sessions, ${recon.wash.total_wet_weight_g}g total wet weight`;
    }
    if (config.kind === "freezedry") {
      return `${recon.freeze_dry.count} sessions, ${recon.freeze_dry.total_output_dry_weight_g}g total dry weight`;
    }
    if (config.kind === "sift") {
      return `${recon.sift.count} sessions, ${recon.sift.total_sift_weight_out_g}g total sift weight, ${recon.overall_yield_pct ?? "—"}% yield`;
    }
    return "";
  }

  function buildSummaryNotes() {
    if (!recon) return "";
    if (config.kind === "wash") {
      return `${recon.wash.count} wash session(s) logged, totaling ${recon.wash.total_wet_weight_g}g wet weight. See Wash Sessions log for per-session detail.`;
    }
    if (config.kind === "freezedry") {
      return `${recon.freeze_dry.count} freeze-dry session(s) logged. Input ${recon.freeze_dry.total_input_wet_weight_g}g → output ${recon.freeze_dry.total_output_dry_weight_g}g. See Freeze-Dry Sessions log for per-session detail.`;
    }
    if (config.kind === "sift") {
      return `${recon.sift.count} sift session(s) logged. Input ${recon.sift.total_dry_weight_in_g}g → output ${recon.sift.total_sift_weight_out_g}g (${recon.overall_yield_pct ?? "—"}% overall yield). See Sift Sessions log for per-session detail.`;
    }
    return "";
  }

  // ── Prefill for the Add Session form ──────────────────────────────────
  // Principle: never make an operator re-type what the system already
  // knows — but keep everything editable, because session reality can
  // differ from creation intent (split washes, swapped washers).
  const lastSession = sessions.length ? sessions[sessions.length - 1] : null;

  function buildPrefill() {
    const prefill = {
      // Equipment carries forward from the previous session on this lot —
      // washer 1 in session 1 almost always means washer 1 in session 2.
      equipmentId: lastSession?.equipment_id || "",
      freshFrozenUids: "",
      wetWeight: "",
      wetWeightHint: "",
    };
    if (config.kind === "wash" && lotInfo) {
      prefill.freshFrozenUids = (lotInfo.inputs || [])
        .map(i => i.fresh_frozen_uid)
        .filter(Boolean)
        .join(", ");

      // Wet weight: prefill the REMAINING unlogged weight — full total for
      // the first session, the leftover for later sessions of a split wash.
      const totalWet = parseFloat(lotInfo.lot?.wet_weight_g) || 0;
      const loggedWet = sessions.reduce(
        (sum, s) => sum + (parseFloat(s.wet_weight_g) || 0), 0
      );
      const remaining = Math.round((totalWet - loggedWet) * 100) / 100;
      if (remaining > 0) {
        prefill.wetWeight = String(remaining);
        prefill.wetWeightHint = sessions.length === 0
          ? "Prefilled from batch creation — adjust if splitting across sessions"
          : `Prefilled with remaining unlogged weight (${remaining}g of ${totalWet}g)`;
      }
    }
    return prefill;
  }

  const readyToClose = sessions.length > 0 && sessions.every(s => s.completed_at);
  const openCount = sessions.filter(s => !s.completed_at).length;

  return (
    <div className={`phase-card ${isActive ? "phase-active" : ""} ${isSigned ? "phase-signed" : ""}`}>
      <button className="phase-header" onClick={onExpand}>
        <div className="phase-header-left">
          <div className={`phase-number ${isSigned ? "num-signed" : ""}`}>
            {isSigned ? "✓" : phaseIndex + 1}
          </div>
          <div className="phase-header-info">
            <div className="phase-title">{phase.name}</div>
            {isSigned ? (
              <div className="phase-signed-by">
                Signed off by <strong>{signoff?.employee_name}</strong>
                {" · "}
                {signoff?.signed_at
                  ? new Date(signoff.signed_at).toLocaleString("en-US", {
                      month: "short", day: "numeric", hour: "numeric", minute: "2-digit"
                    })
                  : ""}
              </div>
            ) : (
              <div className="phase-progress-row">
                <span className="phase-step-count">
                  {sessions.length} session{sessions.length !== 1 ? "s" : ""}
                  {openCount > 0 ? ` · ${openCount} open` : ""}
                </span>
              </div>
            )}
          </div>
        </div>
        <div className="phase-header-right">
          {!isSigned && (
            <span className={`phase-status-chip ${readyToClose ? "chip-ready" : "chip-progress"}`}>
              {readyToClose ? "Ready to close" : "In progress"}
            </span>
          )}
          <span className="phase-chevron">{isActive ? "▲" : "▼"}</span>
        </div>
      </button>

      {isActive && (
        <div className="phase-body">
          {showNamePrompt && (
            <div className="name-prompt">
              <div className="name-prompt-inner">
                <div className="name-prompt-title">Who is logging this session?</div>
                <div className="name-prompt-sub">
                  Your name will be recorded on every session you log. Saved on this device.
                </div>
                <input
                  className="name-input" type="text" placeholder="Full name"
                  value={nameInput} onChange={e => setNameInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && saveName()} autoFocus
                />
                <div className="name-prompt-actions">
                  <button className="btn btn-ghost-sm" onClick={() => setShowNamePrompt(false)}>Cancel</button>
                  <button className="btn btn-primary-sm" onClick={saveName} disabled={!nameInput.trim()}>
                    Confirm Name
                  </button>
                </div>
              </div>
            </div>
          )}

          {!isSigned && (
            <div className="employee-row">
              {nameSet ? (
                <div className="employee-set">
                  <span className="employee-avatar">{employeeName[0]?.toUpperCase()}</span>
                  <span className="employee-name">{employeeName}</span>
                  <button className="btn-text-sm" onClick={() => { localStorage.removeItem("bpr_employee_name"); setEmployeeName(""); setNameSet(false); }}>
                    Change
                  </button>
                </div>
              ) : (
                <button className="btn btn-ghost-sm name-unset-btn" onClick={() => setShowNamePrompt(true)}>
                  ＋ Set your name to start
                </button>
              )}
            </div>
          )}

          {loading ? (
            <div style={{ padding: "20px 0", textAlign: "center", color: "var(--text3)" }}>Loading sessions...</div>
          ) : (
            <>
              <div className="steps-list">
                {sessions.length === 0 && (
                  <div style={{ padding: "16px 0", color: "var(--text3)", fontSize: "0.85rem" }}>
                    No {config.label.toLowerCase()}s logged yet.
                  </div>
                )}
                {sessions.map(s => (
                  <SessionCard
                    key={s.id}
                    session={s}
                    kind={config.kind}
                    onClose={handleCloseSession}
                    isSigned={isSigned}
                  />
                ))}
              </div>

              {!isSigned && nameSet && !showAddForm && (
                <button className="btn btn-ghost-sm" style={{ width: "100%", marginTop: 8 }} onClick={() => setShowAddForm(true)}>
                  ＋ Log New {config.label}
                </button>
              )}

              {!isSigned && showAddForm && (
                <AddSessionForm
                  kind={config.kind}
                  upstream={upstream}
                  upstreamLabel={config.upstreamLabel}
                  prefill={buildPrefill()}
                  onSubmit={handleAddSession}
                  onCancel={() => setShowAddForm(false)}
                  submitting={submitting}
                />
              )}

              {!isSigned && (
                <div className="signoff-section">
                  {!readyToClose && (
                    <div className="signoff-hint">
                      {sessions.length === 0
                        ? `Log at least one ${config.label.toLowerCase()} to close this phase`
                        : `${openCount} open session${openCount !== 1 ? "s" : ""} must be closed first`}
                    </div>
                  )}
                  {!nameSet && <div className="signoff-hint">Set your name above to close this phase</div>}
                  <button
                    className={`btn btn-signoff ${readyToClose && nameSet ? "btn-signoff-ready" : ""}`}
                    disabled={!readyToClose || !nameSet || signing || saving}
                    onClick={handleClosePhase}
                  >
                    {signing ? "Closing phase..." : readyToClose ? `Close Phase — ${phase.name}` : "Close all sessions to continue"}
                  </button>
                </div>
              )}
            </>
          )}

          {isSigned && signoff?.notes && (
            <div className="signed-notes">
              <div className="signed-notes-label">Summary</div>
              <div className="signed-notes-text">{signoff.notes}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Individual session card ───────────────────────────────────────────
function SessionCard({ session, kind, onClose, isSigned }) {
  const [closing, setClosing] = useState(false);
  const [closeVal, setCloseVal] = useState("");

  const isOpen = !session.completed_at;

  const fieldLabel = {
    wash: "Wet weight",
    freezedry: "Dry weight (out)",
    sift: "Sift weight (out)",
  }[kind];

  const closeFieldKey = {
    wash: "wet_weight_g",
    freezedry: "output_dry_weight_g",
    sift: "sift_weight_out_g",
  }[kind];

  async function submitClose() {
    if (!closeVal.trim()) return;
    setClosing(true);
    await onClose(session.id, { [closeFieldKey]: parseFloat(closeVal) });
    setClosing(false);
  }

  return (
    <div className={`step-row ${!isOpen ? "step-checked" : ""}`}>
      <div className={`step-checkbox ${!isOpen ? "cb-checked" : ""}`}>
        {!isOpen && "✓"}
      </div>
      <div className="step-content" style={{ width: "100%" }}>
        <div className="step-text">
          <strong>Session {session.session_num}</strong> — {session.operator_name}
          {session.equipment_id ? ` · ${session.equipment_id}` : ""}
        </div>
        <div className="step-checked-by">
          {kind === "wash" && `${session.wet_weight_g}g wet weight`}
          {kind === "freezedry" && `${session.input_wet_weight_g}g in${session.output_dry_weight_g ? ` → ${session.output_dry_weight_g}g dry` : ""}`}
          {kind === "sift" && `${session.dry_weight_in_g}g in${session.sift_weight_out_g ? ` → ${session.sift_weight_out_g}g sift` : ""}`}
          {session.started_at && ` · started ${new Date(session.started_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}`}
        </div>

        {isOpen && !isSigned && (
          <div className="ccp-input-row">
            <label className="ccp-input-label">{fieldLabel} — enter to close session</label>
            <input
              className="ccp-input" type="number" placeholder="Enter weight..."
              value={closeVal} onChange={e => setCloseVal(e.target.value)}
            />
            <button className="btn btn-primary-sm" style={{ marginTop: 6 }} disabled={closing || !closeVal.trim()} onClick={submitClose}>
              {closing ? "Closing..." : "Close Session"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Add session form — shape differs by kind ──────────────────────────
function AddSessionForm({ kind, upstream, upstreamLabel, prefill = {}, onSubmit, onCancel, submitting }) {
  // Prefill lands via initial state: the form mounts fresh on every
  // "Log New Session" click, so initializers pick up current lot data.
  // Everything stays editable — prefill is a head start, not a lock.
  const [equipmentId, setEquipmentId] = useState(prefill.equipmentId || "");
  const [teaBagCount, setTeaBagCount] = useState("");
  const [freshFrozenUids, setFreshFrozenUids] = useState(prefill.freshFrozenUids || "");
  const [wetWeight, setWetWeight] = useState(prefill.wetWeight || "");
  const [roConfirmed, setRoConfirmed] = useState(false);
  const [pumpOilChecked, setPumpOilChecked] = useState(false);
  const [storageLocation, setStorageLocation] = useState("");
  const [notes, setNotes] = useState("");
  const [allocations, setAllocations] = useState({}); // { sessionId: weight }

  function toggleAllocation(sessionId, remaining) {
    setAllocations(prev => {
      const next = { ...prev };
      if (next[sessionId] !== undefined) {
        delete next[sessionId];
      } else {
        next[sessionId] = remaining;
      }
      return next;
    });
  }

  function handleSubmit() {
    if (kind === "wash") {
      onSubmit({
        equipment_id: equipmentId || null,
        tea_bag_count: teaBagCount ? parseInt(teaBagCount) : null,
        fresh_frozen_uids: freshFrozenUids.split(",").map(s => s.trim()).filter(Boolean),
        wet_weight_g: parseFloat(wetWeight),
        ro_water_confirmed: roConfirmed,
        started_at: new Date().toISOString(),
        notes: notes || null,
      });
    } else if (kind === "freezedry") {
      onSubmit({
        equipment_id: equipmentId || null,
        pump_oil_checked: pumpOilChecked,
        started_at: new Date().toISOString(),
        notes: notes || null,
        allocations: Object.entries(allocations).map(([id, weight]) => ({
          wash_session_id: id, weight_allocated_g: weight
        })),
      });
    } else if (kind === "sift") {
      onSubmit({
        storage_location: storageLocation || null,
        notes: notes || null,
        allocations: Object.entries(allocations).map(([id, weight]) => ({
          freezedry_session_id: id, weight_allocated_g: weight
        })),
      });
    }
  }

  const hasUpstream = kind === "freezedry" || kind === "sift";
  const canSubmit = kind === "wash"
    ? wetWeight.trim() !== ""
    : Object.keys(allocations).length > 0;

  return (
    <div className="phase-body" style={{ background: "var(--light)", borderRadius: 8, padding: 14, marginTop: 10 }}>
      {kind === "wash" && (
        <>
          <div className="notes-section">
            <label className="notes-label">Equipment / Washer ID</label>
            <input className="notes-input" style={{ minHeight: "auto" }} type="text" placeholder="e.g. Washer 2" value={equipmentId} onChange={e => setEquipmentId(e.target.value)} />
          </div>
          <div className="notes-section">
            <label className="notes-label">Tea Bag Count</label>
            <input className="notes-input" style={{ minHeight: "auto" }} type="number" placeholder="e.g. 4" value={teaBagCount} onChange={e => setTeaBagCount(e.target.value)} />
          </div>
          <div className="notes-section">
            <label className="notes-label">Fresh Frozen UIDs (comma-separated)</label>
            <input className="notes-input" style={{ minHeight: "auto" }} type="text" placeholder="1A4060300005D6A000006811, ..." value={freshFrozenUids} onChange={e => setFreshFrozenUids(e.target.value)} />
          </div>
          <div className="notes-section">
            <label className="notes-label">Wet Weight (g) <span className="required-star">*</span></label>
            <input className="notes-input" style={{ minHeight: "auto" }} type="number" placeholder="e.g. 4000" value={wetWeight} onChange={e => setWetWeight(e.target.value)} />
            {prefill.wetWeightHint && wetWeight === prefill.wetWeight && (
              <div style={{ fontSize: "0.75rem", color: "var(--text3)", marginTop: 4 }}>
                {prefill.wetWeightHint}
              </div>
            )}
          </div>
          <label className="release-confirm-row">
            <input type="checkbox" className="release-confirm-cb" checked={roConfirmed} onChange={e => setRoConfirmed(e.target.checked)} />
            <span className="release-confirm-text">RO water confirmed (not tap water)</span>
          </label>
        </>
      )}

      {kind === "freezedry" && (
        <>
          <div className="notes-section">
            <label className="notes-label">Equipment / Freeze Dryer ID</label>
            <input className="notes-input" style={{ minHeight: "auto" }} type="text" placeholder="e.g. Dryer A" value={equipmentId} onChange={e => setEquipmentId(e.target.value)} />
          </div>
          <label className="release-confirm-row">
            <input type="checkbox" className="release-confirm-cb" checked={pumpOilChecked} onChange={e => setPumpOilChecked(e.target.checked)} />
            <span className="release-confirm-text">Pump oil level checked</span>
          </label>
        </>
      )}

      {kind === "sift" && (
        <div className="notes-section">
          <label className="notes-label">Storage Location</label>
          <input className="notes-input" style={{ minHeight: "auto" }} type="text" placeholder="e.g. Freezer 1 — Shelf 2" value={storageLocation} onChange={e => setStorageLocation(e.target.value)} />
        </div>
      )}

      {hasUpstream && (
        <div className="notes-section">
          <label className="notes-label">
            Select {upstreamLabel}s Going Into This {kind === "freezedry" ? "Dryer Load" : "Sift"} <span className="required-star">*</span>
          </label>
          {upstream.length === 0 && (
            <div style={{ fontSize: "0.82rem", color: "var(--text3)", padding: "8px 0" }}>
              No {upstreamLabel.toLowerCase()}s with remaining weight available.
            </div>
          )}
          {upstream.map(u => {
            const checked = allocations[u.id] !== undefined;
            return (
              <div key={u.id} className="step-row" style={{ marginBottom: 6 }}>
                <button
                  className={`step-checkbox ${checked ? "cb-checked" : ""}`}
                  onClick={() => toggleAllocation(u.id, parseFloat(u.remaining_g))}
                >
                  {checked && "✓"}
                </button>
                <div className="step-content">
                  <div className="step-text">
                    Session {u.session_num} — {u.operator_name}
                    {u.equipment_id ? ` · ${u.equipment_id}` : ""}
                    {" · "}{Number(u.remaining_g).toLocaleString()}g remaining
                  </div>
                  {checked && (
                    <input
                      className="ccp-input" type="number"
                      value={allocations[u.id]}
                      max={u.remaining_g}
                      onChange={e => setAllocations(prev => ({ ...prev, [u.id]: parseFloat(e.target.value) || 0 }))}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="notes-section">
        <label className="notes-label">Notes <span className="optional-tag">(optional)</span></label>
        <textarea className="notes-input" rows={2} value={notes} onChange={e => setNotes(e.target.value)} />
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
        <button className="btn btn-ghost-sm" onClick={onCancel}>Cancel</button>
        <button className="btn btn-primary-sm" disabled={!canSubmit || submitting} onClick={handleSubmit}>
          {submitting ? "Saving..." : "Log Session"}
        </button>
      </div>
    </div>
  );
}
