"""iCloud CalDAV sync engine.

Per enabled calendar, each cycle:
  1. push queued local mutations (pending_ops) — If-Match guarded,
  2. cheap ctag check — bail if nothing changed remotely,
  3. PROPFIND etag diff → calendar-multiget only what changed,
  4. upsert events + refresh occurrence cache, detect remote deletions.

A 401 marks the account auth_failed and STOPS retrying (repeated bad
app-specific-password attempts can lock an Apple ID out of CalDAV).
"""

import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

import caldav
from sqlalchemy.orm import Session

from app.core import secrets
from app.core.events import bus
from app.db.models import CaldavAccount, Calendar, Event, PendingOp, SyncLog
from app.db.session import session_factory
from app.services.calendar_service import refresh_occurrences
from app.services.ics import parse_event_ics
from app.sync import caldav_client as dav
from app.sync.caldav_client import CalDAVAuthError, CalDAVConflict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- discovery


def discover(apple_id: str, password: str, server_url: str) -> dict:
    """Resolve the principal and list calendars. Runs in a worker thread."""
    client = caldav.DAVClient(url=server_url, username=apple_id, password=password)
    principal = client.principal()
    calendars = []
    for cal in principal.calendars():
        try:
            name = cal.get_display_name() or cal.url.path.rstrip("/").split("/")[-1]
        except Exception:
            name = cal.url.path.rstrip("/").split("/")[-1]
        # skip non-VEVENT collections (iCloud exposes reminders, inbox, etc.)
        try:
            comps = cal.get_supported_components()
            if comps and "VEVENT" not in comps:
                continue
        except Exception:
            pass
        calendars.append({"url": str(cal.url), "name": str(name)})
    return {"principal_url": str(principal.url), "calendars": calendars}


# ------------------------------------------------------------------- push


def _push_pending(db: Session, client, calendar: Calendar) -> None:
    ops = (
        db.query(PendingOp)
        .join(Event, PendingOp.event_id == Event.id)
        .filter(Event.calendar_id == calendar.id)
        .order_by(PendingOp.id)
        .all()
    )
    for op in ops:
        event = db.get(Event, op.event_id) if op.event_id else None
        try:
            if op.op == "create" and event is not None:
                # filename from the UID's local part only: '@' would be
                # percent-encoded by servers and break href comparisons
                filename = f"{event.uid.split('@')[0]}.ics"
                url = dav.absolute(calendar.remote_url.rstrip("/") + "/", filename)
                etag = dav.put_event(client, url, op.payload_ics or event.ics, is_new=True)
                # store the server-relative path — PROPFIND reports hrefs as paths
                event.remote_href = urlparse(url).path
                event.etag = etag
                event.origin = "remote"
            elif op.op == "update" and event is not None and event.remote_href:
                url = dav.absolute(calendar.remote_url, event.remote_href)
                etag = dav.put_event(
                    client, url, op.payload_ics or event.ics, etag=op.etag or event.etag
                )
                event.etag = etag
            elif op.op == "delete" and op.remote_href:
                url = dav.absolute(calendar.remote_url, op.remote_href)
                dav.delete_event(client, url, etag=op.etag)
            db.delete(op)
            db.commit()
        except CalDAVConflict:
            # Server copy changed underneath us: server wins. Drop the op; the
            # pull phase below refreshes the local copy, and the UI surfaces
            # the overwritten text from the op payload if the user reopens it.
            logger.warning("conflict pushing %s for event %s; server wins", op.op, op.event_id)
            db.delete(op)
            db.commit()
        except CalDAVAuthError:
            raise
        except Exception as exc:
            op.attempts += 1
            op.last_error = str(exc)[:500]
            if op.attempts >= 5:
                logger.error("dropping pending op %s after 5 attempts: %s", op.id, exc)
                db.delete(op)
            db.commit()


# ------------------------------------------------------------------- pull


