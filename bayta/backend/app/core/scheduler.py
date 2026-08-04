"""Background jobs. One in-process APScheduler instance; sync jobs run in the
default thread executor so the (single-writer) SQLite session usage stays sync."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(
    job_defaults={"coalesce": True, "misfire_grace_time": 300, "max_instances": 1}
)


def _refresh_occurrences_job() -> None:
    from app.db.session import session_factory
    from app.services.calendar_service import refresh_all_occurrences

    db = session_factory()()
    try:
        count = refresh_all_occurrences(db)
        logger.info("occurrence window refreshed for %d events", count)
    finally:
        db.close()


def register_jobs() -> None:
    from app.sync.caldav_sync import run_all as caldav_run_all
    from app.sync.weather_sync import sync_weather

    scheduler.add_job(
        sync_weather, "interval", minutes=15, id="weather_sync", replace_existing=True
    )
    scheduler.add_job(
        caldav_run_all,
        "interval",
        minutes=5,
        jitter=30,
        id="caldav_sync",
        replace_existing=True,
    )
    from app.sync.shared_album import sync_shared_albums

    scheduler.add_job(
        sync_shared_albums,
        "interval",
        minutes=30,
        jitter=120,
        id="shared_album_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _sleep_tick, "interval", minutes=1, id="sleep_scheduler", replace_existing=True
    )
    scheduler.add_job(
        _nightly_ui_reload,
        "cron",
        hour=3,
        minute=30,
        id="nightly_ui_reload",
        replace_existing=True,
    )


def _sleep_tick() -> None:
    from datetime import datetime

    from app.core.events import bus
    from app.db.session import session_factory
    from app.services import display_service, settings_service
    from app.services.sleep_service import should_be_asleep

    db = session_factory()()
    try:
        cfg = settings_service.get(db, "sleep_schedule") or {}
    finally:
        db.close()
    if not cfg.get("enabled"):
        return
    asleep = should_be_asleep(
        datetime.now(), cfg.get("off", "21:30"), cfg.get("on", "06:30")
    )
    if asleep and display_service.is_display_on():
        if display_service.display_off():
            bus.publish("sleep_state")
    elif not asleep and not display_service.is_display_on():
        if display_service.display_on():
            bus.publish("sleep_state")


def _nightly_ui_reload() -> None:
    """Chromium's memory creeps over weeks; a 3:30am reload resets it."""
    from app.core.events import bus

    bus.publish("reload")
    scheduler.add_job(
        _refresh_occurrences_job,
        "cron",
        hour=3,
        minute=0,
        id="occurrence_refresh",
        replace_existing=True,
    )


def start() -> None:
    register_jobs()
    scheduler.start()
    # Warm the weather cache shortly after boot (non-blocking).
    try:
        scheduler.modify_job("weather_sync", next_run_time=None)
        from datetime import UTC, datetime, timedelta

        scheduler.modify_job(
            "weather_sync", next_run_time=datetime.now(UTC) + timedelta(seconds=5)
        )
    except Exception:  # pragma: no cover - defensive
        logger.exception("could not prime weather job")


def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
