import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import get_db
from primer.common.schemas import EngineerResponse
from primer.server.services.auth_service import (
    create_access_token,
    create_refresh_token,
    exchange_github_code,
    find_or_create_engineer,
    get_github_authorize_url,
    rotate_refresh_token,
    verify_access_token,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class GithubLoginResponse(BaseModel):
    url: str
    state: str


class GithubCallbackRequest(BaseModel):
    code: str
    state: str


def _is_secure() -> bool:
    return settings.base_url.startswith("https")


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = _is_secure()
    response.set_cookie(
        key="primer_access",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/api",
        max_age=settings.jwt_access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="primer_refresh",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/api/v1/auth/refresh",
        max_age=settings.jwt_refresh_token_expire_days * 86400,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="primer_access", path="/api")
    response.delete_cookie(key="primer_refresh", path="/api/v1/auth/refresh")


@router.get("/github/login", response_model=GithubLoginResponse)
def github_login():
    if not settings.github_client_id:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured")
    state = secrets.token_urlsafe(32)
    url = get_github_authorize_url(state)
    return GithubLoginResponse(url=url, state=state)


@router.post("/github/callback", response_model=EngineerResponse)
async def github_callback(
    payload: GithubCallbackRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        github_profile = await exchange_github_code(payload.code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"GitHub auth failed: {exc}") from exc

    engineer = find_or_create_engineer(db, github_profile)
    access_token = create_access_token(engineer)
    refresh_token = create_refresh_token(db, engineer)
    db.commit()

    _set_auth_cookies(response, access_token, refresh_token)
    return EngineerResponse.model_validate(engineer)


@router.post("/refresh", response_model=EngineerResponse)
def refresh(
    response: Response,
    primer_refresh: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not primer_refresh:
        raise HTTPException(status_code=401, detail="No refresh token")

    result = rotate_refresh_token(db, primer_refresh)
    if not result:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    engineer, access_token, new_refresh = result
    db.commit()

    _set_auth_cookies(response, access_token, new_refresh)
    return EngineerResponse.model_validate(engineer)


@router.post("/logout")
def logout(response: Response):
    _clear_auth_cookies(response)
    return {"status": "ok"}


@router.get("/me", response_model=EngineerResponse)
def me(
    primer_access: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not primer_access:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_access_token(primer_access)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    from primer.common.models import Engineer

    engineer = db.query(Engineer).filter(Engineer.id == payload["sub"]).first()
    if not engineer:
        raise HTTPException(status_code=401, detail="Engineer not found")

    return EngineerResponse.model_validate(engineer)
