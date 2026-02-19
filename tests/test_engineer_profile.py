import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt

from primer.common.models import (
    Engineer,
    Session,
    SessionFacets,
    Team,
    ToolUsage,
)


def _make_engineer(db_session, team, *, name="Eng", email=None, role="engineer"):
    """Create an engineer with a bcrypt-hashed API key, return (engineer, raw_key)."""
    raw_key = f"primer_{secrets.token_urlsafe(32)}"
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    eng = Engineer(
        name=name,
        email=email or f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@test.com",
        team_id=team.id,
        api_key_hash=hashed,
        role=role,
    )
    db_session.add(eng)
    db_session.flush()
    return eng, raw_key


def _create_session(db_session, engineer, **kwargs):
    """Create a minimal session with sensible defaults."""
    sid = kwargs.pop("session_id", str(uuid.uuid4()))
    session = Session(
        id=sid,
        engineer_id=engineer.id,
        message_count=kwargs.pop("message_count", 10),
        user_message_count=kwargs.pop("user_message_count", 5),
        assistant_message_count=kwargs.pop("assistant_message_count", 5),
        tool_call_count=kwargs.pop("tool_call_count", 3),
        input_tokens=kwargs.pop("input_tokens", 1000),
        output_tokens=kwargs.pop("output_tokens", 500),
        duration_seconds=kwargs.pop("duration_seconds", 120.0),
        primary_model=kwargs.pop("primary_model", "claude-sonnet-4-5-20250929"),
        **kwargs,
    )
    db_session.add(session)
    db_session.flush()
    return session


class TestEngineerProfileOverview:
    def test_profile_overview(self, client, db_session, engineer_with_key, admin_headers):
        """Create 1 engineer with 2 sessions, verify overview stats."""
        eng, _key = engineer_with_key
        now = datetime.now(UTC)

        s1 = _create_session(
            db_session,
            eng,
            started_at=now - timedelta(hours=2),
            message_count=10,
            tool_call_count=4,
            input_tokens=2000,
            output_tokens=1000,
            duration_seconds=300.0,
        )
        db_session.add(SessionFacets(session_id=s1.id, session_type="feature", outcome="success"))

        s2 = _create_session(
            db_session,
            eng,
            started_at=now - timedelta(hours=1),
            message_count=8,
            tool_call_count=2,
            input_tokens=1500,
            output_tokens=800,
            duration_seconds=200.0,
        )
        db_session.add(SessionFacets(session_id=s2.id, session_type="debugging", outcome="partial"))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/engineers/{eng.id}/profile",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["engineer_id"] == eng.id
        assert data["name"] == eng.name
        assert data["email"] == eng.email

        overview = data["overview"]
        assert overview["total_sessions"] == 2
        assert overview["total_messages"] == 18
        assert overview["total_tool_calls"] == 6
        assert overview["total_input_tokens"] == 3500
        assert overview["total_output_tokens"] == 1800
        assert overview["avg_session_duration"] is not None


class TestEngineerProfileWeeklyTrajectory:
    def test_profile_weekly_trajectory(self, client, db_session, engineer_with_key, admin_headers):
        """Create sessions in different ISO weeks, verify grouping."""
        eng, _key = engineer_with_key

        # Week 1: Monday 2026-02-02
        s1 = _create_session(
            db_session,
            eng,
            started_at=datetime(2026, 2, 2, 10, 0),
            duration_seconds=100.0,
        )
        db_session.add(SessionFacets(session_id=s1.id, session_type="feature", outcome="success"))
        db_session.add(ToolUsage(session_id=s1.id, tool_name="Read", call_count=5))

        # Week 2: Monday 2026-02-09
        s2 = _create_session(
            db_session,
            eng,
            started_at=datetime(2026, 2, 9, 10, 0),
            duration_seconds=200.0,
        )
        db_session.add(SessionFacets(session_id=s2.id, session_type="debugging", outcome="failure"))
        db_session.add(ToolUsage(session_id=s2.id, tool_name="Bash", call_count=3))

        s3 = _create_session(
            db_session,
            eng,
            started_at=datetime(2026, 2, 10, 10, 0),
            duration_seconds=150.0,
        )
        db_session.add(SessionFacets(session_id=s3.id, session_type="feature", outcome="success"))
        db_session.add(ToolUsage(session_id=s3.id, tool_name="Read", call_count=8))
        db_session.add(ToolUsage(session_id=s3.id, tool_name="Edit", call_count=2))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/engineers/{eng.id}/profile",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        trajectory = data["weekly_trajectory"]
        assert len(trajectory) == 2  # Two distinct ISO weeks

        # Each point should have the expected fields
        for point in trajectory:
            assert "week" in point
            assert "session_count" in point
            assert "tool_diversity" in point
            assert "estimated_cost" in point

        # Week 2 should have 2 sessions
        week2 = [p for p in trajectory if p["session_count"] == 2]
        assert len(week2) == 1
        # Week 2 has Read, Bash, Edit -> 3 tools
        assert week2[0]["tool_diversity"] >= 2


