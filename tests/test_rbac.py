"""Tests for role-based access control across all routers."""

import secrets
import uuid

import bcrypt
import pytest

from primer.common.models import Engineer, Team
from primer.common.models import Session as SessionModel
from primer.server.services.auth_service import create_access_token


@pytest.fixture
def team_a(db_session):
    team = Team(name=f"Team-A-{uuid.uuid4().hex[:6]}")
    db_session.add(team)
    db_session.flush()
    return team


@pytest.fixture
def team_b(db_session):
    team = Team(name=f"Team-B-{uuid.uuid4().hex[:6]}")
    db_session.add(team)
    db_session.flush()
    return team


@pytest.fixture
def admin_engineer(db_session, team_a):
    eng = Engineer(
        name="Admin",
        email=f"admin-{uuid.uuid4().hex[:6]}@example.com",
        api_key_hash="",
        team_id=team_a.id,
        role="admin",
    )
    db_session.add(eng)
    db_session.flush()
    return eng


@pytest.fixture
def team_lead_engineer(db_session, team_a):
    eng = Engineer(
        name="Team Lead",
        email=f"lead-{uuid.uuid4().hex[:6]}@example.com",
        api_key_hash="",
        team_id=team_a.id,
        role="team_lead",
    )
    db_session.add(eng)
    db_session.flush()
    return eng


@pytest.fixture
def regular_engineer(db_session, team_a):
    raw_key = f"primer_{secrets.token_urlsafe(32)}"
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    eng = Engineer(
        name="Regular Eng",
        email=f"regular-{uuid.uuid4().hex[:6]}@example.com",
        api_key_hash=hashed,
        team_id=team_a.id,
        role="engineer",
    )
    db_session.add(eng)
    db_session.flush()
    return eng, raw_key


@pytest.fixture
def other_team_engineer(db_session, team_b):
    eng = Engineer(
        name="Other Team",
        email=f"other-{uuid.uuid4().hex[:6]}@example.com",
        api_key_hash="",
        team_id=team_b.id,
        role="engineer",
    )
    db_session.add(eng)
    db_session.flush()
    return eng


def _jwt_cookie(engineer):
    token = create_access_token(engineer)
    return {"primer_access": token}


def _seed_session(db, engineer_id):
    sid = str(uuid.uuid4())
    s = SessionModel(
        id=sid,
        engineer_id=engineer_id,
        message_count=5,
        user_message_count=2,
        assistant_message_count=3,
        tool_call_count=1,
        input_tokens=100,
        output_tokens=50,
    )
    db.add(s)
    db.flush()
    return sid


# --- Sessions RBAC ---


def test_engineer_sees_only_own_sessions(client, db_session, regular_engineer, other_team_engineer):
    eng, _key = regular_engineer
    _seed_session(db_session, eng.id)
    _seed_session(db_session, other_team_engineer.id)

    r = client.get("/api/v1/sessions", cookies=_jwt_cookie(eng))
    assert r.status_code == 200
    data = r.json()
    assert all(s["engineer_id"] == eng.id for s in data)
    assert len(data) >= 1


def test_team_lead_sees_team_sessions(
    client, db_session, team_lead_engineer, regular_engineer, other_team_engineer
):
    eng, _ = regular_engineer
    _seed_session(db_session, eng.id)
    _seed_session(db_session, team_lead_engineer.id)
    _seed_session(db_session, other_team_engineer.id)

    r = client.get("/api/v1/sessions", cookies=_jwt_cookie(team_lead_engineer))
    assert r.status_code == 200
    data = r.json()
    # Should see team_a sessions (eng + team_lead), not team_b
    assert len(data) >= 2
    for s in data:
        # Verify all sessions belong to team_a engineers
        assert s["engineer_id"] in (eng.id, team_lead_engineer.id)


def test_admin_sees_all_sessions(
    client, db_session, admin_engineer, regular_engineer, other_team_engineer
):
    eng, _ = regular_engineer
    _seed_session(db_session, eng.id)
    _seed_session(db_session, other_team_engineer.id)

    r = client.get("/api/v1/sessions", cookies=_jwt_cookie(admin_engineer))
    assert r.status_code == 200
    data = r.json()
    engineer_ids = {s["engineer_id"] for s in data}
    assert eng.id in engineer_ids
    assert other_team_engineer.id in engineer_ids


