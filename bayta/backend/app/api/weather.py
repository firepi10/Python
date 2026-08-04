import json

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.db.models import WeatherCache
from app.db.session import get_db
from app.sync.weather_sync import sync_weather

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("")
def get_weather(db: Session = Depends(get_db)) -> dict:
    row = db.get(WeatherCache, 1)
    if row is None:
        return {"available": False}
    return {
        "available": True,
        "fetched_at": row.fetched_at.isoformat(),
        "data": json.loads(row.payload),
    }


@router.post("/refresh")
async def refresh_weather() -> dict:
    payload = await run_in_threadpool(sync_weather)
    return {"refreshed": payload is not None}
