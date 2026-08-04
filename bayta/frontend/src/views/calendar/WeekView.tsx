import { format, isSameDay } from "date-fns";
import { profileColorVar, type OccurrenceDTO } from "../../api/client";
import { daysOf, occurrencesFor, rangeFor } from "./calendarUtils";
import { EventChip } from "./EventChip";

interface Props {
  anchor: Date;
  occurrences: OccurrenceDTO[] | undefined;
  onEventTap: (occ: OccurrenceDTO) => void;
  onSlotTap: (day: Date, hour: number) => void;
}

const START_HOUR = 7;
const END_HOUR = 22;
const HOURS = Array.from({ length: END_HOUR - START_HOUR }, (_, i) => START_HOUR + i);
const HOUR_PX = 56;

function eventBlockStyle(occ: OccurrenceDTO): React.CSSProperties {
  const s = new Date(occ.start);
  const e = new Date(occ.end);
  const startH = s.getHours() + s.getMinutes() / 60;
  const endH = e.getHours() + e.getMinutes() / 60 || 24;
  const top = Math.max(0, (startH - START_HOUR) * HOUR_PX);
  const height = Math.max(24, (Math.min(endH, END_HOUR) - Math.max(startH, START_HOUR)) * HOUR_PX - 2);
  const color = profileColorVar(occ.color);
  return {
    position: "absolute",
    top,
    height,
    left: 2,
    right: 2,
    borderRadius: 8,
    background: `color-mix(in srgb, ${color} 20%, var(--surface-solid))`,
    borderLeft: `3px solid ${color}`,
    padding: "4px 6px",
    overflow: "hidden",
    fontSize: 12.5,
    fontWeight: 600,
    textAlign: "left",
    border: "none",
    fontFamily: "inherit",
    color: "var(--text)",
    cursor: "pointer",
  };
}

export function WeekView({ anchor, occurrences, onEventTap, onSlotTap }: Props) {
  const days = daysOf(rangeFor("week", anchor));
  const today = new Date();

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 4 }}>
      {/* day headers + all-day row */}
      <div style={{ display: "grid", gridTemplateColumns: `52px repeat(7, 1fr)`, gap: 4 }}>
        <div />
        {days.map((day) => {
          const isToday = isSameDay(day, today);
          return (
            <div key={day.toISOString()} style={{ textAlign: "center", paddingBottom: 2 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>
                {format(day, "EEE")}
              </div>
              <div
                className="tnum"
                style={{
                  margin: "2px auto 0",
                  fontSize: 17,
                  fontWeight: isToday ? 800 : 600,
                  color: isToday ? "#fff" : "var(--text)",
                  background: isToday ? "var(--accent)" : "transparent",
                  borderRadius: 999,
                  width: 30,
                  height: 30,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {format(day, "d")}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 2, marginTop: 2 }}>
                {occurrencesFor(occurrences, day)
                  .filter((o) => o.all_day)
                  .slice(0, 2)
                  .map((occ) => (
                    <EventChip
                      key={`${occ.event_id}-${occ.start}`}
                      occ={occ}
                      showTime={false}
                      onClick={() => onEventTap(occ)}
                    />
                  ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* timed grid */}
      <div style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `52px repeat(7, 1fr)`,
            gap: 4,
            height: HOURS.length * HOUR_PX,
          }}
        >
          <div style={{ position: "relative" }}>
            {HOURS.map((h, i) => (
              <div
                key={h}
                className="tnum"
                style={{
                  position: "absolute",
                  top: i * HOUR_PX - 7,
                  right: 6,
                  fontSize: 11,
                  fontWeight: 600,
                  color: "var(--text-tertiary)",
                }}
              >
                {format(new Date(2000, 0, 1, h), "h a")}
              </div>
            ))}
          </div>
          {days.map((day) => (
            <div
              key={day.toISOString()}
              style={{
                position: "relative",
                background: "var(--surface-solid)",
                border: "1px solid var(--surface-border)",
                borderRadius: "var(--radius-sm)",
              }}
              onClick={(e) => {
                const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
                const hour = START_HOUR + Math.floor((e.clientY - rect.top) / HOUR_PX);
                onSlotTap(day, hour);
              }}
            >
              {HOURS.slice(1).map((h, i) => (
                <div
                  key={h}
                  aria-hidden
                  style={{
                    position: "absolute",
                    top: (i + 1) * HOUR_PX,
                    left: 0,
                    right: 0,
                    borderTop: "1px solid var(--surface-border)",
                  }}
                />
              ))}
              {occurrencesFor(occurrences, day)
                .filter((o) => !o.all_day)
                .map((occ) => (
                  <button
                    key={`${occ.event_id}-${occ.start}`}
                    style={eventBlockStyle(occ)}
                    onClick={(e) => {
                      e.stopPropagation();
                      onEventTap(occ);
                    }}
                  >
                    <div style={{ whiteSpace: "nowrap", textOverflow: "ellipsis", overflow: "hidden" }}>
                      {occ.summary}
                    </div>
                    <div className="tnum" style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
                      {format(new Date(occ.start), "h:mm")}–{format(new Date(occ.end), "h:mm a")}
                    </div>
                  </button>
                ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
