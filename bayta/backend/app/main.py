import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import calendar, countdowns, health, profiles, stream, weather
from app.api import settings as settings_api
from app.core import scheduler
from app.core.config import get_settings
from app.core.events import bus
from app.db.migrate import upgrade_to_head

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.ensure_dirs()
    bus.attach_loop(asyncio.get_running_loop())
    await run_in_threadpool(upgrade_to_head)
    if settings.scheduler_enabled:
        scheduler.start()
    yield
    scheduler.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="Bayta", version=settings.version, docs_url="/api/docs", lifespan=lifespan)

    for router in (
        health.router,
        calendar.router,
        profiles.router,
        settings_api.router,
        countdowns.router,
        weather.router,
        stream.router,
    ):
        app.include_router(router, prefix="/api")

    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str) -> FileResponse:
            candidate = FRONTEND_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
