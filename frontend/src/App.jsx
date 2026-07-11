import { useState, useEffect } from "react";
import BPRForm from "./pages/BPRForm";
import BPRComplete from "./pages/BPRComplete";
import BPRError from "./pages/BPRError";
import BPRLoading from "./pages/BPRLoading";

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
    returnUrl:   p.get("returnUrl")   || "",
  };
}

export const API_BASE = import.meta.env.VITE_API_URL || "https://your-railway-app.railway.app";

export default function App() {
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
      // First check if BPR already exists
      const statusRes = await fetch(`${API_BASE}/bpr/${params.uid}/status`);
      const statusData = await statusRes.json();

      if (statusData.exists && statusData.status === "completed") {
        // Already done — show complete screen
        const fullRes = await fetch(`${API_BASE}/bpr/${params.uid}`);
        const fullData = await fullRes.json();
        setBprData(fullData);
        setView("complete");
        return;
      }

      if (statusData.exists) {
        // In progress — load it
        const fullRes = await fetch(`${API_BASE}/bpr/${params.uid}`);
        if (!fullRes.ok) throw new Error("Failed to load existing BPR");
        const fullData = await fullRes.json();
        setBprData(fullData);
        setView("form");
        return;
      }

      // Create new BPR
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
  if (view === "error")   return <BPRError message={errorMsg} params={params} />;
  if (view === "complete") return <BPRComplete bprData={bprData} params={params} />;
  if (view === "form")    return (
    <BPRForm
      bprData={bprData}
      setBprData={setBprData}
      params={params}
      onComplete={onComplete}
    />
  );
}
