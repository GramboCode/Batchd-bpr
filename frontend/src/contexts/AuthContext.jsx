// src/contexts/AuthContext.jsx — who's logged in, app-wide.
//
// Wraps the whole app (see App.jsx) so any page can call useAuth() to get
// { user, loading, login, logout } without prop-drilling it down through
// the router.
import { createContext, useContext, useState, useEffect } from "react";
import { fetchCurrentUser, loginWithGoogle, logout as clearStoredToken } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);      // { email, role } | null
  const [loading, setLoading] = useState(true); // true until the initial token check finishes

  // On first mount, if a token is already sitting in localStorage from a
  // previous session, confirm it's still valid before showing anything
  // that assumes a logged-out state.
  useEffect(() => {
    fetchCurrentUser().then(u => {
      setUser(u);
      setLoading(false);
    });
  }, []);

  // Takes the Google ID token from the Sign-In button, exchanges it for
  // our JWT, and updates state. Throws on failure so Login.jsx can show
  // the error inline.
  async function login(googleIdToken) {
    const data = await loginWithGoogle(googleIdToken);
    setUser({ email: data.email, role: data.role });
  }

  function logout() {
    clearStoredToken();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
