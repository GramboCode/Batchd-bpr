import { useState, useEffect } from "react";
import "./PhaseCard.css";
import SanitationLogWash from './SanitationLogWash';

export default function PhaseCard({
  phase, phaseIndex, isActive, isSigned, signoff,
  stepChecks, onToggle, onSignOff, onExpand, saving,
  family, uid, apiBase
}) {
  const [employeeName, setEmployeeName]   = useState(
    () => localStorage.getItem("bpr_employee_name") || ""
  );
  const [nameSet, setNameSet]             = useState(!!localStorage.getItem("bpr_employee_name"));
  const [notes, setNotes]                 = useState("");
  const [ccpValues, setCcpValues]         = useState({});
  const [localChecks, setLocalChecks]     = useState({});
  const [signing, setSigning]             = useState(false);
  const [showNamePrompt, setShowNamePrompt] = useState(false);
  const [nameInput, setNameInput]         = useState("");

  // Build local check state from stepChecks prop
  useEffect(() => {
    const local = {};
    phase.steps.forEach((_, i) => {
      const key = `${phase.id}:${i}`;
      local[i] = stepChecks[key]?.checked || false;
    });
    setLocalChecks(local);
  }, [stepChecks, phase.id]);

  // ── Name management ──────────────────────────────────────────────────
  function saveName() {
    const n = nameInput.trim();
    if (!n) return;
    localStorage.setItem("bpr_employee_name", n);
    setEmployeeName(n);
    setNameSet(true);
    setShowNamePrompt(false);
    setNameInput("");
  }

  function clearName() {
    localStorage.removeItem("bpr_employee_name");
    setEmployeeName("");
    setNameSet(false);
  }

  // ── Step check ───────────────────────────────────────────────────────
  function handleCheck(stepIdx) {
    if (isSigned) return;
    if (!nameSet) { setShowNamePrompt(true); return; }
    const newVal = !localChecks[stepIdx];
    setLocalChecks(prev => ({ ...prev, [stepIdx]: newVal }));
    onToggle(stepIdx, newVal, employeeName);
  }

  // ── CCP value ────────────────────────────────────────────────────────
  function setCCP(stepIdx, val) {
    setCcpValues(prev => ({ ...prev, [stepIdx]: val }));
  }

  // ── Sign-off validation ───────────────────────────────────────────────
  const allChecked = phase.steps.every((_, i) => localChecks[i]);
  const ccpsFilled = (phase.ccps || []).every(i => (ccpValues[i] || "").trim() !== "");
  const noteOk     = !phase.notes_required || notes.trim() !== "";
  const canSignOff = allChecked && ccpsFilled && noteOk && nameSet && !isSigned;

  const checkedCount = Object.values(localChecks).filter(Boolean).length;
  const pct = phase.steps.length > 0
    ? Math.round((checkedCount / phase.steps.length) * 100) : 0;

  // ── Sign off ──────────────────────────────────────────────────────────
  async function handleSignOff() {
    if (!canSignOff || signing) return;
    setSigning(true);
    try {
      await onSignOff(employeeName, notes, ccpValues);
    } finally {
      setSigning(false);
    }
  }

  const ccpSet = new Set(phase.ccps || []);

  return (
    <div className={`phase-card ${isActive ? "phase-active" : ""} ${isSigned ? "phase-signed" : ""}`}>

      {/* ── PHASE HEADER (always visible) ─────────────────────────── */}
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
                      month: "short", day: "numeric",
                      hour: "numeric", minute: "2-digit"
                    })
                  : ""}
              </div>
            ) : (
              <div className="phase-progress-row">
                <div className="phase-mini-track">
                  <div className="phase-mini-fill" style={{ width: `${pct}%` }} />
                </div>
                <span className="phase-step-count">{checkedCount}/{phase.steps.length}</span>
              </div>
            )}
          </div>
        </div>
        <div className="phase-header-right">
          {!isSigned && (
            <span className={`phase-status-chip ${pct === 100 ? "chip-ready" : "chip-progress"}`}>
              {pct === 100 ? "Ready to sign" : `${pct}%`}
            </span>
          )}
          <span className="phase-chevron">{isActive ? "▲" : "▼"}</span>
        </div>
      </button>

      {/* ── PHASE BODY (expanded) ─────────────────────────────────── */}
      {isActive && (
        <div className="phase-body">

          {/* Name prompt overlay */}
          {showNamePrompt && (
            <div className="name-prompt">
              <div className="name-prompt-inner">
                <div className="name-prompt-title">Who is completing this phase?</div>
                <div className="name-prompt-sub">
                  Your name will be recorded with each step you check off.
                  This is saved on this device — you won't need to enter it again.
                </div>
                <input
                  className="name-input"
                  type="text"
                  placeholder="Full name"
                  value={nameInput}
                  onChange={e => setNameInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && saveName()}
                  autoFocus
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

          {/* Employee name display */}
          {!isSigned && (
            <div className="employee-row">
              {nameSet ? (
                <div className="employee-set">
                  <span className="employee-avatar">{employeeName[0]?.toUpperCase()}</span>
                  <span className="employee-name">{employeeName}</span>
                  <button className="btn-text-sm" onClick={clearName}>Change</button>
                </div>
              ) : (
                <button className="btn btn-ghost-sm name-unset-btn" onClick={() => setShowNamePrompt(true)}>
                  ＋ Set your name to start
                </button>
              )}
            </div>
          )}

          {/* Steps list */}
          <div className="steps-list">
            {phase.steps.map((step, i) => {
              const checked  = localChecks[i] || false;
              const isCCP    = ccpSet.has(i);
              const ccpLabel = (phase.ccp_labels || {})[i];
              const stepCheck = stepChecks[`${phase.id}:${i}`];

              return (
                <div key={i} className={`step-row ${checked ? "step-checked" : ""} ${isCCP ? "step-ccp" : ""}`}>
                  <button
                    className={`step-checkbox ${checked ? "cb-checked" : ""}`}
                    onClick={() => handleCheck(i)}
                    disabled={isSigned || !nameSet}
                    aria-label={`${checked ? "Uncheck" : "Check"} step ${i + 1}`}
                  >
                    {checked && "✓"}
                  </button>
                  <div className="step-content">
                    {isCCP && (
                      <div className="ccp-badge">★ Critical Control Point</div>
                    )}
                    <div className="step-text">{step}</div>
                    {checked && stepCheck?.checked_by && (
                      <div className="step-checked-by">
                        {stepCheck.checked_by}
                        {stepCheck.checked_at && (
                          <> · {new Date(stepCheck.checked_at).toLocaleTimeString("en-US", {
                            hour: "numeric", minute: "2-digit"
                          })}</>
                        )}
                      </div>
                    )}
                    {/* CCP measurement input */}
                    {isCCP && !isSigned && (
                      <div className="ccp-input-row">
                        <label className="ccp-input-label">{ccpLabel || "Measurement"}</label>
                        <input
                          className="ccp-input"
                          type="text"
                          placeholder="Enter measurement..."
                          value={ccpValues[i] || ""}
                          onChange={e => setCCP(i, e.target.value)}
                        />
                      </div>
                    )}
                    {/* Show recorded CCP value if signed */}
                    {isCCP && isSigned && signoff?.ccp_values && (
                      <div className="ccp-recorded">
                        <span className="ccp-recorded-label">{ccpLabel}:</span>
                        <span className="ccp-recorded-value">
                          {signoff.ccp_values[i] || signoff.ccp_values[String(i)] || "—"}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Notes field */}
          {!isSigned && (
            <div className="notes-section">
              <label className="notes-label">
                Notes {phase.notes_required && <span className="required-star">*</span>}
                {!phase.notes_required && <span className="optional-tag">(optional)</span>}
              </label>
              <textarea
                className="notes-input"
                placeholder={phase.notes_required
                  ? "Required — describe any observations or deviations..."
                  : "Any observations, deviations, or notes for this phase..."}
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={3}
              />
            </div>
          )}

          {!isSigned && phase.id === 'sanitation' && family === 'rosin_wash' && (
            <SanitationLogWash
              uid={uid}
              apiBase={apiBase}
              operatorName={employeeName}
            />
          )}

          {/* Signed notes display */}
          {isSigned && signoff?.notes && (
            <div className="signed-notes">
              <div className="signed-notes-label">Notes</div>
              <div className="signed-notes-text">{signoff.notes}</div>
            </div>
          )}

          {/* Sign-off button */}
          {!isSigned && (
            <div className="signoff-section">
              {!allChecked && (
                <div className="signoff-hint">
                  {phase.steps.length - checkedCount} step{phase.steps.length - checkedCount !== 1 ? "s" : ""} remaining
                </div>
              )}
              {allChecked && !ccpsFilled && (
                <div className="signoff-hint ccp-hint">
                  ★ Enter all CCP measurements above to sign off
                </div>
              )}
              {allChecked && ccpsFilled && phase.notes_required && !noteOk && (
                <div className="signoff-hint">Notes required for this phase</div>
              )}
              {!nameSet && (
                <div className="signoff-hint">Set your name above to sign off</div>
              )}
              <button
                className={`btn btn-signoff ${canSignOff ? "btn-signoff-ready" : ""}`}
                disabled={!canSignOff || signing || saving}
                onClick={handleSignOff}
              >
                {signing
                  ? "Signing off..."
                  : canSignOff
                  ? `Sign Off — ${phase.name}`
                  : "Complete all steps to sign off"}
              </button>
            </div>
          )}

        </div>
      )}
    </div>
  );
}
