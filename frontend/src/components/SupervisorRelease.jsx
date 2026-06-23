import { useState } from "react";
import "./SupervisorRelease.css";

export default function SupervisorRelease({ params, signoffs, phases, onRelease, onCancel, saving }) {
  const [supervisorName, setSupervisorName] = useState("");
  const [deviationNotes, setDeviationNotes] = useState("");
  const [totalYield, setTotalYield]         = useState("");
  const [confirmed, setConfirmed]           = useState(false);

  const canRelease = supervisorName.trim() && confirmed && !saving;

  return (
    <div className="release-card">
      <div className="release-card-header">
        <div className="release-icon">📋</div>
        <div>
          <div className="release-title">Supervisor Release</div>
          <div className="release-sub">
            Review and authorize this Batch Production Record for release.
            Your signature certifies all phases were completed correctly.
          </div>
        </div>
      </div>

      {/* Phase summary */}
      <div className="release-summary">
        <div className="release-summary-title">Phase Sign-Off Summary</div>
        {phases.map(phase => {
          const so = signoffs[phase.id];
          return (
            <div key={phase.id} className="release-phase-row">
              <span className="release-phase-check">{so ? "✓" : "○"}</span>
              <span className="release-phase-name">{phase.name}</span>
              {so && (
                <span className="release-phase-by">
                  {so.employee_name} · {so.signed_at
                    ? new Date(so.signed_at).toLocaleString("en-US", {
                        month: "short", day: "numeric",
                        hour: "numeric", minute: "2-digit"
                      })
                    : ""}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Yield entry */}
      <div className="release-field-group">
        <label className="release-field-label">
          Total Batch Yield
          <span className="optional-tag">(optional)</span>
        </label>
        <input
          className="release-input"
          type="text"
          placeholder="e.g. 450g of rosin, 1,200 units"
          value={totalYield}
          onChange={e => setTotalYield(e.target.value)}
        />
      </div>

      {/* Deviation notes */}
      <div className="release-field-group">
        <label className="release-field-label">
          Deviation Log
          <span className="optional-tag">(optional)</span>
        </label>
        <textarea
          className="release-textarea"
          placeholder="Document any deviations from standard procedure, corrective actions taken, or QC holds..."
          value={deviationNotes}
          onChange={e => setDeviationNotes(e.target.value)}
          rows={4}
        />
      </div>

      {/* Supervisor name */}
      <div className="release-field-group">
        <label className="release-field-label">
          Supervisor Name <span className="required-star">*</span>
        </label>
        <input
          className="release-input"
          type="text"
          placeholder="Full name of authorizing supervisor"
          value={supervisorName}
          onChange={e => setSupervisorName(e.target.value)}
        />
      </div>

      {/* Certification checkbox */}
      <label className="release-confirm-row">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={e => setConfirmed(e.target.checked)}
          className="release-confirm-cb"
        />
        <span className="release-confirm-text">
          I certify that all phases of this Batch Production Record have been completed
          in accordance with the Master Manufacturing Protocol (MMP-MASTER-001) and
          applicable SOPs. All CCP measurements meet critical limits. This batch is
          authorized for release.
        </span>
      </label>

      <div className="release-actions">
        <button className="btn btn-ghost-release" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button
          className={`btn btn-release-confirm ${canRelease ? "btn-release-active" : ""}`}
          disabled={!canRelease}
          onClick={() => onRelease(supervisorName, deviationNotes, totalYield)}
        >
          {saving ? "Releasing..." : "Release Batch Record"}
        </button>
      </div>

      <div className="release-note">
        Upon release, a PDF copy of this Batch Production Record will be automatically
        filed to the Google Drive batch folder for archival and DCC compliance.
      </div>
    </div>
  );
}
