import { useEffect, useState } from "react";
import { addDays, format } from "date-fns";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, profileColorVar, type EventInput, type OccurrenceDTO } from "../../api/client";
import { Avatar } from "../../components/Avatar";
import { Sheet } from "../../components/Sheet";
import { TouchButton } from "../../components/TouchButton";
import { useToast } from "../../components/Toast";

export interface SheetState {
  mode: "create" | "edit";
  eventId?: number;
  occ?: OccurrenceDTO;
  defaultDay?: Date;
  defaultHour?: number;
}

interface Props {
  state: SheetState | null;
  onClose: () => void;
}

const REPEAT_OPTIONS = [
  { value: "", label: "Never" },
  { value: "FREQ=DAILY", label: "Every day" },
  { value: "FREQ=WEEKLY", label: "Every week" },
  { value: "FREQ=MONTHLY", label: "Every month" },
  { value: "FREQ=YEARLY", label: "Every year" },
];

const field: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  border: "1px solid var(--surface-border)",
  background: "var(--bg)",
  color: "var(--text)",
  borderRadius: "var(--radius-sm)",
  padding: "12px 14px",
  fontSize: 16,
  fontFamily: "inherit",
};

const label: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 700,
  color: "var(--text-secondary)",
  marginBottom: 6,
  display: "block",
};

export function EventSheet({ state, onClose }: Props) {
  const queryClient = useQueryClient();
  const toast = useToast();

  const [summary, setSummary] = useState("");
  const [location, setLocation] = useState("");
  const [allDay, setAllDay] = useState(false);
  const [date, setDate] = useState("");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [repeat, setRepeat] = useState("");
  const [profileId, setProfileId] = useState<number | null>(null);

  const { data: profiles } = useQuery({ queryKey: ["profiles"], queryFn: api.profiles });

  useEffect(() => {
    if (!state) return;
    if (state.mode === "edit" && state.occ) {
      const occ = state.occ;
      setSummary(occ.summary);
      setLocation(occ.location ?? "");
      setAllDay(occ.all_day);
      setProfileId(occ.profile_id);
      const s = new Date(occ.start);
      const e = new Date(occ.end);
      setDate(format(occ.all_day ? new Date(occ.start.slice(0, 10) + "T12:00:00") : s, "yyyy-MM-dd"));
      setStartTime(format(s, "HH:mm"));
      setEndTime(format(e, "HH:mm"));
      setRepeat("");
    } else {
      const day = state.defaultDay ?? new Date();
      const hour = state.defaultHour ?? 9;
      setSummary("");
      setLocation("");
      setAllDay(false);
      setDate(format(day, "yyyy-MM-dd"));
      setStartTime(`${String(hour).padStart(2, "0")}:00`);
      setEndTime(`${String(Math.min(hour + 1, 23)).padStart(2, "0")}:00`);
      setRepeat("");
      setProfileId(null);
    }
  }, [state]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["occurrences"] });

  const save = useMutation({
    mutationFn: async () => {
      let body: EventInput;
      if (allDay) {
        const startISO = `${date}T00:00:00Z`;
        const endISO = `${format(addDays(new Date(`${date}T12:00:00`), 1), "yyyy-MM-dd")}T00:00:00Z`;
        body = {
          summary,
          all_day: true,
          start: startISO,
          end: endISO,
          location: location || null,
          rrule: repeat || null,
          profile_id: profileId,
        };
      } else {
        body = {
          summary,
          all_day: false,
          start: new Date(`${date}T${startTime}`).toISOString(),
          end: new Date(`${date}T${endTime}`).toISOString(),
          location: location || null,
          rrule: repeat || null,
          profile_id: profileId,
        };
      }
      if (state?.mode === "edit" && state.eventId) {
        return api.updateEvent(state.eventId, body);
      }
      return api.createEvent(body);
    },
    onSuccess: () => {
      invalidate();
      toast(state?.mode === "edit" ? "Event updated" : "Event added");
      onClose();
    },
    onError: () => toast("Couldn't save — check the times"),
  });

  const remove = useMutation({
    mutationFn: async () => {
      if (state?.eventId) await api.deleteEvent(state.eventId);
    },
    onSuccess: () => {
      invalidate();
      toast("Event deleted");
      onClose();
    },
  });

  return (
    <Sheet
      open={state !== null}
      onClose={onClose}
      title={state?.mode === "edit" ? "Edit event" : "New event"}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <input
          style={{ ...field, fontSize: 19, fontWeight: 600 }}
          placeholder="Event title"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          autoFocus={state?.mode === "create"}
        />
        <input
          style={field}
          placeholder="Location (optional)"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
        />

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 16, fontWeight: 600 }}>All-day</span>
          <TouchButton
            variant={allDay ? "primary" : "secondary"}
            size="sm"
            onClick={() => setAllDay(!allDay)}
          >
            {allDay ? "On" : "Off"}
          </TouchButton>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: allDay ? "1fr" : "1fr 1fr 1fr", gap: 12 }}>
          <div>
            <span style={label}>Date</span>
            <input type="date" style={field} value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          {!allDay && (
            <>
              <div>
                <span style={label}>Starts</span>
                <input
                  type="time"
                  style={field}
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                />
              </div>
              <div>
                <span style={label}>Ends</span>
                <input
                  type="time"
                  style={field}
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                />
              </div>
            </>
          )}
        </div>

        {profiles && profiles.length > 0 && (
          <div>
            <span style={label}>Who</span>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {profiles.map((p) => {
                const selected = profileId === p.id;
                return (
                  <button
                    key={p.id}
                    onClick={() => setProfileId(selected ? null : p.id)}
                    className="touch-btn"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      border: selected
                        ? `2px solid ${profileColorVar(p.color)}`
                        : "2px solid transparent",
                      background: selected
                        ? `color-mix(in srgb, ${profileColorVar(p.color)} 12%, transparent)`
                        : "var(--bg)",
                      borderRadius: 999,
                      padding: "5px 14px 5px 6px",
                      fontFamily: "inherit",
                      fontSize: 15,
                      fontWeight: 600,
                      color: "var(--text)",
                      transition: `transform var(--dur-fast) var(--ease-spring)`,
                    }}
                  >
                    <Avatar name={p.name} color={profileColorVar(p.color)} size={28} />
                    {p.name}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div>
          <span style={label}>Repeat</span>
          <select style={field} value={repeat} onChange={(e) => setRepeat(e.target.value)}>
            {REPEAT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
          {state?.mode === "edit" && (
            <TouchButton variant="danger" onClick={() => remove.mutate()} disabled={remove.isPending}>
              Delete
            </TouchButton>
          )}
          <div style={{ flex: 1 }} />
          <TouchButton variant="secondary" onClick={onClose}>
            Cancel
          </TouchButton>
          <TouchButton
            variant="primary"
            onClick={() => save.mutate()}
            disabled={!summary.trim() || save.isPending}
          >
            {state?.mode === "edit" ? "Save" : "Add"}
          </TouchButton>
        </div>
      </div>
    </Sheet>
  );
}
