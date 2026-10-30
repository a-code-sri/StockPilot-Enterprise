// API base URL. Local dev talks to uvicorn directly; the Docker image is built
// with VITE_API_BASE_URL=/api so nginx proxies to the backend (same origin).
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

function deriveWsBase() {
  if (import.meta.env.VITE_WS_BASE_URL) {
    return import.meta.env.VITE_WS_BASE_URL.replace(/\/$/, "");
  }
  if (API_BASE_URL.startsWith("/")) {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}${API_BASE_URL}`;
  }
  return API_BASE_URL.replace(/^http/, "ws");
}

export const WS_BASE_URL = deriveWsBase();
