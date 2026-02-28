from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import get_db
from primer.common.models import Engineer, IngestEvent, Team
from primer.common.models import Session as SessionModel
from primer.common.schemas import AuditLogResponse, IngestEventResponse, SystemStats
from primer.server.deps import AuthContext, require_role
from primer.server.services import audit_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/system-stats", response_model=SystemStats)
def system_stats(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    total_engineers = db.query(Engineer).count()
    active_engineers = db.query(Engineer).filter(Engineer.is_active == True).count()  # noqa: E712
    total_teams = db.query(Team).count()
    total_sessions = db.query(SessionModel).count()
    total_ingest_events = db.query(IngestEvent).count()

    # Determine database type from the engine URL
    engine = db.get_bind()
    drivername = engine.url.drivername if hasattr(engine, "url") else "unknown"
    raw = drivername.split("+")[0]
    db_type = raw.replace("postgresql", "PostgreSQL").replace("sqlite", "SQLite")

    return SystemStats(
        total_engineers=total_engineers,
        active_engineers=active_engineers,
        total_teams=total_teams,
        total_sessions=total_sessions,
        total_ingest_events=total_ingest_events,
        database_type=db_type,
    )


@router.get("/ingest-events", response_model=list[IngestEventResponse])
def list_ingest_events(
    engineer_id: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    q = db.query(IngestEvent)
    if engineer_id:
        q = q.filter(IngestEvent.engineer_id == engineer_id)
    if status:
        q = q.filter(IngestEvent.status == status)
    q = q.order_by(IngestEvent.created_at.desc())
    return q.offset(offset).limit(limit).all()


@router.post("/backfill-facets")
def backfill_facets(
    background_tasks: BackgroundTasks,
    limit: int = Query(default=50, le=500),
    auth: AuthContext = Depends(require_role("admin")),
):
    """Trigger LLM facet extraction for sessions that are missing facets."""
    if not settings.anthropic_api_key:
        return {"error": "PRIMER_ANTHROPIC_API_KEY is not configured"}
    if not settings.facet_extraction_enabled:
        return {"error": "Facet extraction is disabled (set PRIMER_FACET_EXTRACTION_ENABLED=true)"}

    from primer.server.services.facet_extraction_service import backfill_facets as _backfill

    background_tasks.add_task(_backfill, limit)
    return {"status": "started", "limit": limit}


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    resource_type: str | None = None,
    action: str | None = None,
    actor_id: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    return audit_service.get_audit_logs(
        db,
        resource_type=resource_type,
        action=action,
        actor_id=actor_id,
        limit=limit,
        offset=offset,
    )
