import asyncio
import logging
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from primer.common.config import settings
from primer.server.middleware import limiter, rate_limit_exceeded_handler
from primer.server.routers import (
    admin,
    alert_configs,
    alerts,
    analytics,
    auth,
    engineers,
    health,
    ingest,
    notifications,
    sessions,
    teams,
    webhooks,
)

logger = logging.getLogger(__name__)

FRONTEND_DIST = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"


async def _narrative_refresh_loop() -> None:
    """Background loop that refreshes all narrative caches periodically."""
    from primer.common.database import SessionLocal
    from primer.server.services.narrative_service import refresh_all_narratives

    await asyncio.sleep(30)  # Initial delay to let the server start up
    while True:
        try:
            db = SessionLocal()
            try:
                count = await asyncio.to_thread(refresh_all_narratives, db)
                db.commit()
                logger.info("Narrative auto-refresh completed: %d narratives refreshed", count)
            finally:
                db.close()
        except Exception:
            logger.exception("Narrative auto-refresh failed")
        await asyncio.sleep(settings.narrative_cache_ttl_hours * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if settings.narrative_auto_refresh and settings.anthropic_api_key:
        task = asyncio.create_task(_narrative_refresh_loop())
    yield
    if task:
        task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="Primer", version="0.1.0", lifespan=lifespan)

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(engineers.router)
    app.include_router(teams.router)
    app.include_router(ingest.router)
    app.include_router(sessions.router)
    app.include_router(analytics.router)
    app.include_router(alerts.router)
    app.include_router(alert_configs.router)
    app.include_router(notifications.router)
    app.include_router(admin.router)
    app.include_router(webhooks.router)

    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


app = create_app()
