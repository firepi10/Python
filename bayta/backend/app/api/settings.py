from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.events import bus
from app.db.session import get_db
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingValue(BaseModel):
    value: Any


@router.get("")
def get_settings_all(db: Session = Depends(get_db)) -> dict:
    return settings_service.get_all(db)


@router.put("/{key}")
def put_setting(key: str, body: SettingValue, db: Session = Depends(get_db)) -> dict:
    if key not in settings_service.DEFAULTS:
        raise HTTPException(404, f"unknown setting {key!r}")
    settings_service.put(db, key, body.value)
    bus.publish("settings")
    return {key: body.value}
