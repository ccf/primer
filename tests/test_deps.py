import pytest
from fastapi import HTTPException
from starlette.requests import Request

from primer.common.models import Engineer, Team
from primer.server.deps import get_auth_context, verify_api_key
from primer.server.services.auth_service import create_access_token


def _request() -> Request:
    return Request({"type": "http", "headers": []})


def test_verify_api_key_returns_engineer(engineer_with_key, db_session):
    engineer, raw_key = engineer_with_key

    verified = verify_api_key(raw_key, db_session)

    assert verified.id == engineer.id


def test_verify_api_key_rejects_deactivated_engineer(db_session):
    team = Team(name="Inactive Team")
    db_session.add(team)
    db_session.flush()

    import bcrypt

    raw_key = "primer_test_inactive_key"
    engineer = Engineer(
        name="Inactive Engineer",
        email="inactive@example.com",
        team_id=team.id,
        api_key_hash=bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode(),
        is_active=False,
    )
    db_session.add(engineer)
    db_session.flush()

    with pytest.raises(HTTPException, match="Account deactivated") as exc_info:
        verify_api_key(raw_key, db_session)

    assert exc_info.value.status_code == 403


def test_get_auth_context_rejects_missing_engineer_for_valid_cookie(db_session):
    team = Team(name="JWT Team")
    db_session.add(team)
    db_session.flush()

    engineer = Engineer(
        name="JWT Engineer",
        email="jwt@example.com",
        api_key_hash="",
        team_id=team.id,
        role="engineer",
    )
    db_session.add(engineer)
    db_session.flush()

    token = create_access_token(engineer)
    db_session.delete(engineer)
    db_session.flush()

    with pytest.raises(HTTPException, match="Engineer not found") as exc_info:
        get_auth_context(_request(), db_session, primer_access=token)

    assert exc_info.value.status_code == 401


def test_get_auth_context_uses_current_engineer_role_and_team(db_session):
    old_team = Team(name="Old Team")
    new_team = Team(name="New Team")
    db_session.add_all([old_team, new_team])
    db_session.flush()

    engineer = Engineer(
        name="Role Change Engineer",
        email="role-change@example.com",
        api_key_hash="",
        team_id=old_team.id,
        role="engineer",
    )
    db_session.add(engineer)
    db_session.flush()

    token = create_access_token(engineer)

    engineer.role = "team_lead"
    engineer.team_id = new_team.id
    db_session.flush()

    auth = get_auth_context(_request(), db_session, primer_access=token)

    assert auth.engineer_id == engineer.id
    assert auth.role == "team_lead"
    assert auth.team_id == new_team.id


def test_get_auth_context_rejects_deactivated_engineer_for_valid_cookie(db_session):
    team = Team(name="Disabled JWT Team")
    db_session.add(team)
    db_session.flush()

    engineer = Engineer(
        name="Disabled Engineer",
        email="disabled@example.com",
        api_key_hash="",
        team_id=team.id,
        role="engineer",
    )
    db_session.add(engineer)
    db_session.flush()

    token = create_access_token(engineer)
    engineer.is_active = False
    db_session.flush()

    with pytest.raises(HTTPException, match="Account deactivated") as exc_info:
        get_auth_context(_request(), db_session, primer_access=token)

    assert exc_info.value.status_code == 403


def test_get_auth_context_uses_shared_api_key_verification(engineer_with_key, db_session):
    engineer, raw_key = engineer_with_key

    auth = get_auth_context(_request(), db_session, x_api_key=raw_key)

    assert auth.engineer_id == engineer.id
    assert auth.role == engineer.role
    assert auth.team_id == engineer.team_id
