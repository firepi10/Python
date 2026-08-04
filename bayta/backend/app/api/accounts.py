from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core import secrets
from app.core.events import bus
from app.db.models import CaldavAccount, Calendar
from app.db.session import get_db
from app.sync import caldav_sync
from app.sync.caldav_client import CalDAVAuthError

router = APIRouter(prefix="/accounts", tags=["accounts"])

ICLOUD = "https://caldav.icloud.com"


class TestIn(BaseModel):
    apple_id: str = Field(min_length=3)
    password: str = Field(min_length=1)
    server_url: str = ICLOUD


class CalendarPick(BaseModel):
    url: str
    name: str
    enabled: bool = True
    profile_id: int | None = None


class AccountIn(TestIn):
    label: str = "iCloud"
    calendars: list[CalendarPick]


class CalendarPatch(BaseModel):
    enabled: bool | None = None
    profile_id: int | None = None
    clear_profile: bool = False


@router.post("/test")
async def test_account(body: TestIn) -> dict:
    """Discovery: validate credentials and list the account's calendars."""
    try:
        return await run_in_threadpool(
            caldav_sync.discover, body.apple_id, body.password, body.server_url
        )
    except Exception as exc:
        message = str(exc)
        if "401" in message or "Unauthorized" in message or isinstance(exc, CalDAVAuthError):
            raise HTTPException(
                401,
                "Sign-in failed. iCloud requires an app-specific password from "
                "appleid.apple.com → Sign-In and Security → App-Specific Passwords.",
            ) from exc
        raise HTTPException(502, f"Could not reach the calendar server: {message}") from exc


@router.get("")
def list_accounts(db: Session = Depends(get_db)) -> list[dict]:
    out = []
    for acct in db.query(CaldavAccount).all():
        out.append(
            {
                "id": acct.id,
                "label": acct.label,
                "apple_id": acct.apple_id,
                "status": acct.status,
                "last_sync_at": acct.last_sync_at.isoformat() if acct.last_sync_at else None,
                "last_error": acct.last_error,
                "calendars": [
                    {
                        "id": c.id,
                        "name": c.display_name,
                        "enabled": c.enabled,
                        "profile_id": c.profile_id,
                    }
                    for c in acct.calendars
                ],
            }
        )
    return out


@router.post("", status_code=201)
def create_account(body: AccountIn, db: Session = Depends(get_db)) -> dict:
    acct = CaldavAccount(
        label=body.label,
        apple_id=body.apple_id,
        password_enc=secrets.encrypt(body.password),
        server_url=body.server_url,
    )
    db.add(acct)
    db.flush()
    for pick in body.calendars:
        db.add(
            Calendar(
                account_id=acct.id,
                remote_url=pick.url,
                display_name=pick.name,
                enabled=pick.enabled,
                profile_id=pick.profile_id,
            )
        )
    db.commit()
    bus.publish("calendar")
    return {"id": acct.id}


@router.patch("/{account_id}/calendars/{calendar_id}")
def patch_calendar(
    account_id: int, calendar_id: int, body: CalendarPatch, db: Session = Depends(get_db)
) -> dict:
    cal = db.get(Calendar, calendar_id)
    if cal is None or cal.account_id != account_id:
        raise HTTPException(404, "calendar not found")
    if body.enabled is not None:
        cal.enabled = body.enabled
    if body.clear_profile:
        cal.profile_id = None
    elif body.profile_id is not None:
        cal.profile_id = body.profile_id
    db.commit()
    bus.publish("calendar")
    return {"id": cal.id, "enabled": cal.enabled, "profile_id": cal.profile_id}


@router.post("/{account_id}/reauth")
def reauth(account_id: int, body: TestIn, db: Session = Depends(get_db)) -> dict:
    acct = db.get(CaldavAccount, account_id)
    if acct is None:
        raise HTTPException(404, "account not found")
    acct.password_enc = secrets.encrypt(body.password)
    acct.status = "ok"
    acct.last_error = None
    db.commit()
    return {"id": acct.id, "status": acct.status}


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    acct = db.get(CaldavAccount, account_id)
    if acct is None:
        raise HTTPException(404, "account not found")
    db.delete(acct)
    db.commit()
    bus.publish("calendar")


@router.post("/sync-now")
async def sync_now() -> dict:
    await run_in_threadpool(caldav_sync.run_all)
    return {"ok": True}
