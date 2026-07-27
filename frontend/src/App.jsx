// App.jsx — BatchD frontend root
// v2: react-router structure. Routes:
//   /                        → Components Dashboard (or BPR flow if ?uid= present —
//                              printed QR codes deep-link to the root URL and must
//                              keep working forever)
//   /components/:lotCode     → Lot detail (ledger view)
//   /bpr                     → BPR flow, explicit path (same query params as root)
import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import BPRForm from "./pages/BPRForm";
import BPRComplete from "./pages/BPRComplete";
import BPRError from "./pages/BPRError";
import BPRLoading from "./pages/BPRLoading";
import Dashboard from "./pages/Dashboard";
import NewComponent from "./pages/NewComponent";
import LotDetail from "./pages/LotDetail";
import PunchDashboard from "./pages/PunchDashboard";
import BatchDetail from "./pages/BatchDetail";
import Login from "./pages/Login";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { getToken } from "./lib/api";

// ── Read URL params ────────────────────────────────────────────────────────
function getParams() {
  const p = new URLSearchParams(window.location.search);
  return {
    uid:         p.get("uid")         || "",
    productName: p.get("product")     || p.get("productName") || "",
    batchId:     p.get("batchId")     || p.get("batch_id")    || "",
    mfgDate:     p.get("mfgDate")     || p.get("mfg_date")    || "",
    category:    p.get("category")    || "",
    bprType:     p.get("bprType")     || p.get("bpr_type")    || "",
    lotCode:     p.get("lotCode")     || p.get("lot_code")    || "",
    returnUrl:   p.get("returnUrl")   || "",
  };
}

export const API_BASE = import.meta.env.VITE_API_URL || "https://batchd-bpr-production.up.railway.app";

// ── API key: attach to every request aimed at our backend ─────────────
// Wrapping fetch once covers every call site in the app — only URLs
// starting with API_BASE are decorated; third-party fetches untouched.
const _origFetch = window.fetch.bind(window);
window.fetch = (url, opts = {}) => {
  if (typeof url === "string" && url.startsWith(API_BASE)) {
    // Both headers ride together on purpose: legacy routes (bpr.py,
    // components.py) still only check X-API-Key today, while new routes
    // (tracker.py, and anything migrated later) check the Bearer JWT.
    // Sending both means no route cares which auth era it's from.
    const token = getToken();
    opts = {
      ...opts,
      headers: {
        ...(opts.headers || {}),
        "X-API-Key": import.meta.env.VITE_BATCHD_API_KEY || "",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    };
  }
  return _origFetch(url, opts);
};

// Fetch the full BPR record for a UID. Both the "already completed" and the
// "exists but still in progress" branches need the identical pull, so it lives
// in one helper instead of being copy-pasted. (The missing version of exactly
// this function is what threw "loadFull is not defined" and blocked the app.)
async function loadFull(uid) {
  const res = await fetch(`${API_BASE}/bpr/${uid}`);
  if (!res.ok) throw new Error("Failed to load batch record (" + res.status + ")");
  return res.json();
}

// ── The original param-driven BPR flow, unchanged, as its own component ──
function BPRFlow() {
  const [view, setView] = useState("loading"); // loading | form | complete | error
  const [bprData, setBprData] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");
  const params = getParams();

  useEffect(() => {
    if (!params.uid) {
      setErrorMsg("No batch UID provided. Open this page from the BatchD batch detail.");
      setView("error");
      return;
    }
    if (!params.productName) {
      setErrorMsg("No product name provided. Return to BatchD and re-open BPR.");
      setView("error");
      return;
    }
    initBPR();
  }, []);

  async function initBPR() {
    try {
      const statusRes = await fetch(`${API_BASE}/bpr/${params.uid}/status`);
      const statusData = await statusRes.json();

      if (statusData.exists && statusData.status === "completed") {
        const fullData = await loadFull(statusData.uid);
        setBprData(fullData);
        setView("complete");
        return;
      }

      if (statusData.exists) {
        const fullData = await loadFull(statusData.uid);   // ← was params.uid
        setBprData(fullData);
        setView(statusData.status === "completed" ? "complete" : "form");
        return;
      }

      const createRes = await fetch(`${API_BASE}/bpr/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          uid:          params.uid,
          product_name: params.productName,
          batch_id:     params.batchId,
          mfg_date:     params.mfgDate,
          category:     params.category,
          bpr_type:     params.bprType,
        }),
      });

      if (!createRes.ok) {
        const err = await createRes.json();
        throw new Error(err.detail || "Failed to create BPR");
      }

      const created = await createRes.json();
      setBprData(created);
      setView("form");

    } catch (e) {
      setErrorMsg(e.message || "Failed to initialize batch record. Check your connection.");
      setView("error");
    }
  }

  function onComplete(completedData) {
    setBprData(prev => ({ ...prev, bpr: { ...prev.bpr, ...completedData } }));
    setView("complete");
  }

  if (view === "loading") return <BPRLoading />;
  if (view === "error")   return <BPRError message={errorMsg} params={getParams()} />;
  if (view === "complete") return <BPRComplete bprData={bprData} params={getParams()} />;
  return (
    <BPRForm
      bprData={bprData}
      setBprData={setBprData}
      params={getParams()}
      onComplete={onComplete}
    />
  );
}

// ── Root route: QR deep links (with ?uid=) get the BPR flow; bare visits
//    get the Punch Tools batch dashboard — this is what keeps every
//    printed QR working while also making "/" the real landing page. ─────
function RootRoute() {
  const location = useLocation();
  const hasUid = new URLSearchParams(location.search).get("uid");
  if (hasUid) return <BPRFlow />;
  return (
    <ProtectedRoute>
      <PunchDashboard />
    </ProtectedRoute>
  );
}

// ── Gate for pages that require a logged-in user ──────────────────────────
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Still checking whether a stored token is valid — render nothing
  // rather than flashing the login screen for a split second.
  if (loading) return null;

  if (!user) {
    // Remember where they were headed so Login can send them back
    // after a successful sign-in, instead of always landing on "/".
    return <Navigate to="/login" state={{ from: location.pathname + location.search }} replace />;
  }
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<RootRoute />} />
          <Route path="/batch/:uid" element={<ProtectedRoute><BatchDetail /></ProtectedRoute>} />
          <Route path="/bpr" element={<BPRFlow />} />
          <Route path="/login" element={<Login />} />
          <Route path="/components" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/components/new" element={<ProtectedRoute><NewComponent /></ProtectedRoute>} />
          <Route path="/components/:lotCode" element={<ProtectedRoute><LotDetail /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
