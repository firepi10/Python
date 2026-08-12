"""The Pi has no RTC. These pin the behaviour that kept a network-less wall
display dark: it decided it was past 21:30 and cut the HDMI output for good."""

from datetime import datetime

from app.core import scheduler as scheduler_mod
from app.services import clock_service, display_service, settings_service
from app.services.sleep_service import should_be_asleep


def test_clock_untrusted_when_timesyncd_has_not_synced(tmp_path, monkeypatch):
    timesync = tmp_path / "timesync"
    timesync.mkdir()
    monkeypatch.setattr(clock_service, "TIMESYNC_DIR", timesync)
    monkeypatch.setattr(clock_service, "SYNC_FLAG", timesync / "synchronized")
    assert clock_service.clock_is_trustworthy() is False

    (timesync / "synchronized").touch()
    assert clock_service.clock_is_trustworthy() is True


def test_clock_trusted_where_nothing_runs_timesyncd(tmp_path, monkeypatch):
    """Dev containers and CI have no timesyncd; don't disable the schedule."""
    missing = tmp_path / "absent"
    monkeypatch.setattr(clock_service, "TIMESYNC_DIR", missing)
    monkeypatch.setattr(clock_service, "SYNC_FLAG", missing / "synchronized")
    assert clock_service.clock_is_trustworthy() is True


def test_sleep_schedule_is_off_until_the_owner_enables_it():
    assert settings_service.DEFAULTS["sleep_schedule"]["enabled"] is False


def _force_clock(monkeypatch, trustworthy: bool):
    monkeypatch.setattr(
        "app.services.clock_service.clock_is_trustworthy", lambda: trustworthy
    )


def test_unsynced_clock_never_blanks_the_panel(client, db, monkeypatch):
    """The reported failure: no Wi-Fi, clock stuck in the evening, screen off."""
    settings_service.put(db, "sleep_schedule", {"enabled": True, "off": "21:30", "on": "06:30"})
    db.commit()

    calls: list[str] = []
    monkeypatch.setattr(display_service, "display_off", lambda: calls.append("off") or True)
    monkeypatch.setattr(display_service, "display_on", lambda: calls.append("on") or True)
    _force_clock(monkeypatch, False)

    scheduler_mod._sleep_tick()
    assert "off" not in calls


def test_unsynced_clock_restores_a_panel_that_is_already_off(client, db, monkeypatch):
    """If NTP is lost after the panel slept, bring it back rather than strand it."""
    settings_service.put(db, "sleep_schedule", {"enabled": True, "off": "21:30", "on": "06:30"})
    db.commit()

    calls: list[str] = []
    monkeypatch.setattr(display_service, "is_display_on", lambda: False)
    monkeypatch.setattr(display_service, "display_on", lambda: calls.append("on") or True)
    monkeypatch.setattr(display_service, "display_off", lambda: calls.append("off") or True)
    _force_clock(monkeypatch, False)

    scheduler_mod._sleep_tick()
    assert calls == ["on"]


def test_synced_clock_still_sleeps_on_schedule(client, db, monkeypatch):
    """The feature itself must keep working once the time is real."""
    settings_service.put(db, "sleep_schedule", {"enabled": True, "off": "21:30", "on": "06:30"})
    db.commit()

    calls: list[str] = []
    monkeypatch.setattr(display_service, "is_display_on", lambda: True)
    monkeypatch.setattr(display_service, "display_off", lambda: calls.append("off") or True)
    _force_clock(monkeypatch, True)
    # the tick imports this at call time, so patching the module attribute wins
    monkeypatch.setattr("app.services.sleep_service.should_be_asleep", lambda *_: True)

    scheduler_mod._sleep_tick()
    assert calls == ["off"]


def test_sleep_window_wraps_midnight():
    assert should_be_asleep(datetime(2026, 8, 6, 22, 0), "21:30", "06:30") is True
    assert should_be_asleep(datetime(2026, 8, 6, 3, 0), "21:30", "06:30") is True
    assert should_be_asleep(datetime(2026, 8, 6, 12, 0), "21:30", "06:30") is False
