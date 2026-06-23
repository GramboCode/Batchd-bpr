// Toast.jsx
export function Toast({ msg, type = "info" }) {
  const colors = { success: "#0A7A3E", error: "#E8192C", info: "#1A56DB" };
  return (
    <div style={{
      position: "fixed", bottom: 20, left: "50%", transform: "translateX(-50%)",
      background: "#1A1D2E", color: "#fff", padding: "12px 20px",
      borderRadius: 8, fontSize: "0.88rem", fontFamily: "'Barlow Condensed', sans-serif",
      fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em",
      zIndex: 9999, boxShadow: "0 4px 20px rgba(0,0,0,0.3)",
      borderLeft: `4px solid ${colors[type] || colors.info}`,
      maxWidth: "90vw", textAlign: "center", whiteSpace: "pre-wrap",
    }}>
      {msg}
    </div>
  );
}
export default Toast;


// BPRLoading.jsx
export function BPRLoading() {
  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      background: "#1A1D2E", gap: 16,
    }}>
      <div style={{
        width: 40, height: 40, border: "3px solid rgba(255,255,255,0.15)",
        borderTopColor: "#E8192C", borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }} />
      <div style={{
        fontFamily: "'Barlow Condensed', sans-serif", fontSize: "0.85rem",
        fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.12em",
        color: "rgba(255,255,255,0.4)",
      }}>Loading Batch Record...</div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}


// BPRError.jsx
export function BPRError({ message, params }) {
  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", padding: 24,
      background: "#F4F6FA",
    }}>
      <div style={{
        background: "#fff", border: "1.5px solid #E2E6EF", borderRadius: 12,
        padding: 32, maxWidth: 400, width: "100%", textAlign: "center",
      }}>
        <div style={{
          fontFamily: "'Barlow Condensed', sans-serif", fontSize: "3rem",
          fontWeight: 900, color: "#E8192C", marginBottom: 12,
        }}>!</div>
        <div style={{
          fontFamily: "'Barlow Condensed', sans-serif", fontSize: "1.2rem",
          fontWeight: 800, textTransform: "uppercase", color: "#0F1117", marginBottom: 8,
        }}>Batch Record Error</div>
        <div style={{ fontSize: "0.88rem", color: "#4A5068", lineHeight: 1.6, marginBottom: 20 }}>
          {message}
        </div>
        {params?.uid && (
          <div style={{
            background: "#F4F6FA", borderRadius: 6, padding: "8px 12px",
            fontFamily: "monospace", fontSize: "0.78rem", color: "#8890A8",
            marginBottom: 20, wordBreak: "break-all",
          }}>
            UID: {params.uid}
          </div>
        )}
        <a
          href="javascript:history.back()"
          style={{
            display: "inline-block", padding: "10px 20px", borderRadius: 7,
            background: "#1A1D2E", color: "#fff",
            fontFamily: "'Barlow Condensed', sans-serif", fontSize: "0.9rem",
            fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em",
            textDecoration: "none",
          }}
        >← Return to BatchD</a>
      </div>
    </div>
  );
}


// BPRComplete.jsx
export function BPRComplete({ bprData, params }) {
  const bpr = bprData?.bpr || {};
  const pdfUrl = bpr.pdf_drive_url;

  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", padding: 24,
      background: "#F4F6FA",
    }}>
      <div style={{
        background: "#fff", border: "2px solid #0A7A3E", borderRadius: 14,
        padding: 32, maxWidth: 460, width: "100%",
      }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div style={{ fontSize: "2.5rem", marginBottom: 8 }}>✅</div>
          <div style={{
            fontFamily: "'Barlow Condensed', sans-serif", fontSize: "1.5rem",
            fontWeight: 900, textTransform: "uppercase", color: "#0A7A3E", letterSpacing: "0.02em",
          }}>BPR Complete</div>
          <div style={{ fontSize: "0.85rem", color: "#4A5068", marginTop: 4 }}>
            This Batch Production Record has been released and archived.
          </div>
        </div>

        {/* Batch details */}
        {[
          ["Product", params.productName || bpr.product_name],
          ["Batch ID", params.batchId || bpr.batch_id],
          ["METRC UID", params.uid || bpr.uid],
          ["Released by", bpr.supervisor_name],
          ["Completed", bpr.completed_at
            ? new Date(bpr.completed_at).toLocaleString("en-US", {
                month: "short", day: "numeric", year: "numeric",
                hour: "numeric", minute: "2-digit"
              })
            : "—"],
        ].map(([label, val]) => (
          <div key={label} style={{
            display: "flex", justifyContent: "space-between", alignItems: "flex-start",
            padding: "8px 0", borderBottom: "1px solid #E2E6EF", gap: 12,
          }}>
            <span style={{
              fontFamily: "'Barlow Condensed', sans-serif", fontSize: "0.7rem",
              fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em",
              color: "#8890A8", flex: "0 0 100px",
            }}>{label}</span>
            <span style={{
              fontSize: "0.88rem", color: "#0F1117", textAlign: "right",
              fontFamily: label === "METRC UID" ? "monospace" : "inherit",
              fontSize: label === "METRC UID" ? "0.75rem" : "0.88rem",
            }}>{val || "—"}</span>
          </div>
        ))}

        {/* Actions */}
        <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 10 }}>
          {pdfUrl && (
            <a
              href={pdfUrl}
              target="_blank"
              rel="noreferrer"
              style={{
                display: "block", padding: "12px", borderRadius: 8, textAlign: "center",
                background: "#0A7A3E", color: "#fff", textDecoration: "none",
                fontFamily: "'Barlow Condensed', sans-serif", fontSize: "0.9rem",
                fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em",
              }}
            >
              📄 View BPR PDF in Drive
            </a>
          )}
          <a
            href="javascript:history.back()"
            style={{
              display: "block", padding: "11px", borderRadius: 8, textAlign: "center",
              border: "1.5px solid #E2E6EF", color: "#4A5068", textDecoration: "none",
              fontFamily: "'Barlow Condensed', sans-serif", fontSize: "0.9rem",
              fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em",
            }}
          >← Return to BatchD</a>
        </div>

        <div style={{
          marginTop: 18, padding: "12px 14px", background: "#ECFDF3",
          borderRadius: 8, fontSize: "0.78rem", color: "#065f46", lineHeight: 1.5,
        }}>
          PDF filed automatically to the Google Drive batch folder for this UID.
          This record is now part of your DCC compliance documentation.
        </div>
      </div>
    </div>
  );
}
