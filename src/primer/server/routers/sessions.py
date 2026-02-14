from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.models import Engineer
from primer.common.models import Session as SessionModel
from primer.common.schemas import SessionDetailResponse, SessionResponse
from primer.server.deps import AuthContext, get_auth_context

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    engineer_id: str | None = None,
    team_id: str | None = None,
    project_name: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    q = db.query(SessionModel)

    # Role-based scoping
    if auth.role == "engineer":
        q = q.filter(SessionModel.engineer_id == auth.engineer_id)
    elif auth.role == "team_lead":
        q = q.join(Engineer).filter(Engineer.team_id == auth.team_id)
    else:
        # Admin: apply optional filters
        if engineer_id:
            q = q.filter(SessionModel.engineer_id == engineer_id)
        if team_id:
            q = q.join(Engineer).filter(Engineer.team_id == team_id)

    if project_name:
        q = q.filter(SessionModel.project_name == project_name)
    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)
    return q.order_by(SessionModel.started_at.desc()).offset(offset).limit(limit).all()


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Role-based ownership check
    if auth.role == "engineer" and session.engineer_id != auth.engineer_id:
        raise HTTPException(status_code=403, detail="Not your session")
    if auth.role == "team_lead":
        eng = db.query(Engineer).filter(Engineer.id == session.engineer_id).first()
        if not eng or eng.team_id != auth.team_id:
            raise HTTPException(status_code=403, detail="Not your team's session")

    return session
