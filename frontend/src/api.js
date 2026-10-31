import axios from "axios";
import { API_BASE_URL } from "./config";

export const TOKEN_KEY = "token";

const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// An expired or revoked token logs the user out everywhere (AuthContext listens).
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLogin = error.config?.url?.startsWith("/auth/login");
    if (error.response?.status === 401 && !isLogin && localStorage.getItem(TOKEN_KEY)) {
      window.dispatchEvent(new Event("auth-expired"));
    }
    return Promise.reject(error);
  }
);

/** Human-readable message from an axios error, including FastAPI 422 validation lists. */
export function errorMessage(error, fallback = "Something went wrong.") {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const field = (d.loc || []).filter((p) => p !== "body").join(".");
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join("; ");
  }
  if (typeof detail === "string") return detail;
  if (error?.code === "ERR_NETWORK") return "Cannot reach the server. Is the backend running?";
  return error?.message || fallback;
}

export default api;
