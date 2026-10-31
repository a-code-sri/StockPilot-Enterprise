import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import api, { TOKEN_KEY, errorMessage } from "../api";
import { realtimeSocket } from "../realtime/websocket.js";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // True until we know whether a stored token is still valid.
  const [restoring, setRestoring] = useState(() => Boolean(localStorage.getItem(TOKEN_KEY)));

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("user"); // written by older versions
    realtimeSocket.disconnect();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const res = await api.get("/auth/me");
    setUser(res.data);
    return res.data;
  }, []);

  // Restore the session on page load (token survives refreshes; profile is re-fetched).
  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) return;
    refreshUser()
      .then(() => realtimeSocket.connect())
      .catch(() => logout())
      .finally(() => setRestoring(false));
  }, [refreshUser, logout]);

  useEffect(() => {
    window.addEventListener("auth-expired", logout);
    return () => window.removeEventListener("auth-expired", logout);
  }, [logout]);

  const login = useCallback(
    async (username, password) => {
      try {
        const res = await api.post("/auth/login", { username, password });
        localStorage.setItem(TOKEN_KEY, res.data.access_token);
        await refreshUser();
        realtimeSocket.reconnect();
        return { ok: true };
      } catch (e) {
        localStorage.removeItem(TOKEN_KEY);
        return { ok: false, error: errorMessage(e, "Login failed") };
      }
    },
    [refreshUser]
  );

  const can = useCallback((permission) => Boolean(user?.permissions?.includes(permission)), [user]);

  // After a password change the server revokes old tokens and hands back a new one.
  const replaceToken = useCallback((token) => {
    localStorage.setItem(TOKEN_KEY, token);
    realtimeSocket.reconnect();
  }, []);

  const value = useMemo(
    () => ({ user, restoring, login, logout, can, refreshUser, replaceToken }),
    [user, restoring, login, logout, can, refreshUser, replaceToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
