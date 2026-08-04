import { format, isSameDay, isSameMonth } from "date-fns";
import type { OccurrenceDTO } from "../../api/client";
import { daysOf, occurrencesFor, rangeFor } from "./calendarUtils";
import { EventChip } from "./EventChip";

interface Props {
  anchor: Date;
  occurrences: OccurrenceDTO[] | undefined;
  onDayTap: (day: Date) => void;
  onEventTap: (occ: OccurrenceDTO) => void;
  maxChips?: number;
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function MonthView({ anchor, occurrences, onDayTap, onEventTap, maxChips = 3 }: Props) {
  const days = daysOf(rangeFor("month", anchor));
  const today = new Date();
  const weeks = days.length / 7;

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 6 }}>
        {WEEKDAYS.map((d) => (
          <div
            key={d}
            style={{
              textAlign: "center",
              fontSize: 12,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-tertiary)",
              padding: "2px 0",
            }}
          >
            {d}
          </div>
        ))}
      </div>
      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gridTemplateRows: `repeat(${weeks}, 1fr)`,
          gap: 6,
        }}
      >
        {days.map((day) => {
          const dayOccs = occurrencesFor(occurrences, day);
          const inMonth = isSameMonth(day, anchor);
          const isToday = isSameDay(day, today);
          const overflow = dayOccs.length - maxChips;
          return (
            <div
              key={day.toISOString()}
              onClick={() => onDayTap(day)}
              style={{
                background: "var(--surface-solid)",
                border: "1px solid var(--surface-border)",
                borderRadius: "var(--radius-sm)",
                padding: 6,
                display: "flex",
                flexDirection: "column",
                gap: 3,
                overflow: "hidden",
                opacity: inMonth ? 1 : 0.45,
                minHeight: 0,
              }}
            >
              <div
                className="tnum"
                style={{
                  alignSelf: "flex-start",
                  fontSize: 14,
                  fontWeight: isToday ? 800 : 600,
                  color: isToday ? "#fff" : "var(--text-secondary)",
                  background: isToday ? "var(--accent)" : "transparent",
                  borderRadius: 999,
                  minWidth: 24,
                  height: 24,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "0 6px",
                }}
              >
                {format(day, "d")}
              </div>
              {dayOccs.slice(0, maxChips).map((occ) => (
                <EventChip
                  key={`${occ.event_id}-${occ.start}`}
                  occ={occ}
                  onClick={() => onEventTap(occ)}
                />
              ))}
              {overflow > 0 && (
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)" }}>
                  +{overflow} more
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
