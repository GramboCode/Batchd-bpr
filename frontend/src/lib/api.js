// src/lib/api.js — JWT storage + the /auth/* calls.
//
// This is the React-side equivalent of auth.py on the backend: it owns
// where the token lives and how it gets attached to requests. Everything
// else that needs "is someone logged in, and who" should go through
// AuthContext (contexts/AuthContext.jsx), not this file directly.
//
// NOTE on API_BASE: App.jsx already exports this same constant, but
// importing it here would create a circular import (App.jsx imports
// getToken from this file, for its fetch wrapper). Duplicating one line
// is cheaper than untangling that, so it's redefined identically below —
// if VITE_API_URL or the Railway URL ever changes, update both spots.
const API_BASE = import.meta.env.VITE_API_URL || "https://batchd-bpr-production.up.railway.app";

const TOKEN_KEY = "batchd_jwt";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// Exchanges a Google ID token (handed to us by the Sign-In button) for our
// own short-lived JWT. Throws on failure — the caller (AuthContext.login)
// should try/catch and show the message.
export async function loginWithGoogle(googleIdToken) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ google_token: googleIdToken }),
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    // 401 = bad/expired Google token, 403 = valid Google token but the
    // email isn't on the Workspace domain or the extra allowlist. Either
    // way, backend sends a human-readable string in `detail`.
    throw new Error(typeof data.detail === "string" ? data.detail : "Login failed");
  }

  // { access_token, token_type, email, role, expires_in_minutes }
  setToken(data.access_token);
  return data;
}

// Confirms a stored token is still valid and fetches who it belongs to.
// Returns null instead of throwing on any failure — on app load, "no
// valid token" just means "show the login page," not an error to surface.
export async function fetchCurrentUser() {
  const token = getToken();
  if (!token) return null;

  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      clearToken(); // expired/invalid — don't keep sending a dead token
      return null;
    }
    return await res.json(); // { email, role }
  } catch {
    return null; // network blip — treat like logged out rather than crash
  }
}

export function logout() {
  clearToken();
}
