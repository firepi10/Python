import shutil
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.events import bus
from app.db.session import get_db
from app.services import display_service, settings_service
from app.services.sleep_service import should_be_asleep

router = APIRouter(prefix="/device", tags=["device"])


@router.get("")
def device_info(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    usage = shutil.disk_usage(settings.data_dir)
    sleep_cfg = settings_service.get(db, "sleep_schedule") or {}
    return {
        "version": settings.version,
        "display_on": display_service.is_display_on(),
        "scheduled_asleep": bool(
            sleep_cfg.get("enabled")
            and should_be_asleep(
                datetime.now(), sleep_cfg.get("off", "21:30"), sleep_cfg.get("on", "06:30")
            )
        ),
        "disk_total_gb": round(usage.total / 1e9, 1),
        "disk_free_gb": round(usage.free / 1e9, 1),
        "time": datetime.now(UTC).isoformat(),
    }


@router.post("/sleep")
def sleep_now() -> dict:
    return {"display_on": not display_service.display_off()}


@router.post("/wake")
def wake_now() -> dict:
    return {"display_on": display_service.display_on()}


class RotationIn(BaseModel):
    transform: str


@router.put("/rotation")
def set_rotation(body: RotationIn) -> dict:
    try:
        applied_live = display_service.set_rotation(body.transform)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"transform": body.transform, "applied_live": applied_live}


@router.post("/reload-ui")
def reload_ui() -> dict:
    """Ask every connected UI (the wall included) to refresh itself."""
    bus.publish("reload")
    return {"ok": True}


@router.post("/update-now")
def update_now() -> dict:
    """Kick the systemd update unit (allowed by a scoped sudoers rule that the
    installer writes). Off-Pi this reports not-available instead of failing."""
    import shutil as _shutil
    import subprocess

    if _shutil.which("sudo") is None or _shutil.which("systemctl") is None:
        return {"started": False, "reason": "not running on the appliance"}
    try:
        subprocess.run(
            ["sudo", "-n", "systemctl", "start", "bayta-update.service"],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return {"started": True}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(500, f"could not start update: {exc}") from exc
