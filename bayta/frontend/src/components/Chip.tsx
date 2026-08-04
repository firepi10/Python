import type { ReactNode } from "react";

interface Props {
  color?: string;
  children: ReactNode;
  onClick?: () => void;
}

/** Compact rounded label, tinted with a profile color. */
export function Chip({ color = "var(--accent)", children, onClick }: Props) {
  const Tag = onClick ? "button" : "span";
  return (
    <Tag
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        border: "none",
        fontFamily: "inherit",
        borderRadius: 999,
        padding: "4px 12px",
        fontSize: 13,
        fontWeight: 600,
        color: "var(--text)",
        background: `color-mix(in srgb, ${color} 16%, transparent)`,
      }}
    >
      <span
        aria-hidden
        style={{ width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0 }}
      />
      {children}
    </Tag>
  );
}
