export default function BPRLoading() {
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
