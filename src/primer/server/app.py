import asyncio
import logging
import os
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
    explorer,
    finops,
    health,
    ingest,
    interventions,
    notifications,
    sessions,
    teams,
    webhooks,
)

logger = logging.getLogger(__name__)

FRONTEND_DIST = (
    pathlib.Path(os.environ["PRIMER_FRONTEND_DIST"])
    if os.environ.get("PRIMER_FRONTEND_DIST")
    else pathlib.Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
)


async def _narrative_refresh_loop() -> None:
    """Background loop that refreshes all narrative caches periodically."""
    from primer.common.database import SessionLocal
    from primer.server.services.narrative_service import refresh_all_narratives

    def _run_refresh() -> int:
        """Run in worker thread so the DB session is created and closed in the same thread."""
        db = SessionLocal()
        try:
            return refresh_all_narratives(db)
        finally:
            db.close()

    await asyncio.sleep(30)  # Initial delay to let the server start up
    while True:
        try:
            count = await asyncio.to_thread(_run_refresh)
            logger.info("Narrative auto-refresh completed: %d narratives refreshed", count)
        except Exception:
            logger.exception("Narrative auto-refresh failed")
        await asyncio.sleep(settings.narrative_cache_ttl_hours * 3600)


async def _background_job_worker_loop() -> None:
    from primer.common.database import SessionLocal
    from primer.server.services.background_job_service import (
        ensure_recurring_jobs,
        run_background_job_cycle,
    )
    from primer.server.services.observability_service import (
        record_counter,
        record_histogram,
        start_span,
    )

    while True:
        try:

            def _run_cycle() -> dict[str, int]:
                db = SessionLocal()
                try:
                    ensure_recurring_jobs(db)
                    return run_background_job_cycle(
                        db,
                        limit=settings.background_job_batch_size,
                        lease_seconds=settings.background_job_lease_seconds,
                    )
                finally:
                    db.close()

            with start_span("background_jobs.worker_cycle"):
                cycle_started = asyncio.get_running_loop().time()
                result = await asyncio.to_thread(_run_cycle)
                duration_ms = (asyncio.get_running_loop().time() - cycle_started) * 1000
                record_counter("primer.background_jobs.cycles", 1, None)
                record_histogram(
                    "primer.background_jobs.cycle.duration_ms",
                    duration_ms,
                    None,
                )
                if result["processed"] > 0:
                    record_counter(
                        "primer.background_jobs.cycle_processed",
                        result["processed"],
                        None,
                    )
                    record_counter(
                        "primer.background_jobs.executions_by_result",
                        result["succeeded"],
                        {"result": "succeeded"},
                    )
                    record_counter(
                        "primer.background_jobs.executions_by_result",
                        result["failed"],
                        {"result": "failed"},
                    )
            if result["processed"] > 0:
                logger.info(
                    "Background jobs processed: %d succeeded, %d failed",
                    result["succeeded"],
                    result["failed"],
                )
        except Exception:
            logger.exception("Background job worker loop failed")
        await asyncio.sleep(settings.background_job_poll_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if settings.background_jobs_enabled:
        task = asyncio.create_task(_background_job_worker_loop())
    elif settings.narrative_auto_refresh and settings.anthropic_api_key:
        task = asyncio.create_task(_narrative_refresh_loop())
    yield
    if task:
        task.cancel()


def create_app() -> FastAPI:
    from primer.server.services.observability_service import setup_observability

    app = FastAPI(title="Primer", version="0.1.0", lifespan=lifespan)
    setup_observability(app)

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

    # Demo mode: block all mutations
    if settings.demo_mode:
        from primer.server.demo_middleware import DemoReadOnlyMiddleware

        app.add_middleware(DemoReadOnlyMiddleware)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(engineers.router)
    app.include_router(teams.router)
    app.include_router(ingest.router)
    app.include_router(sessions.router)
    app.include_router(analytics.router)
    app.include_router(interventions.router)
    app.include_router(alerts.router)
    app.include_router(alert_configs.router)
    app.include_router(notifications.router)
    app.include_router(admin.router)
    app.include_router(webhooks.router)
    app.include_router(explorer.router)
    app.include_router(finops.router)

    if FRONTEND_DIST.is_dir():
        # Serve hashed asset files directly
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

        index_file = FRONTEND_DIST / "index.html"
        frontend_root = FRONTEND_DIST.resolve()

        # SPA catch-all: serve index.html for any non-API path so client-side
        # routes survive a hard refresh. Guards against path traversal by
        # resolving and verifying containment within FRONTEND_DIST.
        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str) -> FileResponse:
            if full_path:
                candidate = (FRONTEND_DIST / full_path).resolve()
                try:
                    candidate.relative_to(frontend_root)
                except ValueError:
                    return FileResponse(index_file)
                if candidate.is_file():
                    return FileResponse(candidate)
            return FileResponse(index_file)

    return app


app = create_app()
