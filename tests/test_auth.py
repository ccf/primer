"""Tests for the auth endpoints (GitHub OAuth, JWT, refresh tokens)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import bcrypt
import jwt

from primer.common.config import settings
from primer.common.models import DeviceToken, Engineer, RefreshToken, Team
from primer.server.services.auth_service import (
    JWT_ALGORITHM,
    _hash_token,
    create_access_token,
    create_refresh_token,
    verify_access_token,
)


def test_github_login_returns_authorize_url(client):
    """GET /auth/github/login returns a GitHub authorize URL and state."""
    with patch.object(settings, "github_client_id", "test-client-id"):
        r = client.get("/api/v1/auth/github/login")
    assert r.status_code == 200
    data = r.json()
    assert "url" in data
    assert "state" in data
    assert "github.com/login/oauth/authorize" in data["url"]
    assert "test-client-id" in data["url"]


def test_github_login_not_configured(client):
    """GET /auth/github/login returns 501 when client_id is empty."""
    with patch.object(settings, "github_client_id", ""):
        r = client.get("/api/v1/auth/github/login")
    assert r.status_code == 501


def test_github_callback_creates_engineer(client, db_session):
    """POST /auth/github/callback provisions a new engineer and sets cookies."""
    mock_profile = {
        "github_id": 99999,
        "github_username": "testuser",
        "avatar_url": "https://avatars.example.com/99999",
        "display_name": "Test User",
        "email": "testuser@example.com",
    }
    with patch(
        "primer.server.routers.auth.exchange_github_code",
        new_callable=AsyncMock,
        return_value=mock_profile,
    ):
        r = client.post(
            "/api/v1/auth/github/callback",
            json={"code": "test-code", "state": "test-state"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "testuser@example.com"
    assert data["github_username"] == "testuser"
    assert data["role"] == "engineer"

    # Check cookies were set
    assert "primer_access" in r.cookies
    assert "primer_refresh" in r.cookies

    # Verify engineer was created in DB
    eng = db_session.query(Engineer).filter(Engineer.email == "testuser@example.com").first()
    assert eng is not None
    assert eng.github_id == 99999


def test_github_callback_links_existing_engineer(client, db_session):
    """POST /auth/github/callback links to an existing engineer by email."""
    # Pre-create an engineer with matching email
    hashed = bcrypt.hashpw(b"test-key", bcrypt.gensalt()).decode()
    eng = Engineer(
        name="Existing Eng",
        email="existing@example.com",
        api_key_hash=hashed,
    )
    db_session.add(eng)
    db_session.flush()

    mock_profile = {
        "github_id": 88888,
        "github_username": "existinguser",
        "avatar_url": "https://avatars.example.com/88888",
        "display_name": "Existing User",
        "email": "existing@example.com",
    }
    with patch(
        "primer.server.routers.auth.exchange_github_code",
        new_callable=AsyncMock,
        return_value=mock_profile,
    ):
        r = client.post(
            "/api/v1/auth/github/callback",
            json={"code": "test-code", "state": "test-state"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == eng.id  # Same engineer, linked
    assert data["github_username"] == "existinguser"


def test_github_callback_invalid_code(client):
    """POST /auth/github/callback returns 400 if GitHub exchange fails."""
    with patch(
        "primer.server.routers.auth.exchange_github_code",
        new_callable=AsyncMock,
        side_effect=Exception("bad code"),
    ):
        r = client.post(
            "/api/v1/auth/github/callback",
            json={"code": "bad-code", "state": "test-state"},
        )
    assert r.status_code == 400


def test_auth_me_with_valid_cookie(client, db_session):
    """GET /auth/me returns profile when a valid JWT cookie is present."""
    team = Team(name="Me Test Team")
    db_session.add(team)
    db_session.flush()
    eng = Engineer(
        name="Cookie Eng",
        email="cookie@example.com",
        api_key_hash="",
        team_id=team.id,
        role="engineer",
    )
    db_session.add(eng)
    db_session.flush()

    token = create_access_token(eng)
    r = client.get("/api/v1/auth/me", cookies={"primer_access": token})
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == eng.id
    assert data["role"] == "engineer"


def test_auth_me_without_cookie(client):
    """GET /auth/me returns 401 when no cookie is set."""
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_refresh_rotates_tokens(client, db_session):
    """POST /auth/refresh rotates the refresh token and returns new cookies."""
    eng = Engineer(
        name="Refresh Eng",
        email="refresh@example.com",
        api_key_hash="",
        role="engineer",
    )
    db_session.add(eng)
    db_session.flush()

    raw_refresh = create_refresh_token(db_session, eng)
    db_session.flush()

    r = client.post("/api/v1/auth/refresh", cookies={"primer_refresh": raw_refresh})
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == eng.id

    # New cookies set
    assert "primer_access" in r.cookies

    # Old token should be revoked
    old_hash = _hash_token(raw_refresh)
    old_token = db_session.query(RefreshToken).filter(RefreshToken.token_hash == old_hash).first()
    assert old_token.revoked is True


def test_refresh_without_cookie(client):
    """POST /auth/refresh returns 401 without cookie."""
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


def test_device_token_lifecycle_with_engineer_api_key(client, engineer_with_key, db_session):
    eng, api_key = engineer_with_key

    create_resp = client.post(
        "/api/v1/auth/device-tokens",
        json={"name": "Laptop"},
        headers={"x-api-key": api_key},
    )
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["device_token"]["engineer_id"] == eng.id
    assert create_data["device_token"]["name"] == "Laptop"
    assert create_data["raw_token"].startswith("primer_dev_")

    stored = (
        db_session.query(DeviceToken)
        .filter(DeviceToken.id == create_data["device_token"]["id"])
        .one()
    )
    assert stored.token_last_four == create_data["raw_token"][-4:]

    list_resp = client.get("/api/v1/auth/device-tokens", headers={"x-api-key": api_key})
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert len(listed) == 1
    assert listed[0]["token_last_four"] == create_data["raw_token"][-4:]

    revoke_resp = client.delete(
        f"/api/v1/auth/device-tokens/{create_data['device_token']['id']}",
        headers={"x-api-key": api_key},
    )
    assert revoke_resp.status_code == 200
    db_session.refresh(stored)
    assert stored.revoked is True


def test_device_setup_code_exchange_creates_device_token(client, engineer_with_key, db_session):
    eng, api_key = engineer_with_key

    create_resp = client.post(
        "/api/v1/auth/device-token-setup-codes",
        json={"expires_in_minutes": 15},
        headers={"x-api-key": api_key},
    )
    assert create_resp.status_code == 200
    setup_code = create_resp.json()["setup_code"]

    exchange_resp = client.post(
        "/api/v1/auth/device-token-setup-codes/exchange",
        json={"setup_code": setup_code, "device_name": "Laptop"},
    )
    assert exchange_resp.status_code == 200
    data = exchange_resp.json()
    assert data["engineer"]["id"] == eng.id
    assert data["device_token"]["name"] == "Laptop"
    assert data["raw_token"].startswith("primer_dev_")

    replay_resp = client.post(
        "/api/v1/auth/device-token-setup-codes/exchange",
        json={"setup_code": setup_code},
    )
    assert replay_resp.status_code == 401


def test_logout_clears_cookies(client):
    """POST /auth/logout clears both cookies."""
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_verify_access_token_expired():
    """verify_access_token returns None for expired tokens."""
    payload = {
        "sub": "test-id",
        "role": "engineer",
        "team_id": None,
        "type": "access",
        "iat": datetime.now(UTC) - timedelta(hours=1),
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    assert verify_access_token(token) is None


def test_verify_access_token_wrong_type():
    """verify_access_token returns None for non-access type tokens."""
    payload = {
        "sub": "test-id",
        "role": "engineer",
        "type": "refresh",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    assert verify_access_token(token) is None
