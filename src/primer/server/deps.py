from dataclasses import dataclass

import bcrypt
from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import get_db
from primer.common.models import Engineer
from primer.server.services.auth_service import verify_access_token


def require_admin(x_admin_key: str = Header()) -> str:
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return x_admin_key


def _require_active_engineer(
    engineer: Engineer | None,
    *,
    missing_detail: str,
) -> Engineer:
    if not engineer:
        raise HTTPException(status_code=401, detail=missing_detail)
    if not engineer.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    return engineer


def _find_engineer_by_api_key(api_key: str, db: Session) -> Engineer | None:
    encoded_key = api_key.encode()
    engineers = db.query(Engineer).filter(
        Engineer.api_key_hash.is_not(None),
        Engineer.api_key_hash != "",
    )
    for eng in engineers:
        if bcrypt.checkpw(encoded_key, eng.api_key_hash.encode()):
            return eng
    return None


def verify_api_key(api_key: str, db: Session) -> Engineer:
    """Verify an API key against stored hashes. Returns the engineer or raises."""
    engineer = _find_engineer_by_api_key(api_key, db)
    return _require_active_engineer(engineer, missing_detail="Invalid API key")


def require_engineer(x_api_key: str = Header(), db: Session = Depends(get_db)) -> Engineer:
    return verify_api_key(x_api_key, db)


@dataclass
class AuthContext:
    engineer_id: str | None  # None for admin-key auth
    role: str  # "engineer" | "team_lead" | "admin"
    team_id: str | None


def get_auth_context(
    request: Request,
    db: Session = Depends(get_db),
    primer_access: str | None = Cookie(default=None),
    x_admin_key: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> AuthContext:
    """Unified auth: try JWT cookie → admin key header → API key header."""
    # 1. JWT cookie
    if primer_access:
        payload = verify_access_token(primer_access)
        if payload:
            eng = _require_active_engineer(
                db.query(Engineer).filter(Engineer.id == payload["sub"]).first(),
                missing_detail="Engineer not found",
            )
            return AuthContext(
                engineer_id=eng.id,
                role=eng.role,
                team_id=eng.team_id,
            )

    # 2. Admin key header
    if x_admin_key and x_admin_key == settings.admin_api_key:
        return AuthContext(engineer_id=None, role="admin", team_id=None)

    # 3. API key header
    if x_api_key:
        eng = verify_api_key(x_api_key, db)
        return AuthContext(
            engineer_id=eng.id,
            role=eng.role,
            team_id=eng.team_id,
        )

    raise HTTPException(status_code=401, detail="Authentication required")


def require_role(*allowed_roles: str):
    """Dependency factory: checks that auth.role is in allowed_roles."""

    def _check(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if auth.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return auth

    return _check
