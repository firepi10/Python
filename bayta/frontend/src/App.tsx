import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import { format } from "date-fns";
import { useClock } from "./hooks/useClock";

function applyTheme() {
  const hour = new Date().getHours();
  const dark = hour >= 19 || hour < 7;
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}

function HomeShell() {
  const now = useClock();
  return (
    <div
      className="kiosk flex h-full flex-col items-center justify-center"
      style={{ background: "var(--bg-gradient)" }}
    >
      <div className="tnum text-[16vw] font-thin leading-none tracking-tight" data-testid="clock">
        {format(now, "h:mm")}
      </div>
      <div className="mt-4 text-[2.2vw] font-light" style={{ color: "var(--text-secondary)" }}>
        {format(now, "EEEE, MMMM d")}
      </div>
      <div
        className="absolute bottom-10 text-[1.2vw] font-medium tracking-[0.3em] uppercase"
        style={{ color: "var(--text-tertiary)" }}
      >
        Bayta
      </div>
    </div>
  );
}

export default function App() {
  useEffect(() => {
    applyTheme();
    const id = setInterval(applyTheme, 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <Routes>
      <Route path="/" element={<HomeShell />} />
    </Routes>
  );
}
