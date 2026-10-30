import { createContext, useContext, useEffect, useRef, useState } from "react";
import { realtimeSocket } from "./websocket";

const RealtimeContext = createContext({ status: "disconnected", lastEvent: null });

export function RealtimeProvider({ children }) {
  const [status, setStatus] = useState(realtimeSocket.status);
  const [lastEvent, setLastEvent] = useState(null);

  useEffect(() => {
    const offEvents = realtimeSocket.subscribe(setLastEvent);
    const offStatus = realtimeSocket.onStatusChange(setStatus);
    return () => {
      offEvents();
      offStatus();
    };
  }, []);

  return <RealtimeContext.Provider value={{ status, lastEvent }}>{children}</RealtimeContext.Provider>;
}

export function useRealtime() {
  return useContext(RealtimeContext);
}

/**
 * Calls `onUpdate` when the worker reports that `module`'s analytics changed.
 * Bursts of events (e.g. a batch import) are debounced into one refresh.
 */
export function useAnalyticsRefresh(module, onUpdate, delayMs = 400) {
  const { lastEvent } = useRealtime();
  const callback = useRef(onUpdate);
  callback.current = onUpdate;

  useEffect(() => {
    if (lastEvent?.type !== "analytics.updated" || lastEvent?.module !== module) return;
    const t = setTimeout(() => callback.current(), delayMs);
    return () => clearTimeout(t);
  }, [lastEvent, module, delayMs]);
}
