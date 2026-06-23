export default function BPRError({ message, params }) {
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
