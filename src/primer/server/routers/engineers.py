import secrets

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.models import Engineer
from primer.common.schemas import (
    EngineerCreate,
    EngineerCreateResponse,
    EngineerResponse,
    EngineerUpdate,
    SessionResponse,
)
from primer.server.deps import AuthContext, get_auth_context, require_role
from primer.server.services import audit_service

router = APIRouter(prefix="/api/v1/engineers", tags=["engineers"])


@router.post("", response_model=EngineerCreateResponse)
def create_engineer(
    payload: EngineerCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
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
    db.flush()
    ip = request.client.host if request.client else None
    audit_service.log_action(
        db,
        auth,
        "create",
        "engineer",
        engineer.id,
        details={"name": engineer.name, "email": engineer.email},
        ip_address=ip,
    )
    db.commit()
    db.refresh(engineer)
    return EngineerCreateResponse(
        engineer=EngineerResponse.model_validate(engineer), api_key=raw_key
    )


@router.get("", response_model=list[EngineerResponse])
def list_engineers(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    if auth.role == "engineer":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    q = db.query(Engineer)
    if not include_inactive:
        q = q.filter(Engineer.is_active == True)  # noqa: E712
    if auth.role == "team_lead":
        q = q.filter(Engineer.team_id == auth.team_id)
    return q.all()


@router.get("/{engineer_id}/sessions", response_model=list[SessionResponse])
def list_engineer_sessions(
    engineer_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    engineer = db.query(Engineer).filter(Engineer.id == engineer_id).first()
    if not engineer:
        raise HTTPException(status_code=404, detail="Engineer not found")

    # Scope check
    if auth.role == "engineer" and engineer.id != auth.engineer_id:
        raise HTTPException(status_code=403, detail="Not your sessions")
    if auth.role == "team_lead" and engineer.team_id != auth.team_id:
        raise HTTPException(status_code=403, detail="Not your team")

    return engineer.sessions


@router.patch("/{engineer_id}", response_model=EngineerResponse)
def update_engineer(
    engineer_id: str,
    payload: EngineerUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    engineer = db.query(Engineer).filter(Engineer.id == engineer_id).first()
    if not engineer:
        raise HTTPException(status_code=404, detail="Engineer not found")

    changes = {}
    if payload.role is not None:
        if payload.role not in ("engineer", "team_lead", "admin"):
            raise HTTPException(status_code=400, detail="Invalid role")
        changes["role"] = {"old": engineer.role, "new": payload.role}
        engineer.role = payload.role
    if payload.team_id is not None:
        changes["team_id"] = {"old": engineer.team_id, "new": payload.team_id}
        engineer.team_id = payload.team_id
    if payload.is_active is not None:
        changes["is_active"] = {"old": engineer.is_active, "new": payload.is_active}
        engineer.is_active = payload.is_active
    if payload.github_username is not None:
        changes["github_username"] = {
            "old": engineer.github_username,
            "new": payload.github_username,
        }
        engineer.github_username = payload.github_username
    if payload.avatar_url is not None:
        changes["avatar_url"] = {"old": engineer.avatar_url, "new": payload.avatar_url}
        engineer.avatar_url = payload.avatar_url
    if payload.display_name is not None:
        changes["display_name"] = {"old": engineer.display_name, "new": payload.display_name}
        engineer.display_name = payload.display_name

    ip = request.client.host if request.client else None
    audit_service.log_action(
        db,
        auth,
        "update",
        "engineer",
        engineer_id,
        details=changes if changes else None,
        ip_address=ip,
    )
    db.commit()
    db.refresh(engineer)
    return EngineerResponse.model_validate(engineer)


@router.delete("/{engineer_id}", response_model=EngineerResponse)
def deactivate_engineer(
    engineer_id: str,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    engineer = db.query(Engineer).filter(Engineer.id == engineer_id).first()
    if not engineer:
        raise HTTPException(status_code=404, detail="Engineer not found")
    engineer.is_active = False
    ip = request.client.host if request.client else None
    audit_service.log_action(db, auth, "deactivate", "engineer", engineer_id, ip_address=ip)
    db.commit()
    db.refresh(engineer)
    return EngineerResponse.model_validate(engineer)


@router.post("/{engineer_id}/rotate-key", response_model=EngineerCreateResponse)
def rotate_api_key(
    engineer_id: str,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    engineer = db.query(Engineer).filter(Engineer.id == engineer_id).first()
    if not engineer:
        raise HTTPException(status_code=404, detail="Engineer not found")
    raw_key = f"primer_{secrets.token_urlsafe(32)}"
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    engineer.api_key_hash = hashed
    ip = request.client.host if request.client else None
    audit_service.log_action(db, auth, "rotate_key", "engineer", engineer_id, ip_address=ip)
    db.commit()
    db.refresh(engineer)
    return EngineerCreateResponse(
        engineer=EngineerResponse.model_validate(engineer), api_key=raw_key
    )
