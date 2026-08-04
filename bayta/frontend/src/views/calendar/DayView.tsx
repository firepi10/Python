import { format } from "date-fns";
import { CalendarDays } from "lucide-react";
import { profileColorVar, type OccurrenceDTO } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { occurrencesFor } from "./calendarUtils";

interface Props {
  anchor: Date;
  occurrences: OccurrenceDTO[] | undefined;
  onEventTap: (occ: OccurrenceDTO) => void;
}

export function DayView({ anchor, occurrences, onEventTap }: Props) {
  const dayOccs = occurrencesFor(occurrences, anchor);
  if (dayOccs.length === 0) {
    return <EmptyState icon={CalendarDays} title="Nothing planned" hint="Tap + to add something." />;
  }
  return (
    <div
      style={{
        height: "100%",
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        maxWidth: 720,
        margin: "0 auto",
        width: "100%",
      }}
    >
      {dayOccs.map((occ) => {
        const color = profileColorVar(occ.color);
        return (
          <button
            key={`${occ.event_id}-${occ.start}`}
            onClick={() => onEventTap(occ)}
            className="touch-btn"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 16,
              border: "1px solid var(--surface-border)",
              background: "var(--surface-solid)",
              borderRadius: "var(--radius-md)",
              boxShadow: "var(--shadow-card)",
              padding: "14px 18px",
              textAlign: "left",
              fontFamily: "inherit",
              color: "var(--text)",
              transition: `transform var(--dur-fast) var(--ease-spring)`,
            }}
          >
            <div style={{ width: 5, alignSelf: "stretch", borderRadius: 3, background: color }} />
            <div className="tnum" style={{ width: 110, flexShrink: 0 }}>
              {occ.all_day ? (
                <span style={{ fontWeight: 700, fontSize: 15 }}>All day</span>
              ) : (
                <>
                  <div style={{ fontWeight: 700, fontSize: 17 }}>
                    {format(new Date(occ.start), "h:mm a")}
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: 13 }}>
                    {format(new Date(occ.end), "h:mm a")}
                  </div>
                </>
              )}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 17, fontWeight: 700 }}>{occ.summary}</div>
              {(occ.location || occ.profile_name) && (
                <div style={{ color: "var(--text-secondary)", fontSize: 14, marginTop: 2 }}>
                  {[occ.profile_name, occ.location].filter(Boolean).join(" · ")}
                </div>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
