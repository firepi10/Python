import { format } from "date-fns";
import { profileColorVar, type OccurrenceDTO } from "../../api/client";

interface Props {
  occ: OccurrenceDTO;
  onClick?: () => void;
  showTime?: boolean;
}

export function EventChip({ occ, onClick, showTime = true }: Props) {
  const color = profileColorVar(occ.color);
  return (
    <button
      onClick={onClick}
      className="touch-btn"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        width: "100%",
        border: "none",
        textAlign: "left",
        fontFamily: "inherit",
        borderRadius: 7,
        padding: "3px 8px",
        fontSize: 13,
        fontWeight: 600,
        color: "var(--text)",
        background: `color-mix(in srgb, ${color} 16%, transparent)`,
        overflow: "hidden",
        whiteSpace: "nowrap",
        transition: `transform var(--dur-fast) var(--ease-spring)`,
      }}
    >
      <span
        aria-hidden
        style={{
          width: 4,
          height: 14,
          borderRadius: 2,
          background: color,
          flexShrink: 0,
        }}
      />
      {showTime && !occ.all_day && (
        <span className="tnum" style={{ color: "var(--text-secondary)", fontWeight: 500, flexShrink: 0 }}>
          {format(new Date(occ.start), "h:mm")}
        </span>
      )}
      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{occ.summary}</span>
    </button>
  );
}
