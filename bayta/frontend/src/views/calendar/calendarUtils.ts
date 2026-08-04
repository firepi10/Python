import {
  addDays,
  eachDayOfInterval,
  endOfDay,
  endOfMonth,
  endOfWeek,
  startOfDay,
  startOfMonth,
  startOfWeek,
} from "date-fns";
import type { OccurrenceDTO } from "../../api/client";

export type CalView = "month" | "week" | "day";

/** Fetch range for the current view, padded to full weeks for month view. */
export function rangeFor(view: CalView, anchor: Date): { start: Date; end: Date } {
  if (view === "month") {
    return {
      start: startOfWeek(startOfMonth(anchor)),
      end: endOfWeek(endOfMonth(anchor)),
    };
  }
  if (view === "week") {
    return { start: startOfWeek(anchor), end: endOfWeek(anchor) };
  }
  return { start: startOfDay(anchor), end: endOfDay(anchor) };
}

export function daysOf(range: { start: Date; end: Date }): Date[] {
  return eachDayOfInterval({ start: range.start, end: range.end });
}

/** True when the occurrence touches the given local day. */
export function occursOn(occ: OccurrenceDTO, day: Date): boolean {
  const dayStart = startOfDay(day).getTime();
  const dayEnd = addDays(startOfDay(day), 1).getTime();
  if (occ.all_day) {
    // all-day occurrences are UTC-midnight encoded; compare by calendar date.
    // DTEND is exclusive; a degenerate end<=start still means a one-day event.
    const s = new Date(occ.start);
    const e = new Date(occ.end);
    const startDate = Date.UTC(s.getUTCFullYear(), s.getUTCMonth(), s.getUTCDate());
    const endDate = Date.UTC(e.getUTCFullYear(), e.getUTCMonth(), e.getUTCDate());
    const dayUTC = Date.UTC(day.getFullYear(), day.getMonth(), day.getDate());
    if (endDate <= startDate) return dayUTC === startDate;
    return dayUTC >= startDate && dayUTC < endDate;
  }
  const s = new Date(occ.start).getTime();
  const e = new Date(occ.end).getTime();
  return s < dayEnd && e > dayStart;
}

export function occurrencesFor(occs: OccurrenceDTO[] | undefined, day: Date): OccurrenceDTO[] {
  if (!occs) return [];
  return occs.filter((o) => occursOn(o, day));
}