def test_engineer_cannot_view_other_session(
    client, db_session, regular_engineer, other_team_engineer
):
    eng, _ = regular_engineer
    other_sid = _seed_session(db_session, other_team_engineer.id)

    r = client.get(f"/api/v1/sessions/{other_sid}", cookies=_jwt_cookie(eng))
    assert r.status_code == 403


# --- Engineers list RBAC ---


def test_engineer_cannot_list_engineers(client, regular_engineer):
    eng, _ = regular_engineer
    r = client.get("/api/v1/engineers", cookies=_jwt_cookie(eng))
    assert r.status_code == 403


def test_team_lead_sees_own_team_engineers(
    client, db_session, team_lead_engineer, regular_engineer, other_team_engineer
):
    r = client.get("/api/v1/engineers", cookies=_jwt_cookie(team_lead_engineer))
    assert r.status_code == 200
    data = r.json()
    eng, _ = regular_engineer
    ids = {e["id"] for e in data}
    assert eng.id in ids
    assert team_lead_engineer.id in ids
    assert other_team_engineer.id not in ids


def test_admin_sees_all_engineers(
    client, db_session, admin_engineer, regular_engineer, other_team_engineer
):
    r = client.get("/api/v1/engineers", cookies=_jwt_cookie(admin_engineer))
    assert r.status_code == 200
    data = r.json()
    ids = {e["id"] for e in data}
    eng, _ = regular_engineer
    assert eng.id in ids
    assert other_team_engineer.id in ids


# --- Admin key backward compat ---


def test_admin_key_still_works(client, admin_headers, db_session, regular_engineer):
    eng, _ = regular_engineer
    _seed_session(db_session, eng.id)

    r = client.get("/api/v1/sessions", headers=admin_headers)
    assert r.status_code == 200


def test_api_key_still_works_for_ingest(client, db_session):
    """Engineer API key auth via x-api-key header still works for ingest."""
    raw_key = f"primer_{secrets.token_urlsafe(32)}"
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    eng = Engineer(
        name="Ingest Eng",
        email=f"ingest-{uuid.uuid4().hex[:6]}@example.com",
        api_key_hash=hashed,
        role="engineer",
    )
    db_session.add(eng)
    db_session.flush()

    # Ingest endpoint uses api_key in payload, not auth context
    r = client.post(
        "/api/v1/ingest/session",
        json={
            "session_id": str(uuid.uuid4()),
            "api_key": raw_key,
            "message_count": 5,
            "user_message_count": 2,
            "assistant_message_count": 3,
            "tool_call_count": 1,
            "input_tokens": 100,
            "output_tokens": 50,
        },
    )
    assert r.status_code == 200


# --- PATCH engineer (admin only) ---


def test_admin_can_patch_engineer_role(client, db_session, admin_engineer, regular_engineer):
    eng, _ = regular_engineer
    r = client.patch(
        f"/api/v1/engineers/{eng.id}",
        json={"role": "team_lead"},
        cookies=_jwt_cookie(admin_engineer),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "team_lead"


def test_non_admin_cannot_patch_engineer(client, db_session, team_lead_engineer, regular_engineer):
    eng, _ = regular_engineer
    r = client.patch(
        f"/api/v1/engineers/{eng.id}",
        json={"role": "admin"},
        cookies=_jwt_cookie(team_lead_engineer),
    )
    assert r.status_code == 403


# --- Analytics RBAC ---


def test_engineer_analytics_scoped_to_own(
    client, db_session, regular_engineer, other_team_engineer
):
    eng, _ = regular_engineer
    _seed_session(db_session, eng.id)
    _seed_session(db_session, other_team_engineer.id)

    r = client.get("/api/v1/analytics/overview", cookies=_jwt_cookie(eng))
    assert r.status_code == 200
    data = r.json()
    # Engineer sees only their own sessions
    assert data["total_engineers"] == 1
    assert data["total_sessions"] >= 1


# --- Teams RBAC ---


def test_engineer_sees_own_team(client, db_session, regular_engineer, team_a, team_b):
    eng, _ = regular_engineer
    r = client.get("/api/v1/teams", cookies=_jwt_cookie(eng))
    assert r.status_code == 200
    data = r.json()
    ids = {t["id"] for t in data}
    assert team_a.id in ids
    assert team_b.id not in ids


def test_non_admin_cannot_create_team(client, team_lead_engineer):
    r = client.post(
        "/api/v1/teams",
        json={"name": "Forbidden Team"},
        cookies=_jwt_cookie(team_lead_engineer),
    )
    assert r.status_code == 403
