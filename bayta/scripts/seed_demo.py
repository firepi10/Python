#!/usr/bin/env python3
"""Seed a demo family into the dev database (used for screenshots and manual
testing). Idempotent: wipes and recreates the demo rows each run."""

import sys
from datetime import datetime, time, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import get_settings  # noqa: E402
from app.db.migrate import upgrade_to_head  # noqa: E402
from app.db.models import Countdown, Event, Occurrence, PendingOp, Profile  # noqa: E402
from app.db.session import session_factory  # noqa: E402
from app.services.calendar_service import create_local_event  # noqa: E402


def next_weekday(base: datetime, weekday: int) -> datetime:
    days = (weekday - base.weekday()) % 7
    return base + timedelta(days=days)


def main() -> None:
    get_settings().ensure_dirs()
    upgrade_to_head()
    db = session_factory()()

    for model in (Occurrence, PendingOp, Event, Countdown, Profile):
        db.query(model).delete()
    db.commit()

    mom = Profile(name="Mom", color="pink", sort_order=0)
    dad = Profile(name="Dad", color="blue", sort_order=1)
    zoe = Profile(name="Zoe", color="green", sort_order=2)
    max_ = Profile(name="Max", color="orange", sort_order=3)
    db.add_all([mom, dad, zoe, max_])
    db.commit()

    today = datetime.now().replace(minute=0, second=0, microsecond=0)
    monday = next_weekday(today, 0)
    wednesday = next_weekday(today, 2)
    thursday = next_weekday(today, 3)
    friday = next_weekday(today, 4)
    saturday = next_weekday(today, 5)

    def at(day: datetime, hh: int, mm: int = 0) -> datetime:
        return datetime.combine(day.date(), time(hh, mm)).astimezone()

    events = [
        dict(summary="Soccer practice", dtstart=at(monday, 16), dtend=at(monday, 17, 30),
             rrule="FREQ=WEEKLY;BYDAY=MO", profile_id=zoe.id, location="Riverside fields"),
        dict(summary="Piano lesson", dtstart=at(wednesday, 15, 30), dtend=at(wednesday, 16, 15),
             rrule="FREQ=WEEKLY;BYDAY=WE", profile_id=max_.id),
        dict(summary="Trash & recycling out", dtstart=at(thursday, 19), dtend=at(thursday, 19, 15),
             rrule="FREQ=WEEKLY;BYDAY=TH", profile_id=dad.id),
        dict(summary="Yoga", dtstart=at(today + timedelta(days=1), 7),
             dtend=at(today + timedelta(days=1), 8), rrule="FREQ=WEEKLY", profile_id=mom.id),
        dict(summary="Dentist — Max", dtstart=at(today + timedelta(days=2), 14),
             dtend=at(today + timedelta(days=2), 15), profile_id=max_.id, location="Dr. Patel"),
        dict(summary="Date night", dtstart=at(friday, 19), dtend=at(friday, 22),
             profile_id=mom.id, location="Lupa"),
        dict(summary="Grandma visits", dtstart=at(saturday, 0), dtend=at(saturday, 0),
             all_day=True),
        dict(summary="School bake sale", dtstart=at(today + timedelta(days=9), 0),
             dtend=at(today + timedelta(days=9), 0), all_day=True, profile_id=zoe.id),
        dict(summary="Book club", dtstart=at(today + timedelta(days=12), 19),
             dtend=at(today + timedelta(days=12), 21), profile_id=mom.id),
        dict(summary="Max's birthday 🎂", dtstart=at(today + timedelta(days=20), 0),
             dtend=at(today + timedelta(days=20), 0), all_day=True, profile_id=max_.id),
    ]
    for spec in events:
        create_local_event(db, timezone=get_settings().timezone, **spec)

    db.add(Countdown(title="Beach week", target_date=(today + timedelta(days=32)).date(), icon="🏖️"))
    db.commit()
    print(f"seeded {len(events)} events, 4 profiles, 1 countdown → {get_settings().db_path}")


if __name__ == "__main__":
    main()
