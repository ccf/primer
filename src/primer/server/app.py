from fastapi import FastAPI

from primer.server.routers import analytics, engineers, health, ingest, sessions, teams


def create_app() -> FastAPI:
    app = FastAPI(title="Primer", version="0.1.0")
    app.include_router(health.router)
    app.include_router(engineers.router)
    app.include_router(teams.router)
    app.include_router(ingest.router)
    app.include_router(sessions.router)
    app.include_router(analytics.router)
    return app


app = create_app()
