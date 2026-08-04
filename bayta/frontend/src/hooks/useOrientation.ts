import { useEffect, useState } from "react";

export type Orientation = "landscape" | "portrait";

export function useOrientation(): Orientation {
  const [orientation, setOrientation] = useState<Orientation>(() =>
    typeof window !== "undefined" && window.matchMedia("(orientation: portrait)").matches
      ? "portrait"
      : "landscape",
  );
  useEffect(() => {
    const mq = window.matchMedia("(orientation: portrait)");
    const onChange = (e: MediaQueryListEvent) => setOrientation(e.matches ? "portrait" : "landscape");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return orientation;
}
