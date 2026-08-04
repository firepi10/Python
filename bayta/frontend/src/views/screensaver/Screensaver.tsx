import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { useClock } from "../../hooks/useClock";

interface Slide {
  url: string;
  width: number;
  height: number;
}

async function fetchSlides(): Promise<Slide[]> {
  const res = await fetch("/api/photos/slideshow?limit=60");
  if (!res.ok) return [];
  return res.json();
}

/** Full-screen Ken Burns slideshow. GPU rules: the pan/zoom is a transform
 *  animation and the crossfade is an opacity transition — nothing else moves.
 *  Two stacked layers alternate; the next image is preloaded before its turn. */
export function Screensaver({ intervalS = 12, kenBurns = true }: { intervalS?: number; kenBurns?: boolean }) {
  const { data: slides } = useQuery({
    queryKey: ["slideshow"],
    queryFn: fetchSlides,
    refetchInterval: 10 * 60_000,
  });
  const [index, setIndex] = useState(0);
  const [frontIsA, setFrontIsA] = useState(true);
  const now = useClock(1000);
  const advanceRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const count = slides?.length ?? 0;

  useEffect(() => {
    if (count === 0) return;
    advanceRef.current = setInterval(() => {
      setIndex((i) => (i + 1) % count);
      setFrontIsA((f) => !f);
    }, intervalS * 1000);
    return () => {
      if (advanceRef.current) clearInterval(advanceRef.current);
    };
  }, [count, intervalS]);

  // preload the upcoming image
  useEffect(() => {
    if (!slides || count === 0) return;
    const img = new Image();
    img.src = slides[(index + 1) % count].url;
  }, [slides, index, count]);

  if (!slides || count === 0) return null;

  const current = slides[index % count];
  const previous = slides[(index - 1 + count) % count];
  const layerA = frontIsA ? current : previous;
  const layerB = frontIsA ? previous : current;

  const layerStyle = (visible: boolean, key: string): React.CSSProperties => ({
    position: "absolute",
    inset: 0,
    width: "100%",
    height: "100%",
    objectFit: "cover",
    opacity: visible ? 1 : 0,
    transition: "opacity 1600ms ease",
    animation: kenBurns && visible ? `bayta-kenburns ${intervalS + 4}s ease-out forwards` : undefined,
    willChange: "transform, opacity",
    // restart the animation whenever the image changes
    ...(key ? {} : {}),
  });

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "#000",
        zIndex: 50,
        overflow: "hidden",
        cursor: "none",
      }}
      data-testid="screensaver"
    >
      <img key={`a-${layerA.url}`} src={layerA.url} alt="" style={layerStyle(frontIsA, layerA.url)} />
      <img key={`b-${layerB.url}`} src={layerB.url} alt="" style={layerStyle(!frontIsA, layerB.url)} />
      <div
        aria-hidden
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: 180,
          background: "linear-gradient(transparent, rgba(0,0,0,0.55))",
        }}
      />
      <div style={{ position: "absolute", left: 36, bottom: 28, color: "#fff" }}>
        <div className="tnum" style={{ fontSize: 64, fontWeight: 300, lineHeight: 1 }}>
          {format(now, "h:mm")}
        </div>
        <div style={{ fontSize: 20, fontWeight: 500, opacity: 0.85, marginTop: 6 }}>
          {format(now, "EEEE, MMMM d")}
        </div>
      </div>
    </div>
  );
}
