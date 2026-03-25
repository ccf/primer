import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt

from primer.common.models import Engineer, ModelUsage, SessionFacets, SessionWorkflowProfile, Team
from primer.common.models import Session as SessionModel


def _make_engineer(db_session, team, *, name, role="engineer"):
    raw_key = f"primer_{secrets.token_urlsafe(32)}"
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    engineer = Engineer(
        name=name,
        email=f"{name.lower().replace(' ', '.')}@example.com",
        team_id=team.id,
        api_key_hash=hashed,
        role=role,
    )
    db_session.add(engineer)
    db_session.flush()
    return engineer, raw_key


def _create_session(
    db_session,
    engineer,
    *,
    project_name: str,
    started_at: datetime,
    archetype: str,
    outcome: str,
    input_tokens: int = 1000,
    output_tokens: int = 500,
):
    session = SessionModel(
        id=str(uuid.uuid4()),
        engineer_id=engineer.id,
        project_name=project_name,
        started_at=started_at,
        duration_seconds=300,
        message_count=4,
        user_message_count=2,
        assistant_message_count=2,
        tool_call_count=2,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        primary_model="claude-sonnet-4-5-20250929",
    )
    db_session.add(session)
    db_session.flush()
    db_session.add(SessionFacets(session_id=session.id, session_type=archetype, outcome=outcome))
    db_session.add(SessionWorkflowProfile(session_id=session.id, archetype=archetype))
    db_session.add(
        ModelUsage(
            session_id=session.id,
            model_name="claude-sonnet-4-5-20250929",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=0,
            cache_creation_tokens=0,
        )
    )
    db_session.flush()
    return session


def test_compare_mode_team(client, db_session, admin_headers):
    team_a = Team(name="Alpha")
    team_b = Team(name="Beta")
    db_session.add_all([team_a, team_b])
    db_session.flush()
    eng_a, _eng_a_key = _make_engineer(db_session, team_a, name="Alice")
    eng_b, _eng_b_key = _make_engineer(db_session, team_b, name="Bob")
    now = datetime.now(UTC)

    _create_session(
        db_session,
        eng_a,
        project_name="alpha-app",
        started_at=now - timedelta(days=1),
        archetype="debugging",
        outcome="success",
    )
    _create_session(
        db_session,
        eng_a,
        project_name="alpha-app",
        started_at=now - timedelta(days=2),
        archetype="debugging",
        outcome="success",
    )
    _create_session(
        db_session,
        eng_b,
        project_name="beta-app",
        started_at=now - timedelta(days=1),
        archetype="implementation",
        outcome="failure",
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/analytics/compare?mode=team&left_key={team_a.id}&right_key={team_b.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "team"
    assert data["left"]["label"] == "Alpha"
    assert data["right"]["label"] == "Beta"
    assert data["left"]["total_sessions"] == 2
    assert data["right"]["total_sessions"] == 1
    assert data["left"]["top_workflows"][0]["label"] == "debugging"


def test_compare_mode_engineer(client, db_session, admin_headers):
    team = Team(name="Compare Engineers")
    db_session.add(team)
    db_session.flush()
    eng_a, _eng_a_key = _make_engineer(db_session, team, name="Alice")
    eng_b, _eng_b_key = _make_engineer(db_session, team, name="Bob")
    now = datetime.now(UTC)

    _create_session(
        db_session,
        eng_a,
        project_name="primer",
        started_at=now - timedelta(days=1),
        archetype="debugging",
        outcome="success",
    )
    _create_session(
        db_session,
        eng_b,
        project_name="primer",
        started_at=now - timedelta(days=1),
        archetype="implementation",
        outcome="failure",
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/analytics/compare?mode=engineer&left_key={eng_a.id}&right_key={eng_b.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["left"]["label"] == "Alice"
    assert data["right"]["label"] == "Bob"
    assert data["left"]["total_sessions"] == 1
    assert data["right"]["total_sessions"] == 1


def test_compare_mode_project(client, db_session, admin_headers):
    team = Team(name="Project Compare")
    db_session.add(team)
    db_session.flush()
    engineer, _engineer_key = _make_engineer(db_session, team, name="Alice")
    now = datetime.now(UTC)

    _create_session(
        db_session,
        engineer,
        project_name="alpha-app",
        started_at=now - timedelta(days=1),
        archetype="debugging",
        outcome="success",
    )
    _create_session(
        db_session,
        engineer,
        project_name="beta-app",
        started_at=now - timedelta(days=1),
        archetype="implementation",
        outcome="success",
    )
    db_session.commit()

    response = client.get(
        "/api/v1/analytics/compare"
        "?mode=project&left_key=alpha-app&right_key=beta-app"
        f"&team_id={team.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["left"]["label"] == "alpha-app"
    assert data["right"]["label"] == "beta-app"
    assert data["left"]["top_workflows"][0]["label"]
    assert data["right"]["top_workflows"][0]["label"]


def test_compare_mode_period(client, db_session, admin_headers):
    team = Team(name="Period Compare")
    db_session.add(team)
    db_session.flush()
    engineer, _engineer_key = _make_engineer(db_session, team, name="Alice")
    now = datetime.now(UTC)
    current_start = now - timedelta(days=7)
    previous_start = current_start - timedelta(days=7)

    _create_session(
        db_session,
        engineer,
        project_name="primer",
        started_at=previous_start + timedelta(days=1),
        archetype="debugging",
        outcome="failure",
    )
    _create_session(
        db_session,
        engineer,
        project_name="primer",
        started_at=current_start,
        archetype="debugging",
        outcome="success",
    )
    _create_session(
        db_session,
        engineer,
        project_name="primer",
        started_at=current_start + timedelta(days=1),
        archetype="debugging",
        outcome="success",
    )
    _create_session(
        db_session,
        engineer,
        project_name="primer",
        started_at=current_start + timedelta(days=2),
        archetype="implementation",
        outcome="success",
    )
    db_session.commit()

    response = client.get(
        "/api/v1/analytics/compare",
        params={
            "mode": "period",
            "team_id": team.id,
            "start_date": current_start.isoformat(),
            "end_date": now.isoformat(),
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["left"]["label"] == "Selected Period"
    assert data["right"]["label"] == "Previous Period"
    assert data["left"]["total_sessions"] == 3
    assert data["right"]["total_sessions"] == 1


def test_compare_mode_team_lead_rejects_unknown_engineer_ids(client, db_session):
    team = Team(name="Team Lead Compare")
    db_session.add(team)
    db_session.flush()
    _lead, lead_key = _make_engineer(db_session, team, name="Lead", role="team_lead")
    engineer, _engineer_key = _make_engineer(db_session, team, name="Alice")
    db_session.commit()

    response = client.get(
        "/api/v1/analytics/compare",
        params={
            "mode": "engineer",
            "left_key": engineer.id,
            "right_key": "missing-engineer-id",
        },
        headers={"x-api-key": lead_key},
    )
    assert response.status_code == 403


def test_parse_percentish_normalizes_numeric_percentages():
    from primer.server.services.compare_service import _parse_percentish

    assert _parse_percentish(80) == 0.8
    assert _parse_percentish(0.8) == 0.8
    assert _parse_percentish(1.01) is None
    assert _parse_percentish("80%") == 0.8
