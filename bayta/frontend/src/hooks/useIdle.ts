import { useEffect, useRef, useState } from "react";

/** True after `timeoutMs` without touch/keyboard activity. */
export function useIdle(timeoutMs: number, enabled = true): boolean {
  const [idle, setIdle] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!enabled) {
      setIdle(false);
      return;
    }
    const arm = () => {
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setIdle(true), timeoutMs);
    };
    const wake = () => {
      setIdle(false);
      arm();
    };
    const events = ["pointerdown", "pointermove", "keydown", "wheel"] as const;
    events.forEach((e) => window.addEventListener(e, wake, { passive: true }));
    arm();
    return () => {
      events.forEach((e) => window.removeEventListener(e, wake));
      if (timer.current) clearTimeout(timer.current);
    };
  }, [timeoutMs, enabled]);

  return idle;
}
