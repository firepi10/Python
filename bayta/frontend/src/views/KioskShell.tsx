import { Outlet } from "react-router-dom";
import { NavRail } from "../components/NavRail";
import { TopBar } from "../components/TopBar";
import { useOrientation } from "../hooks/useOrientation";

/** Root layout: TopBar on top; NavRail left (landscape) or bottom (portrait). */
export function KioskShell() {
  const orientation = useOrientation();
  const portrait = orientation === "portrait";
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
    </div>
  );
}
