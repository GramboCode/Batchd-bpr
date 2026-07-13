// AppHeader.jsx — shared nav for the BatchD app (dashboard + lot detail).
// Deliberately NOT rendered on the BPR flow: operators arriving via QR get
// the focused, distraction-free BPR view they have today.
//
// EXTERNAL_LINKS: fill in the two GAS web app URLs. As the BATCHD webapp
// migrates to Railway, these external links graduate into real routes here
// and the constants get deleted — this header is the future app shell.
import { Link, useLocation } from "react-router-dom";
import "./AppHeader.css";

const EXTERNAL_LINKS = {
  // GAS wash page (New Wash Batch) — paste the /exec URL:
  newWashBatch: "PASTE-GAS-WASH-PAGE-URL",
  // GAS Punch Tools batch dashboard — paste the /exec URL:
  punchTools: "PASTE-GAS-PUNCH-TOOLS-URL",
};

export default function AppHeader() {
  const location = useLocation();
  const onInventory = location.pathname === "/" || location.pathname.startsWith("/components");

  return (
    <header className="app-header">
      <div className="app-header-inner">
        <Link to="/" className="app-brand">
          <span className="app-brand-punch">BATCHD</span>
          <span className="app-brand-sub">Punch Tools</span>
        </Link>
        <nav className="app-nav">
          <Link to="/" className={`app-nav-link ${onInventory ? "nav-on" : ""}`}>
            Inventory
          </Link>
          <a className="app-nav-link" href={EXTERNAL_LINKS.newWashBatch}
             target="_blank" rel="noreferrer">
            New Wash Batch ↗
          </a>
          <a className="app-nav-link" href={EXTERNAL_LINKS.punchTools}
             target="_blank" rel="noreferrer">
            Batch Dashboard ↗
          </a>
        </nav>
      </div>
    </header>
  );
}
