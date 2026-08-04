from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.events import bus
from app.db.models import Countdown
from app.db.session import get_db

router = APIRouter(prefix="/countdowns", tags=["countdowns"])


class CountdownIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    target_date: date
    icon: str | None = None
    profile_id: int | None = None


class CountdownOut(CountdownIn):
    id: int

    model_config = {"from_attributes": True}


@router.get("", response_model=list[CountdownOut])
def list_countdowns(db: Session = Depends(get_db)):
    return db.query(Countdown).order_by(Countdown.target_date).all()


@router.post("", response_model=CountdownOut, status_code=201)
def create_countdown(body: CountdownIn, db: Session = Depends(get_db)):
    row = Countdown(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    bus.publish("countdowns")
    return row


@router.delete("/{countdown_id}", status_code=204)
def delete_countdown(countdown_id: int, db: Session = Depends(get_db)):
    row = db.get(Countdown, countdown_id)
    if row is None:
        raise HTTPException(404, "countdown not found")
    db.delete(row)
    db.commit()
    bus.publish("countdowns")
