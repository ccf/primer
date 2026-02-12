from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.models import Session as SessionModel
from primer.common.schemas import SessionDetailResponse, SessionResponse
from primer.server.deps import require_admin

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    engineer_id: str | None = None,
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    q = db.query(SessionModel)
    if engineer_id:
        q = q.filter(SessionModel.engineer_id == engineer_id)
    if team_id:
        from primer.common.models import Engineer

        q = q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)
    return q.order_by(SessionModel.started_at.desc()).offset(offset).limit(limit).all()


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
