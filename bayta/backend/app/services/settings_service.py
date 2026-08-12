import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Setting

DEFAULTS: dict[str, Any] = {
    # Off until the owner turns it on in Settings: a brand-new device blanking
    # itself on night one reads as broken hardware, not as a feature.
    "sleep_schedule": {"enabled": False, "off": "21:30", "on": "06:30"},
    "idle_timeout_s": 300,
    "orientation": "landscape",
    "theme": "auto",  # auto|light|dark
    "reduced_glass": False,
    "weather": {"lat": 40.7128, "lon": -74.006, "unit": "fahrenheit", "label": "Home"},
    "screensaver": {"enabled": True, "interval_s": 12, "ken_burns": True},
    "admin_pin": None,
}


def get_all(db: Session) -> dict[str, Any]:
    merged = dict(DEFAULTS)
    for row in db.query(Setting).all():
        merged[row.key] = json.loads(row.value)
    return merged


def get(db: Session, key: str) -> Any:
    row = db.get(Setting, key)
    if row is not None:
        return json.loads(row.value)
    return DEFAULTS.get(key)


def put(db: Session, key: str, value: Any) -> Any:
    row = db.get(Setting, key)
    encoded = json.dumps(value)
    if row is None:
        db.add(Setting(key=key, value=encoded))
    else:
        row.value = encoded
    db.commit()
    return value
