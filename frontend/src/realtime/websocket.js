import { WS_BASE_URL } from "../config";
import { TOKEN_KEY } from "../api";

/**
 * Authenticated, auto-reconnecting WebSocket for server push events.
 *
 * Protocol: after the socket opens we send {"type":"auth","token":...}; the server
 * answers {"type":"ready"} and then pushes events such as
 * {"type":"analytics.updated","module":"inventory"}.
 */
class RealtimeSocket {
  constructor() {
    this.socket = null;
    this.listeners = new Set();
    this.statusListeners = new Set();
    this.status = "disconnected";
    this.reconnectTimer = null;
    this.reconnectAttempts = 0;
    this.shouldReconnect = false;
  }

  connect() {
    this.shouldReconnect = true;
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      this.setStatus("unauthenticated");
      return;
    }

    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;

    const socket = new WebSocket(`${WS_BASE_URL}/ws/realtime`);
    this.socket = socket;
    this.setStatus("connecting");

    socket.onopen = () => {
      if (this.socket !== socket) return;
      socket.send(JSON.stringify({ type: "auth", token }));
    };

    socket.onmessage = (event) => {
      if (this.socket !== socket) return;
      let message;
      try {
        message = JSON.parse(event.data);
      } catch {
        return;
      }
      if (message.type === "ready") {
        this.reconnectAttempts = 0;
        this.setStatus("connected");
        return;
      }
      for (const listener of this.listeners) listener(message);
    };

    socket.onclose = (event) => {
      if (this.socket === socket) this.socket = null;
      // 1008 = policy violation (bad/expired token): don't hammer the server.
      if (event.code === 1008) {
        this.setStatus("unauthenticated");
        return;
      }
      this.setStatus("disconnected");
      if (this.shouldReconnect) this.scheduleReconnect();
    };
  }

  reconnect() {
    this.disconnect();
    this.connect();
  }

  disconnect() {
    this.shouldReconnect = false;
    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    const socket = this.socket;
    this.socket = null;
    if (socket) socket.close(1000, "Client disconnected");
    this.setStatus("disconnected");
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  onStatusChange(listener) {
    this.statusListeners.add(listener);
    listener(this.status);
    return () => this.statusListeners.delete(listener);
  }

  setStatus(status) {
    this.status = status;
    for (const listener of this.statusListeners) listener(status);
  }

  scheduleReconnect() {
    if (this.reconnectTimer || !this.shouldReconnect) return;
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      if (this.shouldReconnect) this.connect();
    }, delay);
  }
}

export const realtimeSocket = new RealtimeSocket();
