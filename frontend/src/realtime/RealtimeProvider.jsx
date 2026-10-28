import { createContext, useContext, useEffect, useState } from "react";
import { realtimeSocket } from "./websocket";

const RealtimeContext = createContext({
  status: "disconnected",
  lastEvent: null,
});

export function RealtimeProvider({ children }) {
  const [status, setStatus] = useState("disconnected");
  const [lastEvent, setLastEvent] = useState(null);

  useEffect(() => {
    const unsubscribeEvents = realtimeSocket.subscribe((event) => {
      setLastEvent(event);
    });

    const unsubscribeStatus = realtimeSocket.onStatusChange((nextStatus) => {
      setStatus(nextStatus);
    });

    realtimeSocket.connect();

    return () => {
      unsubscribeEvents();
      unsubscribeStatus();
      realtimeSocket.disconnect();
    };
  }, []);

  useEffect(() => {
    const handleAuthChange = () => {
      realtimeSocket.disconnect();
      realtimeSocket.connect();
    };

    window.addEventListener("auth-changed", handleAuthChange);

    return () => {
      window.removeEventListener("auth-changed", handleAuthChange);
    };
  }, []);

  return (
    <RealtimeContext.Provider
      value={{
        status,
        lastEvent,
      }}
    >
      {children}
    </RealtimeContext.Provider>
  );
}

export function useRealtime() {
  return useContext(RealtimeContext);
}