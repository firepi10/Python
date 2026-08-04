import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const styles: Record<Variant, React.CSSProperties> = {
  primary: { background: "var(--accent)", color: "#fff" },
  secondary: { background: "var(--surface-solid)", color: "var(--text)", boxShadow: "var(--shadow-card)" },
  ghost: { background: "transparent", color: "var(--accent)" },
  danger: { background: "var(--danger)", color: "#fff" },
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md" | "lg";
  children: ReactNode;
}

/** Apple-style button with a haptic-feeling press: scales down on :active.
 *  GPU rule: only transform/opacity are animated. */
export function TouchButton({ variant = "secondary", size = "md", style, children, ...rest }: Props) {
  const pad = size === "sm" ? "8px 14px" : size === "lg" ? "16px 28px" : "12px 20px";
  const font = size === "sm" ? 14 : size === "lg" ? 18 : 16;
  return (
    <button
      {...rest}
      className={`touch-btn ${rest.className ?? ""}`}
      style={{
        border: "none",
        borderRadius: "var(--radius-md)",
        padding: pad,
        fontSize: font,
        fontWeight: 600,
        fontFamily: "inherit",
        transition: `transform var(--dur-fast) var(--ease-spring), opacity var(--dur-fast) ease`,
        ...styles[variant],
        ...style,
      }}
    >
      {children}
    </button>
  );
}
