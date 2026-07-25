// src/pages/Login.jsx — the one page GAS gave you for free (Google's own
// session) and React doesn't: a place to actually sign in.
//
// Loads Google's Identity Services script itself on mount, rather than
// assuming it's already in index.html — keeps this page self-contained
// while the rest of the migration is still in flight.
import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

// Same Client ID as the backend's GOOGLE_OAUTH_CLIENT_ID — Google embeds
// the client ID as the token's "aud" (audience) claim, and the backend
// rejects any token whose aud doesn't match. If login mysteriously 401s
// with a valid-looking Google token, this mismatch is the first thing to check.
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const buttonRef = useRef(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) {
      setError("VITE_GOOGLE_CLIENT_ID is not set in Netlify's env vars.");
      return;
    }

    function renderButton() {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleCredentialResponse,
      });
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "filled_black",
        size: "large",
        text: "signin_with",
        shape: "pill",
      });
    }

    // Script may already be present (e.g. navigating back to /login
    // without a full page reload) — don't inject it twice.
    if (window.google?.accounts?.id) {
      renderButton();
      return;
    }
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = renderButton;
    document.body.appendChild(script);
    // No cleanup/removal on unmount: Google's own script is safe to leave
    // cached in the page for the rare case the user navigates back here.
  }, []);

  // `response.credential` is the Google ID token (a signed JWT from
  // Google) — this is the thing that gets POSTed to /auth/login.
  async function handleCredentialResponse(response) {
    try {
      await login(response.credential);
      const dest = location.state?.from || "/";
      navigate(dest, { replace: true });
    } catch (e) {
      setError(e.message || "Login failed");
    }
  }

  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", gap: 24,
      background: "#1A1D2E",
    }}>
      <div style={{
        fontFamily: "'Barlow Condensed', sans-serif", fontSize: "1.8rem",
        fontWeight: 900, color: "#fff", textTransform: "uppercase",
        letterSpacing: "0.04em",
      }}>
        <span style={{ background: "#E8192C", padding: "5px 14px", borderRadius: 7 }}>
          BATCHD
        </span>
      </div>
      <div ref={buttonRef} />
      {error && (
        <div style={{
          color: "#FCA5A5", fontSize: "0.85rem", maxWidth: 320,
          textAlign: "center", lineHeight: 1.5,
        }}>
          {error}
        </div>
      )}
    </div>
  );
}
