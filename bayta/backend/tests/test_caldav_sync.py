"""Integration tests for the CalDAV engine against a live local Radicale
server (RFC-compliant CalDAV incl. etags, If-Match and multiget)."""

import socket
import subprocess
import sys
import time
from datetime import UTC, datetime

import caldav as caldav_lib
import pytest

from app.core import secrets
from app.db.models import CaldavAccount, Calendar, Event, Occurrence, PendingOp
from app.services.calendar_service import create_local_event, delete_event, update_local_event
from app.sync.caldav_sync import discover, run_all, sync_account

EVENT_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//EN
BEGIN:VEVENT
UID:remote-1
SUMMARY:Team dinner
DTSTART:20260810T230000Z
DTEND:20260811T010000Z
END:VEVENT
END:VCALENDAR
"""

RECURRING_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//EN
BEGIN:VEVENT
UID:remote-2
SUMMARY:Swim class
DTSTART:20260805T150000Z
DTEND:20260805T160000Z
RRULE:FREQ=WEEKLY;COUNT=6
END:VEVENT
END:VCALENDAR
"""


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def radicale(tmp_path_factory):
    storage = tmp_path_factory.mktemp("radicale")
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "radicale",
            "--storage-filesystem-folder",
            str(storage),
            "--auth-type",
            "none",
            "--server-hosts",
            f"127.0.0.1:{port}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}/"
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                break
        except OSError:
            time.sleep(0.2)
    else:
        proc.terminate()
        raise RuntimeError("radicale did not start")
    yield base
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture
def remote_calendar(radicale):
    """A fresh Radicale calendar seeded with two events, per test."""
    client = caldav_lib.DAVClient(url=radicale, username="fam", password="pw")
    principal = client.principal()
    name = f"family-{int(time.time() * 1000)}"
    cal = principal.make_calendar(name=name)
    cal.save_event(EVENT_ICS)
    cal.save_event(RECURRING_ICS)
    return {"client": client, "caldav_cal": cal, "url": str(cal.url), "base": radicale}


@pytest.fixture
def synced_account(client, db, remote_calendar):
    acct = CaldavAccount(
        label="Test",
        apple_id="fam",
        password_enc=secrets.encrypt("pw"),
        server_url=remote_calendar["base"],
    )
    db.add(acct)
    db.flush()
    cal = Calendar(
        account_id=acct.id, remote_url=remote_calendar["url"], display_name="Family"
    )
    db.add(cal)
    db.commit()
    return {"account": acct, "calendar": cal, **remote_calendar}


def test_discover_lists_calendars(client, remote_calendar):
    result = discover("fam", "pw", remote_calendar["base"])
    assert result["principal_url"]
    assert any(c["url"] == remote_calendar["url"] for c in result["calendars"])


def test_first_sync_pulls_events_and_expands(client, db, synced_account):
    changed = sync_account(db, synced_account["account"])
    assert changed == 2

    events = db.query(Event).all()
    assert {e.uid for e in events} == {"remote-1", "remote-2"}
    assert all(e.origin == "remote" and e.etag for e in events)

    swim = next(e for e in events if e.uid == "remote-2")
    occs = db.query(Occurrence).filter(Occurrence.event_id == swim.id).count()
    assert occs == 6

    db.refresh(synced_account["calendar"])
    assert synced_account["calendar"].ctag

    # second run: ctag unchanged -> no work
    assert sync_account(db, synced_account["account"]) == 0


def test_local_create_update_delete_push(client, db, synced_account):
    sync_account(db, synced_account["account"])

    event = create_local_event(
        db,
        summary="Parent-teacher conf",
        dtstart=datetime(2026, 8, 20, 18, 0, tzinfo=UTC),
        dtend=datetime(2026, 8, 20, 19, 0, tzinfo=UTC),
        calendar_id=synced_account["calendar"].id,
    )
    assert db.query(PendingOp).count() == 1

    sync_account(db, synced_account["account"])
    db.refresh(event)
    assert db.query(PendingOp).count() == 0
    assert event.remote_href and event.etag

    cal = caldav_lib.DAVClient(
        url=synced_account["base"], username="fam", password="pw"
    ).calendar(url=synced_account["calendar"].remote_url)
    summaries = [str(e.icalendar_component.get("summary")) for e in cal.events()]
    assert "Parent-teacher conf" in summaries

    update_local_event(
        db,
        event,
        summary="Parent-teacher conference",
        dtstart=datetime(2026, 8, 20, 18, 30, tzinfo=UTC),
        dtend=datetime(2026, 8, 20, 19, 30, tzinfo=UTC),
    )
    sync_account(db, synced_account["account"])
    summaries = [str(e.icalendar_component.get("summary")) for e in cal.events()]
    assert "Parent-teacher conference" in summaries

    delete_event(db, event)
    sync_account(db, synced_account["account"])
    summaries = [str(e.icalendar_component.get("summary")) for e in cal.events()]
    assert "Parent-teacher conference" not in summaries


def test_remote_edit_and_delete_propagate(client, db, synced_account):
    sync_account(db, synced_account["account"])

    cal = synced_account["calendar"]
    dav = caldav_lib.DAVClient(
        url=synced_account["base"], username="fam", password="pw"
    ).calendar(url=cal.remote_url)

    dav.save_event(EVENT_ICS.replace("Team dinner", "Team brunch"))
    for ev in dav.events():
        if str(ev.icalendar_component.get("uid")) == "remote-2":
            ev.delete()

    sync_account(db, synced_account["account"])
    events = db.query(Event).all()
    assert {e.summary for e in events} == {"Team brunch"}


def test_conflict_server_wins(client, db, synced_account):
    sync_account(db, synced_account["account"])
    event = db.query(Event).filter(Event.uid == "remote-1").one()

    # Someone edits the same event remotely...
    dav = caldav_lib.DAVClient(
        url=synced_account["base"], username="fam", password="pw"
    ).calendar(url=synced_account["calendar"].remote_url)
    dav.save_event(EVENT_ICS.replace("Team dinner", "Team dinner (remote edit)"))

    # ...while we queue a local edit against the now-stale etag.
    update_local_event(
        db,
        event,
        summary="Team dinner (local edit)",
        dtstart=datetime(2026, 8, 10, 23, 0, tzinfo=UTC),
        dtend=datetime(2026, 8, 11, 1, 0, tzinfo=UTC),
    )

    sync_account(db, synced_account["account"])
    db.refresh(event)
    assert db.query(PendingOp).count() == 0  # conflict op dropped, not retried
    assert event.summary == "Team dinner (remote edit)"  # server won


def test_auth_failure_stops_account(client, db, monkeypatch):
    acct = CaldavAccount(
        label="Broken",
        apple_id="x@icloud.com",
        password_enc=secrets.encrypt("bad"),
        server_url="http://127.0.0.1:1/",
    )
    db.add(acct)
    db.commit()

    from app.sync import caldav_sync
    from app.sync.caldav_client import CalDAVAuthError

    def boom(_db, _acct):
        raise CalDAVAuthError("401")

    monkeypatch.setattr(caldav_sync, "sync_account", boom)
    run_all()

    db.expire_all()
    acct = db.get(CaldavAccount, acct.id)
    assert acct.status == "auth_failed"
    assert "app-specific" in (acct.last_error or "")

    calls = []
    monkeypatch.setattr(caldav_sync, "sync_account", lambda *a: calls.append(1))
    run_all()
    assert calls == []  # auth_failed accounts are skipped until re-auth
