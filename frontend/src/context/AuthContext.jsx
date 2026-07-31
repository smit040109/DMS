import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import api, { formatApiErrorDetail } from "@/lib/api";

const AuthContext = createContext(null);

const IMPERSONATE_KEY = "go_oil_impersonation";
const TOKEN_KEY = "go_oil_token";

function readImpersonation() {
  try {
    const raw = localStorage.getItem(IMPERSONATE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = anon, obj = user
  const [error, setError] = useState("");
  const [impersonation, setImpersonation] = useState(readImpersonation());

  const bootstrap = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data.user);
    } catch {
      setUser(false);
    }
  }, []);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const login = async (email, password) => {
    setError("");
    try {
      const { data } = await api.post("/auth/login", { email, password });
      if (data.token) localStorage.setItem(TOKEN_KEY, data.token);
      localStorage.removeItem(IMPERSONATE_KEY);
      setImpersonation(null);
      setUser(data.user);
      return { ok: true };
    } catch (e) {
      const msg = formatApiErrorDetail(e.response?.data?.detail) || e.message;
      setError(msg);
      return { ok: false, error: msg };
    }
  };

  const register = async (payload) => {
    setError("");
    try {
      const { data } = await api.post("/auth/register", payload);
      if (data.token) localStorage.setItem(TOKEN_KEY, data.token);
      setUser(data.user);
      return { ok: true };
    } catch (e) {
      const msg = formatApiErrorDetail(e.response?.data?.detail) || e.message;
      setError(msg);
      return { ok: false, error: msg };
    }
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(IMPERSONATE_KEY);
    setImpersonation(null);
    setUser(false);
  };

  const switchRole = (role) => {
    if (!user) return;
    setUser({ ...user, role });
  };

  /**
   * Impersonate another user (owner only).
   * Saves current owner token so we can switch back.
   */
  const startImpersonation = async (uid) => {
    try {
      const currentToken = localStorage.getItem(TOKEN_KEY);
      const { data } = await api.post(`/dms/owner/impersonate/${uid}`);
      if (!data.token) throw new Error("No token returned");
      const record = {
        owner_token: currentToken,
        owner_user: user,
        target_user: data.user,
        started_at: new Date().toISOString(),
      };
      localStorage.setItem(TOKEN_KEY, data.token);
      localStorage.setItem(IMPERSONATE_KEY, JSON.stringify(record));
      setImpersonation(record);
      setUser(data.user);
      return { ok: true, user: data.user };
    } catch (e) {
      const msg = formatApiErrorDetail(e.response?.data?.detail) || e.message;
      return { ok: false, error: msg };
    }
  };

  /** Exit impersonation and restore owner session. */
  const exitImpersonation = () => {
    const rec = readImpersonation();
    if (!rec) return;
    if (rec.owner_token) {
      localStorage.setItem(TOKEN_KEY, rec.owner_token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
    localStorage.removeItem(IMPERSONATE_KEY);
    setImpersonation(null);
    setUser(rec.owner_user || false);
  };

  return (
    <AuthContext.Provider value={{
      user, error, login, register, logout, switchRole,
      impersonation, startImpersonation, exitImpersonation,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
