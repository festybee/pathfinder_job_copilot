import { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as api from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!api.getToken()) {
      setLoading(false);
      return;
    }
    api
      .fetchMe()
      .then(setUser)
      .catch(() => api.setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const doLogin = useCallback(async (username, password) => {
    const data = await api.login(username, password);
    api.setToken(data.token);
    setUser(data.user);
  }, []);

  const doSignup = useCallback(async (username, email, password) => {
    const data = await api.signup(username, email, password);
    // New accounts are inactive until an admin approves them in /admin/,
    // so signup no longer returns a token - nothing to log in with yet.
    // Return the raw response so the caller (SignupPage) can show the
    // pending-approval message instead of assuming it's now logged in.
    if (data.token) {
      api.setToken(data.token);
      setUser(data.user);
    }
    return data;
  }, []);

  const doLogout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // token may already be invalid - clear locally regardless
    }
    api.setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login: doLogin, signup: doSignup, logout: doLogout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
