import { useMemo, useState } from "react";
import { addDays, addMonths, addWeeks, format } from "date-fns";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { api, type OccurrenceDTO } from "../../api/client";
import { SegmentedControl } from "../../components/SegmentedControl";
import { TouchButton } from "../../components/TouchButton";
import { rangeFor, type CalView } from "./calendarUtils";
import { DayView } from "./DayView";
import { EventSheet, type SheetState } from "./EventSheet";
import { MonthView } from "./MonthView";
import { WeekView } from "./WeekView";

export function CalendarView() {
  const [view, setView] = useState<CalView>("month");
  const [anchor, setAnchor] = useState(() => new Date());
  const [sheet, setSheet] = useState<SheetState | null>(null);

  const range = useMemo(() => rangeFor(view, anchor), [view, anchor]);
  const { data: occurrences } = useQuery({
    queryKey: ["occurrences", range.start.toISOString(), range.end.toISOString()],
    queryFn: () => api.occurrences(range.start.toISOString(), range.end.toISOString()),
  });

  const step = (dir: 1 | -1) => {
    if (view === "month") setAnchor((a) => addMonths(a, dir));
    else if (view === "week") setAnchor((a) => addWeeks(a, dir));
    else setAnchor((a) => addDays(a, dir));
  };

  const title =
    view === "day" ? format(anchor, "EEEE, MMMM d") : format(anchor, "MMMM yyyy");

  const openEdit = (occ: OccurrenceDTO) =>
    setSheet({ mode: "edit", eventId: occ.event_id, occ });

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, flex: 1 }}>{title}</h1>
        <div style={{ width: 300 }}>
          <SegmentedControl
            options={[
              { value: "month", label: "Month" },
              { value: "week", label: "Week" },
              { value: "day", label: "Day" },
            ]}
            value={view}
            onChange={setView}
          />
        </div>
        <TouchButton variant="secondary" size="sm" onClick={() => step(-1)} aria-label="Previous">
          <ChevronLeft size={20} style={{ display: "block" }} />
        </TouchButton>
        <TouchButton variant="secondary" size="sm" onClick={() => setAnchor(new Date())}>
          Today
        </TouchButton>
        <TouchButton variant="secondary" size="sm" onClick={() => step(1)} aria-label="Next">
          <ChevronRight size={20} style={{ display: "block" }} />
        </TouchButton>
        <TouchButton
          variant="primary"
          size="sm"
          onClick={() => setSheet({ mode: "create", defaultDay: anchor })}
          aria-label="Add event"
        >
          <Plus size={20} style={{ display: "block" }} />
        </TouchButton>
      </div>

      <div style={{ flex: 1, minHeight: 0 }}>
        {view === "month" && (
          <MonthView
            anchor={anchor}
            occurrences={occurrences}
            onDayTap={(day) => {
              setAnchor(day);
              setView("day");
            }}
            onEventTap={openEdit}
          />
        )}
        {view === "week" && (
          <WeekView
            anchor={anchor}
            occurrences={occurrences}
            onEventTap={openEdit}
            onSlotTap={(day, hour) => setSheet({ mode: "create", defaultDay: day, defaultHour: hour })}
          />
        )}
        {view === "day" && (
          <DayView anchor={anchor} occurrences={occurrences} onEventTap={openEdit} />
        )}
      </div>

      <EventSheet state={sheet} onClose={() => setSheet(null)} />
    </div>
  );
}