def _pull_calendar(db: Session, client, calendar: Calendar) -> int:
    remote = dav.list_etags(client, calendar.remote_url)

    local_events = (
        db.query(Event)
        .filter(Event.calendar_id == calendar.id, Event.remote_href.isnot(None))
        .all()
    )
    by_href = {e.remote_href: e for e in local_events}

    changed_hrefs = [
        href
        for href, etag in remote.items()
        if href not in by_href or by_href[href].etag != etag or by_href[href].deleted
    ]
    removed = [e for href, e in by_href.items() if href not in remote and e.origin == "remote"]

    changes = 0
    if changed_hrefs:
        for obj in dav.multiget(client, calendar.remote_url, changed_hrefs):
            if not obj.data:
                continue
            try:
                fields = parse_event_ics(obj.data)
            except Exception as exc:
                logger.warning("unparseable event at %s: %s", obj.href, exc)
                continue
            event = by_href.get(obj.href)
            if event is None:
                event = (
                    db.query(Event)
                    .filter(Event.calendar_id == calendar.id, Event.uid == fields["uid"])
                    .one_or_none()
                )
            if event is None:
                event = Event(calendar_id=calendar.id, ics="", uid=fields["uid"])
                db.add(event)
            event.remote_href = obj.href
            event.etag = obj.etag
            event.ics = obj.data
            event.origin = "remote"
            event.deleted = False
            for key in (
                "summary",
                "location",
                "dtstart_utc",
                "dtend_utc",
                "all_day",
                "is_recurring",
                "rrule",
            ):
                setattr(event, key, fields[key])
            event.last_modified = datetime.now(UTC)
            db.flush()
            refresh_occurrences(db, event)
            changes += 1

    for event in removed:
        db.delete(event)  # cascades occurrences
        changes += 1

    db.commit()
    return changes


# ------------------------------------------------------------------ driver


def sync_account(db: Session, account: CaldavAccount) -> int:
    password = secrets.decrypt(account.password_enc)
    total = 0
    with dav.make_client(account.apple_id, password) as client:
        for calendar in account.calendars:
            if not calendar.enabled:
                continue
            has_pending = (
                db.query(PendingOp)
                .join(Event, PendingOp.event_id == Event.id)
                .filter(Event.calendar_id == calendar.id)
                .count()
                > 0
            )
            if has_pending:
                _push_pending(db, client, calendar)

            ctag = dav.get_ctag(client, calendar.remote_url)
            if ctag is not None and ctag == calendar.ctag and not has_pending:
                continue
            total += _pull_calendar(db, client, calendar)
            calendar.ctag = ctag
            db.commit()
    return total


def run_all() -> None:
    """Scheduler entrypoint: sync every enabled account sequentially."""
    db = session_factory()()
    log = SyncLog(kind="caldav")
    db.add(log)
    db.commit()
    changed = 0
    status = "ok"
    detail = None
    try:
        accounts = db.query(CaldavAccount).filter(CaldavAccount.status != "auth_failed").all()
        for account in accounts:
            try:
                changed += sync_account(db, account)
                account.status = "ok"
                account.last_sync_at = datetime.now(UTC)
                account.last_error = None
            except CalDAVAuthError as exc:
                db.rollback()
                account.status = "auth_failed"
                account.last_error = (
                    "Sign-in failed. Use an app-specific password from appleid.apple.com "
                    "(regular Apple ID passwords are rejected by CalDAV)."
                )
                status, detail = "error", str(exc)
                logger.error("auth failure for %s: %s", account.apple_id, exc)
            except Exception as exc:
                db.rollback()
                account.status = "error"
                account.last_error = str(exc)[:500]
                status, detail = "error", str(exc)[:500]
                logger.exception("sync failed for %s", account.apple_id)
            db.commit()
    finally:
        log.finished_at = datetime.now(UTC)
        log.status = status
        log.detail = detail
        db.commit()
        db.close()
    if changed:
        bus.publish("calendar")
