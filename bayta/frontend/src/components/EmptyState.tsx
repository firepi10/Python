import type { LucideIcon } from "lucide-react";

interface Props {
  icon: LucideIcon;
  title: string;
  hint?: string;
}

export function EmptyState({ icon: Icon, title, hint }: Props) {
  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 12,
        color: "var(--text-tertiary)",
      }}
    >
      <Icon size={56} strokeWidth={1.4} />
      <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text-secondary)" }}>{title}</div>
      {hint && <div style={{ fontSize: 15, maxWidth: 360, textAlign: "center" }}>{hint}</div>}
    </div>
  );
}
