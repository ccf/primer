import secrets

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.models import Engineer
from primer.common.schemas import (
    EngineerCreate,
    EngineerCreateResponse,
    EngineerResponse,
    SessionResponse,
)
from primer.server.deps import require_admin

router = APIRouter(prefix="/api/v1/engineers", tags=["engineers"])


@router.post("", response_model=EngineerCreateResponse)
def create_engineer(
    payload: EngineerCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    existing = db.query(Engineer).filter(Engineer.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Engineer with this email already exists")

    raw_key = f"primer_{secrets.token_urlsafe(32)}"
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()

    engineer = Engineer(
        name=payload.name,
        email=payload.email,
        team_id=payload.team_id,
        api_key_hash=hashed,
    )
    db.add(engineer)
    db.commit()
    db.refresh(engineer)
    return EngineerCreateResponse(engineer=EngineerResponse.model_validate(engineer), api_key=raw_key)


@router.get("", response_model=list[EngineerResponse])
def list_engineers(
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    return db.query(Engineer).all()


@router.get("/{engineer_id}/sessions", response_model=list[SessionResponse])
def list_engineer_sessions(
    engineer_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    engineer = db.query(Engineer).filter(Engineer.id == engineer_id).first()
    if not engineer:
        raise HTTPException(status_code=404, detail="Engineer not found")
    return engineer.sessions
