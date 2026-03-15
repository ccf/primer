from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import get_db
from primer.common.models import Engineer, IngestEvent, Team
from primer.common.models import Session as SessionModel
from primer.common.schemas import (
    AuditLogResponse,
    FacetNormalizationSummary,
    IngestEventResponse,
    MeasurementIntegrityStats,
    PaginatedResponse,
    SystemStats,
    WorkflowProfileBackfillSummary,
)
from primer.server.deps import AuthContext, require_role
from primer.server.services import audit_service
from primer.server.services.measurement_integrity_service import (
    get_measurement_integrity_stats,
    normalize_existing_facets,
)

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


@router.get("/measurement-integrity", response_model=MeasurementIntegrityStats)
def measurement_integrity(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    return get_measurement_integrity_stats(db)


@router.get("/ingest-events", response_model=PaginatedResponse[IngestEventResponse])
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
    total_count = q.count()
    items = q.offset(offset).limit(limit).all()
    return PaginatedResponse(items=items, total_count=total_count, limit=limit, offset=offset)


@router.post("/backfill-facets")
def backfill_facets(
    background_tasks: BackgroundTasks,
    limit: int = Query(default=50, le=500),
    auth: AuthContext = Depends(require_role("admin")),
):
    """Trigger LLM facet extraction for sessions that are missing facets."""
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=422, detail="PRIMER_ANTHROPIC_API_KEY is not configured")
    if not settings.facet_extraction_enabled:
        raise HTTPException(
            status_code=422,
            detail="Facet extraction is disabled (set PRIMER_FACET_EXTRACTION_ENABLED=true)",
        )

    from primer.server.services.facet_extraction_service import backfill_facets as _backfill

    background_tasks.add_task(_backfill, limit)
    return {"status": "started", "limit": limit}


@router.post("/normalize-facets", response_model=FacetNormalizationSummary)
def normalize_facets(
    request: Request,
    limit: int = Query(default=500, le=5000),
    dry_run: bool = Query(default=True),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    summary = normalize_existing_facets(db, limit=limit, dry_run=dry_run)
    if not dry_run:
        ip = request.client.host if request.client else None
        audit_service.log_action(
            db,
            auth,
            "normalize",
            "session_facets",
            details={
                "limit": limit,
                "dry_run": dry_run,
                **summary,
            },
            ip_address=ip,
        )
        db.commit()
    return summary


@router.post("/backfill-workflow-profiles", response_model=WorkflowProfileBackfillSummary)
def backfill_workflow_profiles(
    request: Request,
    limit: int = Query(default=500, le=5000),
    recompute: bool = Query(default=False),
    dry_run: bool = Query(default=True),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    from primer.server.services.workflow_profile_service import (
        backfill_workflow_profiles as _backfill,
    )

    summary = _backfill(db, limit=limit, recompute=recompute, dry_run=dry_run)
    if not dry_run:
        ip = request.client.host if request.client else None
        audit_service.log_action(
            db,
            auth,
            "backfill",
            "session_workflow_profiles",
            details={
                "limit": limit,
                "recompute": recompute,
                "dry_run": dry_run,
                **summary,
            },
            ip_address=ip,
        )
        db.commit()
    return summary


@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
def list_audit_logs(
    resource_type: str | None = None,
    action: str | None = None,
    actor_id: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    items, total_count = audit_service.get_audit_logs(
        db,
        resource_type=resource_type,
        action=action,
        actor_id=actor_id,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse(items=items, total_count=total_count, limit=limit, offset=offset)
