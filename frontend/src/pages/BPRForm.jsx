import { useState, useEffect, useRef } from "react";
import { API_BASE } from "../App";
import PhaseCard from "../components/PhaseCard";
import SupervisorRelease from "../components/SupervisorRelease";
import Toast from "../components/Toast";
import "./BPRForm.css";
import SessionLogPhase from "../components/SessionLogPhase";

export default function BPRForm({ bprData, setBprData, params, onComplete }) {
  const [phases, setPhases]           = useState([]);
  const [signoffs, setSignoffs]       = useState({});
  const [stepChecks, setStepChecks]   = useState({});
  const [activePhase, setActivePhase] = useState(null);
  const [showRelease, setShowRelease] = useState(false);
  const [toast, setToast]             = useState(null);
  const [saving, setSaving]           = useState(false);
  const phaseRefs                     = useRef({});

  useEffect(() => {
    if (!bprData) return;
    const def = bprData.phases || bprData.definition || {};
    const phaseList = def.phases || [];
    setPhases(phaseList);
    setSignoffs(bprData.signoffs || {});
    setStepChecks(bprData.steps || {});
    // Open first unsigned phase automatically
    const firstUnsigned = phaseList.find(p => !(bprData.signoffs || {})[p.id]);
    if (firstUnsigned) setActivePhase(firstUnsigned.id);
  }, [bprData]);

  const uid = params.uid;
  const family = bprData?.family || bprData?.bpr?.product_family || null;
  
  // ── Step check toggle ─────────────────────────────────────────────────
  async function toggleStep(phaseId, stepIndex, checked, employeeName) {
    const key = `${phaseId}:${stepIndex}`;
    // Optimistic update
    setStepChecks(prev => ({
      ...prev,
      [key]: { checked, checked_by: employeeName, checked_at: new Date().toISOString() }
    }));

    try {
      const res = await fetch(`${API_BASE}/bpr/${uid}/step`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phase_id: phaseId,
          step_index: stepIndex,
          checked,
          checked_by: employeeName,
        }),
      });
      if (!res.ok) throw new Error("Failed to save step");
    } catch (e) {
      // Revert
      setStepChecks(prev => ({
        ...prev,
        [key]: { checked: !checked }
      }));
      showToast("Failed to save — check connection", "error");
    }
  }

  async function toggleStepAwaitable(phaseId, stepIndex, checked, employeeName) {
    await fetch(`${API_BASE}/bpr/${uid}/step`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phase_id: phaseId, step_index: stepIndex, checked, checked_by: employeeName }),
    });
  }

  // ── Phase sign-off ────────────────────────────────────────────────────
  async function signOffPhase(phaseId, employeeName, notes, ccpValues) {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/bpr/${uid}/phase/signoff`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phase_id: phaseId,
          employee_name: employeeName,
          notes: notes || null,
          ccp_values: ccpValues || null,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        if (typeof detail === "object" && detail.message) {
          throw new Error(detail.message + (detail.missing_ccps
            ? "\n\nRequired: " + detail.missing_ccps.join(", ")
            : "") + (detail.unchecked_steps
            ? `\n\n${detail.unchecked_steps.length} step(s) not yet checked`
            : ""));
        }
        throw new Error(detail || "Sign-off failed");
      }

      // Update signoffs
      setSignoffs(prev => ({ ...prev, [phaseId]: data.signoff }));
      showToast(`${data.signoff.phase_name} signed off`, "success");

      // Auto-open next phase
      const phaseList = phases;
      const currentIdx = phaseList.findIndex(p => p.id === phaseId);
      const nextPhase = phaseList[currentIdx + 1];
      if (nextPhase) {
        setActivePhase(nextPhase.id);
        setTimeout(() => {
          phaseRefs.current[nextPhase.id]?.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 300);
      } else {
        // All phases signed — prompt supervisor release
        setActivePhase(null);
      }
    } catch (e) {
      showToast(e.message || "Sign-off failed", "error");
    } finally {
      setSaving(false);
    }
  }

  // ── Supervisor release ────────────────────────────────────────────────
  async function supervisorRelease(supervisorName, deviationNotes, totalYield) {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/bpr/${uid}/release`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supervisor_name: supervisorName,
          deviation_notes: deviationNotes || null,
          total_yield: totalYield || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        const msg = typeof detail === "object" ? detail.message : detail;
        throw new Error(msg || "Release failed");
      }
      onComplete(data.bpr);
    } catch (e) {
      showToast(e.message || "Release failed", "error");
    } finally {
      setSaving(false);
    }
  }

  function showToast(msg, type = "info") {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  }

  // ── Progress ──────────────────────────────────────────────────────────
  const signedCount = Object.keys(signoffs).length;
  const totalPhases = phases.length;
  const pct = totalPhases > 0 ? Math.round((signedCount / totalPhases) * 100) : 0;
  const allSigned = signedCount === totalPhases && totalPhases > 0;

  return (
    <div className="bpr-app">
      {/* ── TOP HEADER ─────────────────────────────────────────────── */}
      <header className="bpr-header">
        <div className="bpr-header-inner">
          <div className="bpr-brand">
            <span className="brand-punch">PUNCH</span>
            <span className="brand-bpr">BPR</span>
          </div>
          <div className="bpr-batch-info">
            <span className="batch-name">{params.productName}</span>
            <span className="batch-id">{params.batchId}</span>
          </div>
          <div className="bpr-progress-pill">
            <span className="progress-label">{signedCount}/{totalPhases}</span>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${pct}%` }} />
            </div>
          </div>
        </div>

        {/* Batch context strip */}
        <div className="batch-context-strip">
          <span className="context-item">
            <span className="context-label">UID</span>
            <span className="context-value uid">{params.uid}</span>
          </span>
          {params.mfgDate && (
            <span className="context-item">
              <span className="context-label">Mfg Date</span>
              <span className="context-value">{params.mfgDate}</span>
            </span>
          )}
          <span className="context-item">
            <span className="context-label">Status</span>
            <span className="context-value status">
              {allSigned ? "READY FOR RELEASE" : "IN PROGRESS"}
            </span>
          </span>
        </div>
      </header>

      {/* ── PHASE NAVIGATION ──────────────────────────────────────── */}
      <div className="phase-nav">
        <div className="phase-nav-inner">
          {phases.map((phase, i) => {
            const signed = !!signoffs[phase.id];
            const active = activePhase === phase.id;
            return (
              <button
                key={phase.id}
                className={`phase-nav-btn ${signed ? "signed" : ""} ${active ? "active" : ""}`}
                onClick={() => {
                  setActivePhase(active ? null : phase.id);
                  phaseRefs.current[phase.id]?.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
              >
                <span className="phase-nav-num">
                  {signed ? "✓" : i + 1}
                </span>
                <span className="phase-nav-name">{phase.name}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── MAIN CONTENT ──────────────────────────────────────────── */}
      <main className="bpr-main">

        {phases.map((phase, i) => {
          const isSessionPhase = ["ice_water_wash", "freeze_drying", "sifting"].includes(phase.id);
          return (
            <div
              key={phase.id}
              ref={el => phaseRefs.current[phase.id] = el}
              className="phase-section"
            >
              {isSessionPhase ? (
                <SessionLogPhase
                  phase={phase}
                  phaseIndex={i}
                  hashLotId={params.batchId}
                  isActive={activePhase === phase.id}
                  isSigned={!!signoffs[phase.id]}
                  signoff={signoffs[phase.id]}
                  onToggleStep={(idx, checked, name) => toggleStepAwaitable(phase.id, idx, checked, name)}
                  onSignOff={(name, notes, ccpValues) => signOffPhase(phase.id, name, notes, ccpValues)}
                  onExpand={() => setActivePhase(activePhase === phase.id ? null : phase.id)}
                  saving={saving}
                />
              ) : (
                <PhaseCard
                  phase={phase}
                  phaseIndex={i}
                  isActive={activePhase === phase.id}
                  isSigned={!!signoffs[phase.id]}
                  signoff={signoffs[phase.id]}
                  stepChecks={stepChecks}
                  family={family}
                  uid={params.batchId}
                  apiBase={API_BASE}
                  onToggle={(stepIdx, checked, name) =>
                    toggleStep(phase.id, stepIdx, checked, name)
                  }
                  onSignOff={(name, notes, ccpValues) =>
                    signOffPhase(phase.id, name, notes, ccpValues)
                  }
                  onExpand={() => setActivePhase(activePhase === phase.id ? null : phase.id)}
                  saving={saving}
                />
              )}
            </div>
          );
        })}

        {/* ── RELEASE BANNER ──────────────────────────────────────── */}
        {allSigned && !showRelease && (
          <div className="release-banner">
            <div className="release-banner-icon">✓</div>
            <div className="release-banner-text">
              <div className="release-banner-title">All Phases Complete</div>
              <div className="release-banner-sub">
                All {totalPhases} production phases have been signed off.
                Supervisor release is required to complete this batch record.
              </div>
            </div>
            <button
              className="btn btn-release"
              onClick={() => setShowRelease(true)}
            >
              Supervisor Release
            </button>
          </div>
        )}

        {showRelease && (
          <SupervisorRelease
            params={params}
            signoffs={signoffs}
            phases={phases}
            onRelease={supervisorRelease}
            onCancel={() => setShowRelease(false)}
            saving={saving}
          />
        )}

      </main>

      {toast && <Toast msg={toast.msg} type={toast.type} />}
    </div>
  );
}
