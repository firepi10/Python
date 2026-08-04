"""Weather via Open-Meteo (no API key required)."""

import json
from datetime import UTC, datetime

import httpx

from app.core.events import bus
from app.db.models import WeatherCache
from app.db.session import session_factory
from app.services import settings_service

API_URL = "https://api.open-meteo.com/v1/forecast"


def sync_weather(client: httpx.Client | None = None) -> dict | None:
    db = session_factory()()
    try:
        cfg = settings_service.get(db, "weather") or {}
        params = {
            "latitude": cfg.get("lat"),
            "longitude": cfg.get("lon"),
            "current": "temperature_2m,weather_code,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "temperature_unit": cfg.get("unit", "fahrenheit"),
            "timezone": "auto",
            "forecast_days": 7,
        }
        if params["latitude"] is None or params["longitude"] is None:
            return None

        own_client = client is None
        c = client or httpx.Client(timeout=15)
        try:
            resp = c.get(API_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()
        finally:
            if own_client:
                c.close()

        row = db.get(WeatherCache, 1)
        if row is None:
            row = WeatherCache(id=1, payload=json.dumps(payload))
            db.add(row)
        else:
            row.payload = json.dumps(payload)
            row.fetched_at = datetime.now(UTC)
        db.commit()
        bus.publish("weather")
        return payload
    finally:
        db.close()
