"""Build and parse iCalendar payloads for events.

The raw ICS text is the source of truth on the `events` row; these helpers
keep the denormalized columns (summary, dtstart_utc, ...) in agreement.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from icalendar import Calendar as ICalendar
from icalendar import Event as IEvent

PRODID = "-//Bayta//Family Hub//EN"


def new_uid() -> str:
    return f"bayta-{uuid.uuid4()}@bayta.local"


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def build_event_ics(
    *,
    uid: str,
    summary: str,
    dtstart: datetime | date,
    dtend: datetime | date,
    all_day: bool,
    location: str | None = None,
    description: str | None = None,
    rrule: str | None = None,
    timezone: str = "UTC",
) -> str:
    cal = ICalendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")

    ev = IEvent()
    ev.add("uid", uid)
    ev.add("summary", summary)
    def as_date(value: datetime | date) -> date:
        return value.date() if isinstance(value, datetime) else value

    if all_day:
        start_d = as_date(dtstart)
        end_d = as_date(dtend)
        if end_d <= start_d:
            # DTEND is exclusive: a one-day event ends the next morning.
            end_d = start_d + timedelta(days=1)
        ev.add("dtstart", start_d)
        ev.add("dtend", end_d)
    else:
        tz = ZoneInfo(timezone)
        assert isinstance(dtstart, datetime) and isinstance(dtend, datetime)
        ev.add("dtstart", to_utc(dtstart).astimezone(tz))
        ev.add("dtend", to_utc(dtend).astimezone(tz))
    if location:
        ev.add("location", location)
    if description:
        ev.add("description", description)
    if rrule:
        from icalendar.prop import vRecur

        ev.add("rrule", vRecur.from_ical(rrule))
    ev.add("dtstamp", datetime.now(UTC))
    cal.add_component(ev)
    return cal.to_ical().decode()


def _first_vevent(ics_text: str) -> IEvent:
    cal = ICalendar.from_ical(ics_text)
    for component in cal.walk("VEVENT"):
        # The master component has no RECURRENCE-ID; overrides do.
        if component.get("recurrence-id") is None:
            return component
    for component in cal.walk("VEVENT"):
        return component
    raise ValueError("no VEVENT in payload")


def parse_event_ics(ics_text: str) -> dict:
    """Denormalize the master VEVENT into DB columns."""
    ev = _first_vevent(ics_text)

    dtstart = ev.decoded("dtstart")
    all_day = isinstance(dtstart, date) and not isinstance(dtstart, datetime)

    if "dtend" in ev:
        dtend = ev.decoded("dtend")
    elif "duration" in ev:
        dtend = dtstart + ev.decoded("duration")
    else:
        dtend = dtstart

    if all_day:
        start_utc = datetime(dtstart.year, dtstart.month, dtstart.day, tzinfo=UTC)
        end_utc = datetime(dtend.year, dtend.month, dtend.day, tzinfo=UTC)
    else:
        start_utc = to_utc(dtstart)
        end_utc = to_utc(dtend)

    return {
        "uid": str(ev.get("uid", "")),
        "summary": str(ev.get("summary", "")),
        "location": str(ev["location"]) if ev.get("location") else None,
        "dtstart_utc": start_utc,
        "dtend_utc": end_utc,
        "all_day": all_day,
        "is_recurring": ev.get("rrule") is not None or ev.get("rdate") is not None,
    }
