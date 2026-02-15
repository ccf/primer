import pathlib

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
)

FRONTEND_DIST = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="Primer", version="0.1.0")

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

    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


app = create_app()
