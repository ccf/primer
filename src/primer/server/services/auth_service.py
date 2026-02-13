import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
import jwt
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.models import Engineer, RefreshToken

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"  # noqa: S105  # nosec B105
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

JWT_ALGORITHM = "HS256"


def get_github_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "read:user user:email",
        "state": state,
    }
    return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_github_code(code: str) -> dict:
    """Exchange authorization code for GitHub user profile + primary email."""
    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data["access_token"]

        auth_headers = {"Authorization": f"Bearer {access_token}"}

        # Fetch user profile
        user_resp = await client.get(GITHUB_USER_URL, headers=auth_headers)
        user_resp.raise_for_status()
        user = user_resp.json()

        # Fetch primary email
        email = user.get("email")
        if not email:
            emails_resp = await client.get(GITHUB_EMAILS_URL, headers=auth_headers)
            emails_resp.raise_for_status()
            for e in emails_resp.json():
                if e.get("primary") and e.get("verified"):
                    email = e["email"]
                    break

        return {
            "github_id": user["id"],
            "github_username": user["login"],
            "avatar_url": user.get("avatar_url"),
            "display_name": user.get("name") or user["login"],
            "email": email or f"{user['login']}@users.noreply.github.com",
        }


def find_or_create_engineer(db: Session, github_profile: dict) -> Engineer:
    """Match by github_id first, then email, then auto-provision."""
    # 1. Match by github_id (returning user)
    engineer = db.query(Engineer).filter(Engineer.github_id == github_profile["github_id"]).first()
    if engineer:
        # Update profile fields
        engineer.github_username = github_profile["github_username"]
        engineer.avatar_url = github_profile["avatar_url"]
        engineer.display_name = github_profile["display_name"]
        db.flush()
        return engineer

    # 2. Match by email (link existing engineer to GitHub)
    engineer = db.query(Engineer).filter(Engineer.email == github_profile["email"]).first()
    if engineer:
        engineer.github_id = github_profile["github_id"]
        engineer.github_username = github_profile["github_username"]
        engineer.avatar_url = github_profile["avatar_url"]
        engineer.display_name = github_profile["display_name"]
        db.flush()
        return engineer

    # 3. Auto-provision new engineer
    engineer = Engineer(
        name=github_profile["display_name"],
        email=github_profile["email"],
        github_id=github_profile["github_id"],
        github_username=github_profile["github_username"],
        avatar_url=github_profile["avatar_url"],
        display_name=github_profile["display_name"],
        api_key_hash="",
        role="engineer",
    )
    db.add(engineer)
    db.flush()
    return engineer


def create_access_token(engineer: Engineer) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": engineer.id,
        "role": engineer.role,
        "team_id": engineer.team_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_refresh_token(db: Session, engineer: Engineer) -> str:
    """Create a refresh token, store its hash, return the raw token."""
    raw = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    token = RefreshToken(
        engineer_id=engineer.id,
        token_hash=_hash_token(raw),
        expires_at=expires_at,
    )
    db.add(token)
    db.flush()
    return raw


def verify_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token. Returns payload or None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.InvalidTokenError:
        return None


def rotate_refresh_token(db: Session, raw_token: str) -> tuple[Engineer, str, str] | None:
    """Validate refresh token, revoke old, issue new pair. Returns (engineer, access, refresh)."""
    token_hash = _hash_token(raw_token)
    stored = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked.is_(False),
        )
        .first()
    )
    if not stored:
        return None

    if stored.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        stored.revoked = True
        db.flush()
        return None

    # Revoke old token
    stored.revoked = True
    db.flush()

    engineer = db.query(Engineer).filter(Engineer.id == stored.engineer_id).first()
    if not engineer:
        return None

    access = create_access_token(engineer)
    refresh = create_refresh_token(db, engineer)
    return engineer, access, refresh
