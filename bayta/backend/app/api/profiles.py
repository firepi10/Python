from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.events import bus
from app.db.models import Profile
from app.db.session import get_db

router = APIRouter(prefix="/profiles", tags=["profiles"])

PROFILE_COLORS = {"blue", "purple", "pink", "orange", "green", "teal", "yellow", "red"}


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = "blue"
    sort_order: int = 0


class ProfileOut(ProfileIn):
    id: int

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ProfileOut])
def list_profiles(db: Session = Depends(get_db)):
    return db.query(Profile).order_by(Profile.sort_order, Profile.id).all()


@router.post("", response_model=ProfileOut, status_code=201)
def create_profile(body: ProfileIn, db: Session = Depends(get_db)):
    if body.color not in PROFILE_COLORS:
        raise HTTPException(422, f"color must be one of {sorted(PROFILE_COLORS)}")
    profile = Profile(**body.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    bus.publish("profiles")
    return profile


@router.patch("/{profile_id}", response_model=ProfileOut)
def update_profile(profile_id: int, body: ProfileIn, db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(404, "profile not found")
    if body.color not in PROFILE_COLORS:
        raise HTTPException(422, f"color must be one of {sorted(PROFILE_COLORS)}")
    for k, v in body.model_dump().items():
        setattr(profile, k, v)
    db.commit()
    db.refresh(profile)
    bus.publish("profiles")
    return profile


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(404, "profile not found")
    db.delete(profile)
    db.commit()
    bus.publish("profiles")
