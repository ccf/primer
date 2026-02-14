from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.models import Team
from primer.common.schemas import TeamCreate, TeamResponse
from primer.server.deps import AuthContext, get_auth_context, require_role

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


@router.post("", response_model=TeamResponse)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
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
    auth: AuthContext = Depends(get_auth_context),
):
    if auth.role == "admin":
        return db.query(Team).all()
    # engineer and team_lead: only own team
    if auth.team_id:
        return db.query(Team).filter(Team.id == auth.team_id).all()
    return []


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Role-based access
    if auth.role != "admin" and auth.team_id != team_id:
        raise HTTPException(status_code=403, detail="Not your team")

    return team
