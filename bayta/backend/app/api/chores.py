from datetime import date as date_type
from datetime import datetime, timedelta

from dateutil.rrule import rrulestr
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.events import bus
from app.db.models import Chore, ChoreAssignee, ChoreCompletion
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
    # One entry = personal chore; several = a shared chore that EACH person
    # checks off themselves; empty = an "Everyone" chore with one checkbox.
    profile_ids: list[int] = []
    rrule: str = "FREQ=DAILY"
    points: int = Field(default=1, ge=0, le=100)
    active: bool = True


def _chore_meta(c: Chore) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "icon": c.icon,
        "profile_ids": sorted(a.profile_id for a in c.assignees),
        "rrule": c.rrule,
        "points": c.points,
        "active": c.active,
    }


@router.get("")
def chores_for_day(
    day: date_type = Query(default_factory=date_type.today), db: Session = Depends(get_db)
) -> list[dict]:
    """Day view, expanded per assignee: a chore shared by Lainey and Charlee
    appears in both columns, each with its own completion state."""
    chores = (
        db.query(Chore)
        .options(joinedload(Chore.assignees))
        .filter(Chore.active.is_(True))
        .all()
    )
    done = {
        (c.chore_id, c.profile_id)
        for c in db.query(ChoreCompletion).filter(ChoreCompletion.due_date == day).all()
    }
    out = []
    for chore in chores:
        if not due_on(chore, day):
            continue
        base = {
            "id": chore.id,
            "title": chore.title,
            "icon": chore.icon,
            "points": chore.points,
            "shared": len(chore.assignees) > 1,
        }
        if chore.assignees:
            for assignee in chore.assignees:
                out.append(
                    {
                        **base,
                        "profile_id": assignee.profile_id,
                        "completed": (chore.id, assignee.profile_id) in done,
                    }
                )
        else:
            out.append({**base, "profile_id": None, "completed": (chore.id, None) in done})
    return out


@router.get("/all")
def all_chores(db: Session = Depends(get_db)) -> list[dict]:
    chores = db.query(Chore).options(joinedload(Chore.assignees)).order_by(Chore.id).all()
    return [_chore_meta(c) for c in chores]


def _set_assignees(db: Session, chore: Chore, profile_ids: list[int]) -> None:
    db.query(ChoreAssignee).filter(ChoreAssignee.chore_id == chore.id).delete()
    for pid in dict.fromkeys(profile_ids):  # dedupe, keep order
        db.add(ChoreAssignee(chore_id=chore.id, profile_id=pid))


@router.post("", status_code=201)
def create_chore(body: ChoreIn, db: Session = Depends(get_db)) -> dict:
    try:
        rrulestr(body.rrule, dtstart=RRULE_EPOCH)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, f"invalid repeat rule: {exc}") from exc
    chore = Chore(**body.model_dump(exclude={"profile_ids"}))
    db.add(chore)
    db.flush()
    _set_assignees(db, chore, body.profile_ids)
    db.commit()
    db.refresh(chore)
    bus.publish("chores")
    return _chore_meta(chore)


@router.patch("/{chore_id}")
def update_chore(chore_id: int, body: ChoreIn, db: Session = Depends(get_db)) -> dict:
    chore = db.get(Chore, chore_id)
    if chore is None:
        raise HTTPException(404, "chore not found")
    for k, v in body.model_dump(exclude={"profile_ids"}).items():
        setattr(chore, k, v)
    _set_assignees(db, chore, body.profile_ids)
    db.commit()
    db.refresh(chore)
    bus.publish("chores")
    return _chore_meta(chore)


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
    profile_id: int | None = None


@router.post("/{chore_id}/complete")
def toggle_complete(chore_id: int, body: CompleteIn, db: Session = Depends(get_db)) -> dict:
    chore = db.get(Chore, chore_id)
    if chore is None:
        raise HTTPException(404, "chore not found")
    assignee_ids = {a.profile_id for a in chore.assignees}
    if assignee_ids and body.profile_id not in assignee_ids:
        raise HTTPException(422, "that person isn't assigned to this chore")
    if not assignee_ids and body.profile_id is not None:
        raise HTTPException(422, "this chore has one shared checkbox — omit profile_id")

    existing = (
        db.query(ChoreCompletion)
        .filter(
            ChoreCompletion.chore_id == chore_id,
            ChoreCompletion.due_date == body.date,
            ChoreCompletion.profile_id == body.profile_id,
        )
        .one_or_none()
    )
    if existing is not None:
        db.delete(existing)
        completed = False
    else:
        db.add(
            ChoreCompletion(
                chore_id=chore_id,
                due_date=body.date,
                profile_id=body.profile_id,
                points_awarded=chore.points,
            )
        )
        completed = True
    db.commit()
    bus.publish("chores")
    return {"id": chore_id, "profile_id": body.profile_id, "completed": completed}


@router.get("/stars")
def stars(since: date_type = Query(...), db: Session = Depends(get_db)) -> list[dict]:
    """Total points per family member since a date. Each person earns stars
    for the completions THEY checked off — shared chores pay everyone who
    did their part."""
    rows = (
        db.query(ChoreCompletion.profile_id, func.sum(ChoreCompletion.points_awarded))
        .filter(ChoreCompletion.due_date >= since, ChoreCompletion.profile_id.isnot(None))
        .group_by(ChoreCompletion.profile_id)
        .all()
    )
    return [{"profile_id": pid, "points": int(points or 0)} for pid, points in rows]