class TestEngineerProfileFriction:
    def test_profile_friction_breakdown(self, client, db_session, engineer_with_key, admin_headers):
        """Create session with friction_counts, verify friction reports."""
        eng, _key = engineer_with_key
        now = datetime.now(UTC)

        s1 = _create_session(db_session, eng, started_at=now - timedelta(hours=1))
        s1.has_facets = True
        db_session.add(
            SessionFacets(
                session_id=s1.id,
                session_type="feature",
                outcome="partial",
                friction_counts={"tool_error": 3, "permission_denied": 1},
                friction_detail="Tool crashed on large file",
            )
        )

        s2 = _create_session(db_session, eng, started_at=now - timedelta(hours=2))
        s2.has_facets = True
        db_session.add(
            SessionFacets(
                session_id=s2.id,
                session_type="debugging",
                outcome="success",
                friction_counts={"tool_error": 2},
                friction_detail="Timeout in edit",
            )
        )
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/engineers/{eng.id}/profile",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        friction = data["friction"]
        assert len(friction) >= 1

        tool_error = next((f for f in friction if f["friction_type"] == "tool_error"), None)
        assert tool_error is not None
        assert tool_error["count"] == 5
        assert len(tool_error["details"]) >= 1


class TestEngineerProfileAuth:
    def test_profile_auth_own(self, client, db_session, engineer_with_key):
        """Engineer can access own profile."""
        eng, raw_key = engineer_with_key

        # Create at least one session so profile has data
        now = datetime.now(UTC)
        _create_session(db_session, eng, started_at=now - timedelta(hours=1))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/engineers/{eng.id}/profile",
            headers={"x-api-key": raw_key},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["engineer_id"] == eng.id

    def test_profile_auth_other_forbidden(self, client, db_session, engineer_with_key):
        """Engineer cannot access another engineer's profile (403)."""
        eng, raw_key = engineer_with_key

        team = db_session.query(Team).filter(Team.id == eng.team_id).first()
        other_eng, _other_key = _make_engineer(db_session, team, name="Other Eng")

        r = client.get(
            f"/api/v1/analytics/engineers/{other_eng.id}/profile",
            headers={"x-api-key": raw_key},
        )
        assert r.status_code == 403

    def test_profile_auth_team_lead(self, client, db_session):
        """Team lead can view team member's profile."""
        team = Team(name=f"Lead Team {uuid.uuid4().hex[:6]}")
        db_session.add(team)
        db_session.flush()

        _lead, lead_key = _make_engineer(db_session, team, name="Team Lead", role="team_lead")
        member, _member_key = _make_engineer(db_session, team, name="Team Member")

        # Create a session for the member so profile has data
        now = datetime.now(UTC)
        _create_session(db_session, member, started_at=now - timedelta(hours=1))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/engineers/{member.id}/profile",
            headers={"x-api-key": lead_key},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["engineer_id"] == member.id


class TestEngineerProfileEmpty:
    def test_profile_empty(self, client, db_session, engineer_with_key, admin_headers):
        """Engineer with no sessions returns zeros."""
        eng, _key = engineer_with_key

        r = client.get(
            f"/api/v1/analytics/engineers/{eng.id}/profile",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        overview = data["overview"]
        assert overview["total_sessions"] == 0
        assert overview["total_messages"] == 0
        assert overview["total_tool_calls"] == 0
        assert overview["total_input_tokens"] == 0
        assert overview["total_output_tokens"] == 0
        assert data["weekly_trajectory"] == []
        assert data["friction"] == []

    def test_profile_leverage_score_and_projects(
        self, client, db_session, engineer_with_key, admin_headers
    ):
        """Profile includes leverage_score and projects fields."""
        eng, _key = engineer_with_key
        now = datetime.now(UTC)

        _create_session(
            db_session,
            eng,
            started_at=now - timedelta(hours=1),
            project_name="my-project",
        )
        _create_session(
            db_session,
            eng,
            started_at=now - timedelta(hours=2),
            project_name="other-project",
        )
        _create_session(
            db_session,
            eng,
            started_at=now - timedelta(hours=3),
            project_name="my-project",
        )
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/engineers/{eng.id}/profile",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert "leverage_score" in data
        assert "projects" in data
        assert isinstance(data["projects"], list)
        assert set(data["projects"]) == {"my-project", "other-project"}
