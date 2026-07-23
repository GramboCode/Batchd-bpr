export default function BPRComplete({ bprData, params }) {
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
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div style={{ fontSize: "2.5rem", marginBottom: 8 }}>✅</div>
          <div style={{
            fontFamily: "'Barlow Condensed', sans-serif", fontSize: "1.5rem",
            fontWeight: 900, textTransform: "uppercase", color: "#0A7A3E",
          }}>BPR Complete</div>
          <div style={{ fontSize: "0.85rem", color: "#4A5068", marginTop: 4 }}>
            This Batch Production Record has been released and archived.
          </div>
        </div>

        {[
          ["Product",    params?.productName || bpr.product_name],
          ["Batch ID",   params?.batchId     || bpr.batch_id],
          ["METRC UID",  params?.uid         || bpr.uid],
          ["Released by",bpr.supervisor_name],
          ["Completed",  bpr.completed_at
            ? new Date(bpr.completed_at).toLocaleString("en-US", {
                month: "short", day: "numeric", year: "numeric",
                hour: "numeric", minute: "2-digit"
              })
            : "—"],
        ].map(([label, val]) => (
          <div key={label} style={{
            display: "flex", justifyContent: "space-between",
            padding: "8px 0", borderBottom: "1px solid #E2E6EF", gap: 12,
          }}>
            <span style={{
              fontFamily: "'Barlow Condensed', sans-serif", fontSize: "0.7rem",
              fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em",
              color: "#8890A8", flex: "0 0 100px",
            }}>{label}</span>
            <span style={{
              fontSize: label === "METRC UID" ? "0.75rem" : "0.88rem",
              color: "#0F1117", textAlign: "right",
              fontFamily: label === "METRC UID" ? "monospace" : "inherit",
            }}>{val || "—"}</span>
          </div>
        ))}

        <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 10 }}>
          {pdfUrl && (
            <a href={pdfUrl} target="_blank" rel="noreferrer" style={{
              display: "block", padding: "12px", borderRadius: 8, textAlign: "center",
              background: "#0A7A3E", color: "#fff", textDecoration: "none",
              fontFamily: "'Barlow Condensed', sans-serif", fontSize: "0.9rem",
              fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em",
            }}>📄 View BPR PDF in Drive</a>
          )}
          <button
            onClick={() => {
              // This page is always opened as a new tab via window.open() from
              // the Punch Tools batch detail button, so there's no history to
              // go "back" to in this tab — that's why history.back() did
              // nothing. Closing the tab returns focus to the batch detail
              // page that's still open behind it.
              window.close();
              // Fallback for the rare case a browser blocks script-initiated
              // close (some do, if it doesn't believe the tab was opened by
              // a script) — send them somewhere sane instead of a dead button.
              setTimeout(() => {
                window.location.href = "https://batchd-bpr.netlify.app";
              }, 300);
            }}
            style={{
              display: "block", width: "100%", padding: "11px", borderRadius: 8,
              textAlign: "center", border: "1.5px solid #E2E6EF", background: "#fff",
              color: "#4A5068", cursor: "pointer",
              fontFamily: "'Barlow Condensed', sans-serif", fontSize: "0.9rem",
              fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em",
            }}
          >← Return to BatchD</button>
        </div>

        <div style={{
          marginTop: 18, padding: "12px 14px", background: "#ECFDF3",
          borderRadius: 8, fontSize: "0.78rem", color: "#065f46", lineHeight: 1.5,
        }}>
          PDF filed automatically to the Google Drive batch folder.
          This record is now part of your DCC compliance documentation.
        </div>
      </div>
    </div>
  );
}
