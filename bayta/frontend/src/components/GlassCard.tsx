import type { HTMLAttributes, ReactNode } from "react";

interface Props extends HTMLAttributes<HTMLDivElement> {
  /** True glass (backdrop blur). GPU budget: at most ONE blurred surface on
   *  screen at a time on the Pi — cards default to a solid elevated surface. */
  blur?: boolean;
  padding?: number | string;
  children: ReactNode;
}

export function GlassCard({ blur = false, padding = 20, style, children, ...rest }: Props) {
  return (
    <div
      {...rest}
      className={`${blur ? "glass" : ""} ${rest.className ?? ""}`}
      style={{
        background: blur ? undefined : "var(--surface-solid)",
        border: blur ? undefined : "1px solid var(--surface-border)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-card)",
        padding,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
