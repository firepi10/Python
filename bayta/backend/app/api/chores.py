from datetime import date as date_type
from datetime import datetime, timedelta

from dateutil.rrule import rrulestr
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.events import bus
from app.db.models import Chore, ChoreCompletion
from app.db.session import get_db

router = APIRouter(prefix="/chores", tags=["chores"])

# Fixed Monday anchor so FREQ=WEEKLY;BYDAY=... behaves independently of when
# the chore was created.
RRULE_EPOCH = datetime(2020, 1, 6)


def due_on(chore: Chore, day: date_type) -> bool:
    try:
        rule = rrulestr(chore.rrule, dtstart=RRULE_EPOCH)
    except (ValueError, TypeError):
        return False
    day_start = datetime(day.year, day.month, day.day)
    return bool(
        rule.between(day_start - timedelta(seconds=1), day_start + timedelta(days=1), inc=False)
    )


class ChoreIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    icon: str | None = None
    profile_id: int | None = None
    rrule: str = "FREQ=DAILY"
    points: int = Field(default=1, ge=0, le=100)
    active: bool = True


def _chore_dict(c: Chore, completed: bool | None = None) -> dict:
    out = {
        "id": c.id,
        "title": c.title,
        "icon": c.icon,
        "profile_id": c.profile_id,
        "rrule": c.rrule,
        "points": c.points,
        "active": c.active,
    }
    if completed is not None:
        out["completed"] = completed
    return out


@router.get("")
def chores_for_day(
    day: date_type = Query(default_factory=date_type.today), db: Session = Depends(get_db)
) -> list[dict]:
    chores = db.query(Chore).filter(Chore.active.is_(True)).all()
    done_ids = {
        c.chore_id
        for c in db.query(ChoreCompletion).filter(ChoreCompletion.due_date == day).all()
    }
    return [_chore_dict(c, completed=c.id in done_ids) for c in chores if due_on(c, day)]


@router.get("/all")
def all_chores(db: Session = Depends(get_db)) -> list[dict]:
    return [_chore_dict(c) for c in db.query(Chore).order_by(Chore.id).all()]


@router.post("", status_code=201)
def create_chore(body: ChoreIn, db: Session = Depends(get_db)) -> dict:
    try:
        rrulestr(body.rrule, dtstart=RRULE_EPOCH)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, f"invalid repeat rule: {exc}") from exc
    chore = Chore(**body.model_dump())
    db.add(chore)
    db.commit()
    db.refresh(chore)
    bus.publish("chores")
    return _chore_dict(chore)


@router.patch("/{chore_id}")
def update_chore(chore_id: int, body: ChoreIn, db: Session = Depends(get_db)) -> dict:
    chore = db.get(Chore, chore_id)
    if chore is None:
        raise HTTPException(404, "chore not found")
    for k, v in body.model_dump().items():
        setattr(chore, k, v)
    db.commit()
    bus.publish("chores")
    return _chore_dict(chore)


@router.delete("/{chore_id}", status_code=204)
def delete_chore(chore_id: int, db: Session = Depends(get_db)):
    chore = db.get(Chore, chore_id)
    if chore is None:
        raise HTTPException(404, "chore not found")
    db.delete(chore)
    db.commit()
    bus.publish("chores")


class CompleteIn(BaseModel):
    date: date_type


@router.post("/{chore_id}/complete")
def toggle_complete(chore_id: int, body: CompleteIn, db: Session = Depends(get_db)) -> dict:
    chore = db.get(Chore, chore_id)
    if chore is None:
        raise HTTPException(404, "chore not found")
    existing = (
        db.query(ChoreCompletion)
        .filter(ChoreCompletion.chore_id == chore_id, ChoreCompletion.due_date == body.date)
        .one_or_none()
    )
    if existing is not None:
        db.delete(existing)
        completed = False
    else:
        db.add(
            ChoreCompletion(chore_id=chore_id, due_date=body.date, points_awarded=chore.points)
        )
        completed = True
    db.commit()
    bus.publish("chores")
    return {"id": chore_id, "completed": completed}


@router.get("/stars")
def stars(
    since: date_type = Query(...), db: Session = Depends(get_db)
) -> list[dict]:
    """Total points per family member since a date (week scoreboard)."""
    rows = (
        db.query(Chore.profile_id, func.sum(ChoreCompletion.points_awarded))
        .join(ChoreCompletion, ChoreCompletion.chore_id == Chore.id)
        .filter(ChoreCompletion.due_date >= since, Chore.profile_id.isnot(None))
        .group_by(Chore.profile_id)
        .all()
    )
    return [{"profile_id": pid, "points": int(points or 0)} for pid, points in rows]
