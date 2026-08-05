"""RRULE expansion into the `occurrences` cache via recurring-ical-events
(handles RRULE, EXDATE, RDATE and RECURRENCE-ID overrides)."""

from datetime import UTC, date, datetime, timedelta

import recurring_ical_events
from icalendar import Calendar as ICalendar

# Expansion window relative to "now". Past 365 days so a yearly event (a
# birthday) always caches at least its next two occurrences; ranges beyond this
# are expanded on demand by calendar_service.
WINDOW_PAST_DAYS = 35
WINDOW_FUTURE_DAYS = 800


def default_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(UTC)
    return now - timedelta(days=WINDOW_PAST_DAYS), now + timedelta(days=WINDOW_FUTURE_DAYS)


def expand_ics(
    ics_text: str, window_start: datetime, window_end: datetime
) -> list[tuple[datetime, datetime, bool]]:
    """Return concrete (start_utc, end_utc, all_day) tuples inside the window."""
    cal = ICalendar.from_ical(ics_text)
    out: list[tuple[datetime, datetime, bool]] = []
    for ev in recurring_ical_events.of(cal).between(window_start, window_end):
        dtstart = ev.decoded("dtstart")
        all_day = isinstance(dtstart, date) and not isinstance(dtstart, datetime)
        if "dtend" in ev:
            dtend = ev.decoded("dtend")
        elif "duration" in ev:
            dtend = dtstart + ev.decoded("duration")
        else:
            dtend = dtstart
        if all_day:
            start = datetime(dtstart.year, dtstart.month, dtstart.day, tzinfo=UTC)
            end = datetime(dtend.year, dtend.month, dtend.day, tzinfo=UTC)
        else:
            start = dtstart.astimezone(UTC)
            end = dtend.astimezone(UTC)
        out.append((start, end, all_day))
    out.sort(key=lambda t: t[0])
    return out
