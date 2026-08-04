import { Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { NavRail } from "../components/NavRail";
import { TopBar } from "../components/TopBar";
import { useIdle } from "../hooks/useIdle";
import { useOrientation } from "../hooks/useOrientation";
import { Screensaver } from "./screensaver/Screensaver";

interface ScreensaverSettings {
  enabled: boolean;
  interval_s: number;
  ken_burns: boolean;
}

/** Root layout: TopBar on top; NavRail left (landscape) or bottom (portrait).
 *  After the idle timeout the Ken Burns screensaver covers the shell. */
export function KioskShell() {
  const orientation = useOrientation();
  const portrait = orientation === "portrait";

  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const saver = (settings?.screensaver as ScreensaverSettings | undefined) ?? {
    enabled: true,
    interval_s: 12,
    ken_burns: true,
  };
  const idleTimeout = ((settings?.idle_timeout_s as number | undefined) ?? 300) * 1000;
  const idle = useIdle(idleTimeout, saver.enabled);

  return (
    <div
      className="kiosk"
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: "var(--bg-gradient)",
      }}
    >
      <TopBar />
      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: portrait ? "column" : "row",
        }}
      >
        {!portrait && <NavRail orientation={orientation} />}
        <main style={{ flex: 1, minWidth: 0, minHeight: 0, overflow: "hidden", padding: 20 }}>
          <Outlet />
        </main>
        {portrait && <NavRail orientation={orientation} />}
      </div>
      {idle && <Screensaver intervalS={saver.interval_s} kenBurns={saver.ken_burns} />}
    </div>
  );
}
