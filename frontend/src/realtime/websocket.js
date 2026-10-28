import { WS_BASE_URL } from "../config";

class RealtimeSocket {
  constructor() {
    this.socket = null;

    this.listeners = new Set();
    this.statusListeners = new Set();

    this.reconnectTimer = null;
    this.reconnectAttempts = 0;

    this.shouldReconnect = false;
  }

  connect() {
    this.shouldReconnect = true;

    if (
      this.socket &&
      (
        this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING
      )
    ) {
      return;
    }

    const token = localStorage.getItem("token");

    if (!token) {
      this.setStatus("unauthenticated");
      return;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    const url =
      `${WS_BASE_URL}/ws/realtime?token=${encodeURIComponent(token)}`;

    console.log("Connecting to realtime WebSocket...");

    const socket = new WebSocket(url);

    this.socket = socket;
    this.setStatus("connecting");

    socket.onopen = () => {
      // Ignore callbacks from an old socket.
      if (this.socket !== socket) {
        return;
      }

      console.log("Realtime WebSocket connected");

      this.reconnectAttempts = 0;
      this.setStatus("connected");
    };

    socket.onmessage = (event) => {
      // Ignore messages from an old socket.
      if (this.socket !== socket) {
        return;
      }

      try {
        const message = JSON.parse(event.data);

        console.log("Realtime event:", message);

        for (const listener of this.listeners) {
          listener(message);
        }
      } catch (error) {
        console.error(
          "Invalid realtime WebSocket message:",
          error
        );
      }
    };

    socket.onclose = (event) => {
      // Only clean up the currently active socket.
      if (this.socket === socket) {
        this.socket = null;
      }

      console.log(
        "Realtime WebSocket closed:",
        event.code,
        event.reason
      );

      this.setStatus("disconnected");

      if (this.shouldReconnect) {
        this.scheduleReconnect();
      }
    };

    socket.onerror = (error) => {
      if (this.socket !== socket) {
        return;
      }

      console.error(
        "Realtime WebSocket error:",
        error
      );
    };
  }

  disconnect() {
    this.shouldReconnect = false;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    const socket = this.socket;
    this.socket = null;

    if (socket) {
      socket.close(1000, "Client disconnected");
    }

    this.setStatus("disconnected");
  }

  subscribe(listener) {
    this.listeners.add(listener);

    return () => {
      this.listeners.delete(listener);
    };
  }

  onStatusChange(listener) {
    this.statusListeners.add(listener);

    return () => {
      this.statusListeners.delete(listener);
    };
  }

  setStatus(status) {
    for (const listener of this.statusListeners) {
      listener(status);
    }
  }

  scheduleReconnect() {
    if (this.reconnectTimer) {
      return;
    }

    if (!this.shouldReconnect) {
      return;
    }

    const token = localStorage.getItem("token");

    if (!token) {
      this.setStatus("unauthenticated");
      return;
    }

    const delay = Math.min(
      1000 * 2 ** this.reconnectAttempts,
      30000
    );

    console.log(
      `Realtime WebSocket reconnecting in ${delay}ms`
    );

    this.reconnectAttempts += 1;

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;

      if (!this.shouldReconnect) {
        return;
      }

      this.connect();
    }, delay);
  }
}

export const realtimeSocket = new RealtimeSocket();