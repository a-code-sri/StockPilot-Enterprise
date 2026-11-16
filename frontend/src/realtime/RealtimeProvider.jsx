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
 * Calls `onUpdate` when the worker reports that the analytics of `modules`
 * (a module name or an array of them) changed. Bursts of events (e.g. a batch
 * import) are debounced into one refresh.
 */
export function useAnalyticsRefresh(modules, onUpdate, delayMs = 400) {
  const { lastEvent } = useRealtime();
  const callback = useRef(onUpdate);
  callback.current = onUpdate;
  const key = [].concat(modules).join(",");
  const timer = useRef(null);

  useEffect(() => {
    if (lastEvent?.type !== "analytics.updated" || !key.split(",").includes(lastEvent?.module)) return;
    // Only matching events restart the debounce. Events for other modules (a dispatch sends
    // inventory and delivery events together) must not cancel a pending refresh.
    clearTimeout(timer.current);
    timer.current = setTimeout(() => callback.current(), delayMs);
  }, [lastEvent, key, delayMs]);

  useEffect(() => () => clearTimeout(timer.current), []);
}
