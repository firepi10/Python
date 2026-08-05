from datetime import datetime

from dateutil.rrule import rrulestr
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Calendar, Event
from app.db.session import get_db
from app.services import calendar_service

router = APIRouter(prefix="/calendar", tags=["calendar"])


class EventIn(BaseModel):
    summary: str = Field(min_length=1, max_length=512)
    start: datetime
    end: datetime
    all_day: bool = False
    location: str | None = None
    rrule: str | None = None
    calendar_id: int | None = None
    profile_id: int | None = None


def validate_rrule(rrule: str | None) -> None:
    """Reject junk rules with a clear message instead of silently dropping the
    recurrence (empty parse) or raising a 500 (bad FREQ)."""
    if not rrule:
        return
    try:
        rule = rrulestr(rrule, dtstart=datetime(2020, 1, 6))
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, f"invalid repeat rule: {exc}") from exc
    if "FREQ=" not in rrule.upper():
        raise HTTPException(422, "invalid repeat rule: missing FREQ")
    del rule


class CalendarOut(BaseModel):
    id: int
    display_name: str
    color: str | None
    profile_id: int | None
    enabled: bool
    read_only: bool

    model_config = {"from_attributes": True}


@router.get("/occurrences")
def occurrences(
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: Session = Depends(get_db),
) -> list[dict]:
    return calendar_service.occurrences_window(db, start, end)


@router.get("/calendars", response_model=list[CalendarOut])
def calendars(db: Session = Depends(get_db)):
    return db.query(Calendar).order_by(Calendar.display_name).all()


@router.post("/events", status_code=201)
def create_event(body: EventIn, db: Session = Depends(get_db)) -> dict:
    if body.end <= body.start and not body.all_day:
        raise HTTPException(422, "end must be after start")
    validate_rrule(body.rrule)
    event = calendar_service.create_local_event(
        db,
        summary=body.summary,
        dtstart=body.start,
        dtend=body.end,
        all_day=body.all_day,
        location=body.location,
        rrule=body.rrule,
        calendar_id=body.calendar_id,
        profile_id=body.profile_id,
        timezone=get_settings().timezone,
    )
    return {"id": event.id, "uid": event.uid}


@router.patch("/events/{event_id}")
def update_event(event_id: int, body: EventIn, db: Session = Depends(get_db)) -> dict:
    event = db.get(Event, event_id)
    if event is None or event.deleted:
        raise HTTPException(404, "event not found")
    # An omitted rrule means "leave the repeat alone"; clearing it takes an
    # explicit null. Without this, saving an edit silently destroys the series.
    rrule = body.rrule if "rrule" in body.model_fields_set else event.rrule
    validate_rrule(rrule)
    calendar_service.update_local_event(
        db,
        event,
        summary=body.summary,
        dtstart=body.start,
        dtend=body.end,
        all_day=body.all_day,
        location=body.location,
        rrule=rrule,
        profile_id=body.profile_id,
        timezone=get_settings().timezone,
    )
    return {"id": event.id}


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if event is None or event.deleted:
        raise HTTPException(404, "event not found")
    calendar_service.delete_event(db, event)


@router.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)) -> dict:
    event = db.get(Event, event_id)
    if event is None or event.deleted:
        raise HTTPException(404, "event not found")
    return {
        "id": event.id,
        "summary": event.summary,
        "location": event.location,
        "start": event.dtstart_utc.isoformat(),
        "end": event.dtend_utc.isoformat(),
        "all_day": event.all_day,
        "is_recurring": event.is_recurring,
        "rrule": event.rrule,
        "calendar_id": event.calendar_id,
        "profile_id": event.profile_id,
        "origin": event.origin,
    }
