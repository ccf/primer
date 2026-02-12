from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.models import Team
from primer.common.schemas import TeamCreate, TeamResponse
from primer.server.deps import require_admin

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


@router.post("", response_model=TeamResponse)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    existing = db.query(Team).filter(Team.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Team already exists")

    team = Team(name=payload.name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("", response_model=list[TeamResponse])
def list_teams(
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    return db.query(Team).all()
