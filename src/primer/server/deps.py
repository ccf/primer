from dataclasses import dataclass

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import get_db
from primer.common.models import Engineer
from primer.server.services.auth_service import (
    find_engineer_by_api_key,
    find_engineer_by_device_token,
    verify_access_token,
)


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


def verify_api_key(api_key: str, db: Session) -> Engineer:
    """Verify an API key against stored hashes. Returns the engineer or raises."""
    engineer = find_engineer_by_api_key(db, api_key)
    return _require_active_engineer(engineer, missing_detail="Invalid API key")


def verify_device_token(device_token: str, db: Session) -> Engineer:
    engineer = find_engineer_by_device_token(db, device_token)
    return _require_active_engineer(engineer, missing_detail="Invalid device token")


def _header_value(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def require_engineer(
    x_api_key: str | None = Header(default=None),
    x_device_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Engineer:
    x_api_key = _header_value(x_api_key)
    x_device_token = _header_value(x_device_token)
    if x_device_token:
        return verify_device_token(x_device_token, db)
    if x_api_key:
        return verify_api_key(x_api_key, db)
    raise HTTPException(status_code=401, detail="Authentication required")


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
    x_device_token: str | None = Header(default=None),
) -> AuthContext:
    """Unified auth: try JWT cookie → admin key header → API key header."""
    x_admin_key = _header_value(x_admin_key)
    x_api_key = _header_value(x_api_key)
    x_device_token = _header_value(x_device_token)
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

    # 3. Device token header
    if x_device_token:
        eng = verify_device_token(x_device_token, db)
        return AuthContext(
            engineer_id=eng.id,
            role=eng.role,
            team_id=eng.team_id,
        )

    # 4. API key header
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
