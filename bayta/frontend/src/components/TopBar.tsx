import { format } from "date-fns";
import { useClock } from "../hooks/useClock";
import { WeatherChip } from "./WeatherChip";

/** Persistent header: date on the left, live clock on the right.
 *  Solid-tint surface (not blur) — the Sheet owns the app's blur budget. */
export function TopBar() {
  const now = useClock();
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 28px",
        height: 64,
        flexShrink: 0,
        background: "color-mix(in srgb, var(--surface-solid) 92%, transparent)",
        borderBottom: "1px solid var(--surface-border)",
      }}
    >
      <div style={{ fontSize: 20, fontWeight: 700 }}>
        {format(now, "EEEE")}{" "}
        <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
          {format(now, "MMMM d")}
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <WeatherChip />
        <div className="tnum" style={{ fontSize: 26, fontWeight: 300 }} data-testid="clock">
          {format(now, "h:mm")}
          <span style={{ color: "var(--text-tertiary)", fontSize: 17, marginLeft: 6 }}>
            {format(now, "a")}
          </span>
        </div>
      </div>
    </header>
  );
}
