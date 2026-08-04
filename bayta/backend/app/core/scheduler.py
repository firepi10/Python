"""Background jobs. One in-process APScheduler instance; sync jobs run in the
default thread executor so the (single-writer) SQLite session usage stays sync."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(
    job_defaults={"coalesce": True, "misfire_grace_time": 300, "max_instances": 1}
)


def register_jobs() -> None:
    from app.sync.weather_sync import sync_weather

    scheduler.add_job(
        sync_weather, "interval", minutes=15, id="weather_sync", replace_existing=True
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
