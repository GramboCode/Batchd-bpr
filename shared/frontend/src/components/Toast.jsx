export default function Toast({ msg, type = "info" }) {
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
