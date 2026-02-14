from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.models import Engineer, IngestEvent, Team
from primer.common.models import Session as SessionModel
from primer.common.schemas import IngestEventResponse, SystemStats
from primer.server.deps import AuthContext, require_role

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
    db_type = engine.url.drivername if hasattr(engine, "url") else "unknown"

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
