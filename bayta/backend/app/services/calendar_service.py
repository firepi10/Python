"""Local-first event operations.

Every mutation lands in SQLite immediately (UI refreshes via SSE), and — when
the event belongs to a synced CalDAV calendar — a row is queued in
`pending_ops` for the sync engine to push upstream.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.events import bus
from app.db.models import Calendar, Event, Occurrence, PendingOp, Profile
from app.services import ics as ics_helpers
from app.sync.ics_expand import default_window, expand_ics

logger = logging.getLogger(__name__)

PROFILE_FALLBACK_COLOR = "blue"


def refresh_occurrences(
    db: Session, event: Event, window: tuple[datetime, datetime] | None = None
) -> None:
    start, end = window or default_window()
    db.query(Occurrence).filter(Occurrence.event_id == event.id).delete()
    if event.deleted:
        return
    for occ_start, occ_end, all_day in expand_ics(event.ics, start, end):
        db.add(
            Occurrence(
                event_id=event.id, start_utc=occ_start, end_utc=occ_end, all_day=all_day
            )
        )


def _apply_ics(event: Event, ics_text: str) -> None:
    fields = ics_helpers.parse_event_ics(ics_text)
    event.ics = ics_text
    event.uid = fields["uid"] or event.uid
    event.summary = fields["summary"]
    event.location = fields["location"]
    event.dtstart_utc = fields["dtstart_utc"]
    event.dtend_utc = fields["dtend_utc"]
    event.all_day = fields["all_day"]
    event.is_recurring = fields["is_recurring"]
    event.rrule = fields["rrule"]
    event.last_modified = datetime.now(UTC)


def create_local_event(
    db: Session,
    *,
    summary: str,
    dtstart: datetime,
    dtend: datetime,
    all_day: bool = False,
    location: str | None = None,
    rrule: str | None = None,
    calendar_id: int | None = None,
    profile_id: int | None = None,
    timezone: str = "UTC",
) -> Event:
    uid = ics_helpers.new_uid()
    ics_text = ics_helpers.build_event_ics(
        uid=uid,
        summary=summary,
        dtstart=dtstart.date() if all_day else dtstart,
        dtend=dtend.date() if all_day else dtend,
        all_day=all_day,
        location=location,
        rrule=rrule,
        timezone=timezone,
    )
    event = Event(calendar_id=calendar_id, uid=uid, origin="local", ics="", profile_id=profile_id)
    _apply_ics(event, ics_text)
    db.add(event)
    db.flush()
    refresh_occurrences(db, event)

    if calendar_id is not None:
        db.add(PendingOp(event_id=event.id, op="create", payload_ics=ics_text))
    db.commit()
    db.refresh(event)
    bus.publish("calendar")
    return event


def update_local_event(
    db: Session,
    event: Event,
    *,
    summary: str,
    dtstart: datetime,
    dtend: datetime,
    all_day: bool = False,
    location: str | None = None,
    rrule: str | None = None,
    profile_id: int | None = None,
    timezone: str = "UTC",
) -> Event:
    event.profile_id = profile_id
    ics_text = ics_helpers.build_event_ics(
        uid=event.uid,
        summary=summary,
        dtstart=dtstart.date() if all_day else dtstart,
        dtend=dtend.date() if all_day else dtend,
        all_day=all_day,
        location=location,
        rrule=rrule,
        timezone=timezone,
    )
    _apply_ics(event, ics_text)
    refresh_occurrences(db, event)
    if event.calendar_id is not None:
        db.add(
            PendingOp(
                event_id=event.id,
                op="update",
                payload_ics=ics_text,
                remote_href=event.remote_href,
                etag=event.etag,
            )
        )
    db.commit()
    bus.publish("calendar")
    return event


def delete_event(db: Session, event: Event) -> None:
    event.deleted = True
    db.query(Occurrence).filter(Occurrence.event_id == event.id).delete()
    if event.calendar_id is not None and event.remote_href:
        db.add(
            PendingOp(
                event_id=event.id,
                op="delete",
                remote_href=event.remote_href,
                etag=event.etag,
            )
        )
    db.commit()
    bus.publish("calendar")


def _occurrence_dict(
    ev: Event,
    profiles: dict[int, Profile],
    start_utc: datetime,
    end_utc: datetime,
    all_day: bool,
) -> dict:
    cal: Calendar | None = ev.calendar
    profile = profiles.get(ev.profile_id) if ev.profile_id else None
    if profile is None and cal and cal.profile_id:
        profile = profiles.get(cal.profile_id)
    color = (cal.color if cal else None) or PROFILE_FALLBACK_COLOR
    if profile is not None:
        color = profile.color
    return {
        "event_id": ev.id,
        "summary": ev.summary,
        "location": ev.location,
        "start": start_utc.isoformat(),
        "end": end_utc.isoformat(),
        "all_day": all_day,
        "is_recurring": ev.is_recurring,
        "rrule": ev.rrule,
        "calendar_id": ev.calendar_id,
        "calendar_name": cal.display_name if cal else "Bayta",
        "read_only": bool(cal.read_only) if cal else False,
        "color": color,
        "profile_id": profile.id if profile else None,
        "profile_name": profile.name if profile else None,
    }


def _expand_beyond_cache(
    db: Session, profiles: dict[int, Profile], start: datetime, end: datetime
) -> list[dict]:
    """Occurrences for a range past the cached window — computed on the fly so
    browsing years ahead still shows yearly birthdays. Not persisted."""
    events = (
        db.query(Event)
        .options(joinedload(Event.calendar))
        .filter(Event.deleted.is_(False), Event.is_recurring.is_(True))
        .all()
    )
    out: list[dict] = []
    for ev in events:
        try:
            for occ_start, occ_end, all_day in expand_ics(ev.ics, start, end):
                out.append(_occurrence_dict(ev, profiles, occ_start, occ_end, all_day))
        except Exception as exc:  # a single unparseable event must not 500 the view
            logger.warning("could not expand event %s beyond cache: %s", ev.id, exc)
    return out


def occurrences_window(db: Session, start: datetime, end: datetime) -> list[dict]:
    rows = (
        db.execute(
            select(Occurrence)
            .join(Event)
            .options(joinedload(Occurrence.event).joinedload(Event.calendar))
            .where(
                Occurrence.start_utc < end,
                Occurrence.end_utc > start,
                Event.deleted.is_(False),
            )
            .order_by(Occurrence.start_utc)
        )
        .scalars()
        .all()
    )

    profiles = {p.id: p for p in db.query(Profile).all()}
    out = [
        _occurrence_dict(occ.event, profiles, occ.start_utc, occ.end_utc, occ.all_day)
        for occ in rows
    ]

    _, cache_end = default_window()
    if end > cache_end:
        seen = {(o["event_id"], o["start"]) for o in out}
        for extra in _expand_beyond_cache(db, profiles, max(start, cache_end), end):
            if (extra["event_id"], extra["start"]) not in seen:
                out.append(extra)
        out.sort(key=lambda o: o["start"])
    return out


def refresh_all_occurrences(db: Session) -> int:
    """Nightly job target: re-expand every live event over a fresh window."""
    window = default_window()
    events = db.query(Event).filter(Event.deleted.is_(False)).all()
    for event in events:
        refresh_occurrences(db, event, window)
    db.commit()
    return len(events)
