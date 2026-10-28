import { useEffect, useRef } from "react";

export function usePolling(fn, intervalMs, enabled = true) {
  const savedFn = useRef(fn);

  useEffect(() => {
    savedFn.current = fn;
  }, [fn]);

  useEffect(() => {
    if (!enabled) return;

    let timer = null;

    const tick = async () => {
      try {
        await savedFn.current();
      } finally {
        timer = setTimeout(tick, intervalMs);
      }
    };

    tick();
    return () => timer && clearTimeout(timer);
  }, [intervalMs, enabled]);
}