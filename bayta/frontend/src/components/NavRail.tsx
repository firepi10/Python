import { NavLink } from "react-router-dom";
import {
  CalendarDays,
  ClipboardCheck,
  Images,
  ListTodo,
  Settings,
  UtensilsCrossed,
  type LucideIcon,
} from "lucide-react";
import type { Orientation } from "../hooks/useOrientation";

const ITEMS: { to: string; label: string; icon: LucideIcon }[] = [
  { to: "/calendar", label: "Calendar", icon: CalendarDays },
  { to: "/meals", label: "Meals", icon: UtensilsCrossed },
  { to: "/chores", label: "Chores", icon: ClipboardCheck },
  { to: "/lists", label: "Lists", icon: ListTodo },
  { to: "/photos", label: "Photos", icon: Images },
  { to: "/settings", label: "Settings", icon: Settings },
];

/** Side rail in landscape, bottom tab bar in portrait. */
export function NavRail({ orientation }: { orientation: Orientation }) {
  const portrait = orientation === "portrait";
  return (
    <nav
      style={{
        display: "flex",
        flexDirection: portrait ? "row" : "column",
        justifyContent: portrait ? "space-around" : "flex-start",
        alignItems: "center",
        gap: portrait ? 0 : 6,
        padding: portrait ? "6px 8px calc(6px + env(safe-area-inset-bottom))" : "16px 8px",
        width: portrait ? "100%" : 92,
        flexShrink: 0,
        background: "color-mix(in srgb, var(--surface-solid) 92%, transparent)",
        borderTop: portrait ? "1px solid var(--surface-border)" : "none",
        borderRight: portrait ? "none" : "1px solid var(--surface-border)",
      }}
    >
      {ITEMS.map(({ to, label, icon: Icon }) => (
        <NavLink key={to} to={to} style={{ textDecoration: "none", width: portrait ? "auto" : "100%" }}>
          {({ isActive }) => (
            <div
              className="touch-btn"
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 3,
                padding: "10px 6px",
                borderRadius: "var(--radius-md)",
                background: isActive ? "var(--accent-soft)" : "transparent",
                color: isActive ? "var(--accent)" : "var(--text-secondary)",
                transition: `transform var(--dur-fast) var(--ease-spring)`,
              }}
            >
              <Icon size={26} strokeWidth={isActive ? 2.4 : 2} />
              <span style={{ fontSize: 11, fontWeight: 600 }}>{label}</span>
            </div>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
