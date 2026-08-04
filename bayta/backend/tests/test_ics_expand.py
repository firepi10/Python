from datetime import UTC, datetime

from app.services.ics import build_event_ics, new_uid, parse_event_ics
from app.sync.ics_expand import expand_ics


def test_roundtrip_timed_event():
    ics = build_event_ics(
        uid=new_uid(),
        summary="Dentist",
        dtstart=datetime(2026, 8, 10, 14, 0, tzinfo=UTC),
        dtend=datetime(2026, 8, 10, 15, 0, tzinfo=UTC),
        all_day=False,
        location="Main St",
        timezone="America/New_York",
    )
    fields = parse_event_ics(ics)
    assert fields["summary"] == "Dentist"
    assert fields["location"] == "Main St"
    assert fields["dtstart_utc"] == datetime(2026, 8, 10, 14, 0, tzinfo=UTC)
    assert fields["all_day"] is False
    assert fields["is_recurring"] is False


def test_weekly_rrule_with_exdate():
    ics = "\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//test//EN",
            "BEGIN:VEVENT",
            "UID:weekly-1",
            "SUMMARY:Soccer",
            "DTSTART:20260803T210000Z",
            "DTEND:20260803T223000Z",
            "RRULE:FREQ=WEEKLY;BYDAY=MO",
            "EXDATE:20260817T210000Z",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )
    occs = expand_ics(
        ics,
        datetime(2026, 8, 1, tzinfo=UTC),
        datetime(2026, 8, 31, tzinfo=UTC),
    )
    starts = [o[0] for o in occs]
    assert datetime(2026, 8, 3, 21, 0, tzinfo=UTC) in starts
    assert datetime(2026, 8, 10, 21, 0, tzinfo=UTC) in starts
    assert datetime(2026, 8, 17, 21, 0, tzinfo=UTC) not in starts  # EXDATE
    assert datetime(2026, 8, 24, 21, 0, tzinfo=UTC) in starts


def test_recurrence_override_moves_instance():
    ics = "\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//test//EN",
            "BEGIN:VEVENT",
            "UID:daily-1",
            "SUMMARY:Standup",
            "DTSTART:20260803T130000Z",
            "DTEND:20260803T131500Z",
            "RRULE:FREQ=DAILY;COUNT=3",
            "END:VEVENT",
            "BEGIN:VEVENT",
            "UID:daily-1",
            "RECURRENCE-ID:20260804T130000Z",
            "SUMMARY:Standup (moved)",
            "DTSTART:20260804T160000Z",
            "DTEND:20260804T161500Z",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )
    occs = expand_ics(
        ics, datetime(2026, 8, 1, tzinfo=UTC), datetime(2026, 8, 10, tzinfo=UTC)
    )
    starts = [o[0] for o in occs]
    assert len(starts) == 3
    assert datetime(2026, 8, 4, 16, 0, tzinfo=UTC) in starts
    assert datetime(2026, 8, 4, 13, 0, tzinfo=UTC) not in starts


def test_dst_boundary_keeps_local_time():
    # 9am America/New_York across the spring-forward gap (Mar 8 2026):
    # UTC offset shifts from -5 to -4 but local hour must stay 9.
    ics = "\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//test//EN",
            "BEGIN:VTIMEZONE",
            "TZID:America/New_York",
            "BEGIN:STANDARD",
            "DTSTART:20251102T020000",
            "TZOFFSETFROM:-0400",
            "TZOFFSETTO:-0500",
            "END:STANDARD",
            "BEGIN:DAYLIGHT",
            "DTSTART:20260308T020000",
            "TZOFFSETFROM:-0500",
            "TZOFFSETTO:-0400",
            "END:DAYLIGHT",
            "END:VTIMEZONE",
            "BEGIN:VEVENT",
            "UID:dst-1",
            "SUMMARY:School run",
            "DTSTART;TZID=America/New_York:20260306T090000",
            "DTEND;TZID=America/New_York:20260306T093000",
            "RRULE:FREQ=DAILY;COUNT=4",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )
    occs = expand_ics(
        ics, datetime(2026, 3, 5, tzinfo=UTC), datetime(2026, 3, 12, tzinfo=UTC)
    )
    assert [o[0] for o in occs] == [
        datetime(2026, 3, 6, 14, 0, tzinfo=UTC),  # EST (-5)
        datetime(2026, 3, 7, 14, 0, tzinfo=UTC),
        datetime(2026, 3, 8, 13, 0, tzinfo=UTC),  # EDT (-4) — local 9am preserved
        datetime(2026, 3, 9, 13, 0, tzinfo=UTC),
    ]


def test_all_day_event():
    ics = build_event_ics(
        uid=new_uid(),
        summary="Birthday",
        dtstart=datetime(2026, 9, 1, tzinfo=UTC).date(),
        dtend=datetime(2026, 9, 2, tzinfo=UTC).date(),
        all_day=True,
    )
    fields = parse_event_ics(ics)
    assert fields["all_day"] is True
    occs = expand_ics(
        ics, datetime(2026, 8, 25, tzinfo=UTC), datetime(2026, 9, 5, tzinfo=UTC)
    )
    assert len(occs) == 1
    assert occs[0][2] is True
