import { createContext, useState, useEffect } from "react";
import api from "../api";
import { MOCK_MODE } from "../config";
import { realtimeSocket } from "../realtime/websocket.js";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  // Load user from localStorage on refresh
  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const token = localStorage.getItem("token");

    // Only restore user if token exists too
    if (storedUser && token) {
      setUser(JSON.parse(storedUser));
    }
  }, []);

  const login = async (username, password) => {
    if (MOCK_MODE) {
      if (username && password) {
        const mockUser = { username, roles: ["admin"] };
        localStorage.setItem("user", JSON.stringify(mockUser));
        localStorage.setItem("token", "mock-token");
        setUser(mockUser);
        return true;
      }
      return false;
    }

    try {
      // FastAPI OAuth2PasswordRequestForm expects x-www-form-urlencoded
      const res = await api.post("/auth/login", {
        username,
        password,
      });

      const token = res.data?.access_token || res.data?.token;
      if (!token) return false;

      localStorage.setItem("token", token);

      // Fetch current user
      const userRes = await api.get("/auth/me");
      localStorage.setItem("user", JSON.stringify(userRes.data));
      setUser(userRes.data);
      window.dispatchEvent(new Event("auth-changed"));
      return true;
    } catch (e) {
      // Optional: temporarily log during integration
      // console.error("Login failed:", e?.response?.data || e?.message);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    realtimeSocket.disconnect();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}