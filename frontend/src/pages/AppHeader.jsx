// AppHeader.jsx — shared nav for the BatchD app (dashboard + lot detail).
// Deliberately NOT rendered on the BPR flow: operators arriving via QR get
// the focused, distraction-free BPR view they have today.
//
// EXTERNAL_LINKS: fill in the two GAS web app URLs. As the BATCHD webapp
// migrates to Railway, these external links graduate into real routes here
// and the constants get deleted — this header is the future app shell.
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import "./AppHeader.css";

export const EXTERNAL_LINKS = {
  // "New Component" is now a NATIVE React flow (/components/new) — no longer a
  // GAS link. See NewComponent.jsx. (The old ?page=wash GAS page is retired.)
  // GAS create page (New Batch) — same deployment, ?page=create. Batch
  // creation isn't migrated to React yet (heavy GAS logic: template clone,
  // UID assignment, folder creation), so this links out for now — same
  // pattern as newComponent until /create grows a native React flow.
  newBatch: "https://script.google.com/a/macros/punchedibles.com/s/AKfycbxJpIgvk2ghXgG2GZCIYCFoQwSLrT2SVCaoKG3-T4X2rbJnsAi37XjvStrfaQeKNj6u/exec?page=create",
  // GAS Punch Tools batch dashboard — paste the /exec URL:
  punchTools: "https://script.google.com/macros/s/AKfycbxJpIgvk2ghXgG2GZCIYCFoQwSLrT2SVCaoKG3-T4X2rbJnsAi37XjvStrfaQeKNj6u/exec",
};

export default function AppHeader() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const onBatches   = location.pathname === "/";
  const onInventory = location.pathname.startsWith("/components");

  return (
    <header className="app-header">
      <div className="app-header-inner">
        <Link to="/" className="app-brand">
          <span className="app-brand-punch">BATCHD</span>
          <span className="app-brand-sub">Punch Tools</span>
        </Link>
        <nav className="app-nav">
          <Link to="/" className={`app-nav-link ${onBatches ? "nav-on" : ""}`}>
            Batches
          </Link>
          <Link to="/components" className={`app-nav-link ${onInventory ? "nav-on" : ""}`}>
            Components
          </Link>
          {/* "New Component" moved to the Components dashboard (top-right),
              mirroring "New Batch" on the Batches dashboard. */}
          <a className="app-nav-link" href={EXTERNAL_LINKS.punchTools}
             target="_blank" rel="noreferrer">
            Legacy GAS Dashboard ↗
          </a>
        </nav>
        {user && (
          <div className="app-user">
            <span className="app-user-email">{user.email}</span>
            <button className="app-user-logout" onClick={logout}>Sign out</button>
          </div>
        )}
      </div>
    </header>
  );
}
