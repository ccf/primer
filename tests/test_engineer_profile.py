import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt

from primer.common.models import (
    Engineer,
    GitRepository,
    ModelUsage,
    PullRequest,
    ReviewFinding,
    Session,
    SessionCommit,
    SessionFacets,
    SessionMessage,
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
        for ordinal in range(10):
            db_session.add(
                SessionMessage(
                    session_id=s1.id,
                    ordinal=ordinal,
                    role="human" if ordinal % 2 == 0 else "assistant",
                    content_text=f"message {ordinal}",
                )
            )
        db_session.add(ToolUsage(session_id=s1.id, tool_name="Read", call_count=4))
        db_session.add(
            ModelUsage(
                session_id=s1.id,
                model_name="claude-sonnet-4-5-20250929",
                input_tokens=2000,
                output_tokens=1000,
                cache_read_tokens=0,
                cache_creation_tokens=0,
            )
        )

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
        for ordinal in range(8):
            db_session.add(
                SessionMessage(
                    session_id=s2.id,
                    ordinal=ordinal,
                    role="human" if ordinal % 2 == 0 else "assistant",
                    content_text=f"message {ordinal}",
                )
            )
        db_session.add(ToolUsage(session_id=s2.id, tool_name="Read", call_count=2))
        db_session.add(
            ModelUsage(
                session_id=s2.id,
                model_name="claude-sonnet-4-5-20250929",
                input_tokens=1500,
                output_tokens=800,
                cache_read_tokens=0,
                cache_creation_tokens=0,
            )
        )
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
        assert "tool_rankings" in data
        assert isinstance(data["tool_rankings"], list)

    def test_profile_includes_effectiveness_score(
        self, client, db_session, engineer_with_key, admin_headers
    ):
        eng, _key = engineer_with_key
        now = datetime.now(UTC)
        team = db_session.query(Team).filter(Team.id == eng.team_id).one()
        peer, _peer_key = _make_engineer(db_session, team, name="Peer")

        repo = GitRepository(full_name=f"acme/{uuid.uuid4().hex[:8]}")
        db_session.add(repo)
        db_session.flush()

        session = _create_session(
            db_session,
            eng,
            started_at=now - timedelta(hours=1),
            project_name="effectiveness-proj",
        )
        db_session.add(
            SessionFacets(session_id=session.id, session_type="feature", outcome="success")
        )
        db_session.add(
            ModelUsage(
                session_id=session.id,
                model_name="claude-sonnet-4-5-20250929",
                input_tokens=1000,
                output_tokens=500,
                cache_read_tokens=0,
                cache_creation_tokens=0,
            )
        )
        pr = PullRequest(
            repository_id=repo.id,
            engineer_id=eng.id,
            github_pr_number=101,
            title="Ship effectiveness score",
            state="merged",
            review_comments_count=1,
            pr_created_at=now - timedelta(days=1),
            merged_at=now - timedelta(hours=2),
        )
        db_session.add(pr)
        db_session.flush()
        db_session.add(
            SessionCommit(
                session_id=session.id,
                repository_id=repo.id,
                pull_request_id=pr.id,
                commit_sha=uuid.uuid4().hex[:12],
                commit_message="feat: ship score",
                committed_at=now - timedelta(hours=1),
                files_changed=3,
                lines_added=42,
                lines_deleted=7,
            )
        )
        db_session.add(
            ReviewFinding(
                pull_request_id=pr.id,
                source="bugbot",
                external_id=f"finding-{uuid.uuid4().hex[:8]}",
                severity="medium",
                title="Null guard",
                status="fixed",
                detected_at=now - timedelta(hours=6),
                resolved_at=now - timedelta(hours=3),
            )
        )

        peer_session = _create_session(
            db_session,
            peer,
            started_at=now - timedelta(hours=2),
            project_name="peer-proj",
        )
        db_session.add(
            SessionFacets(session_id=peer_session.id, session_type="feature", outcome="success")
        )
        db_session.add(
            ModelUsage(
                session_id=peer_session.id,
                model_name="claude-sonnet-4-5-20250929",
                input_tokens=8000,
                output_tokens=4000,
                cache_read_tokens=0,
                cache_creation_tokens=0,
            )
        )
        db_session.flush()

        response = client.get(
            f"/api/v1/analytics/engineers/{eng.id}/profile",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["effectiveness"]["score"] is not None
        assert data["effectiveness"]["breakdown"]["success_rate"] == 1.0
        assert data["effectiveness"]["breakdown"]["quality_outcomes"] == 1.0
        assert data["effectiveness"]["breakdown"]["follow_through"] == 1.0
        assert data["effectiveness"]["breakdown"]["cost_efficiency"] is not None

    def test_profile_includes_workflow_playbooks_from_peer_patterns(
        self, client, db_session, engineer_with_key, admin_headers
    ):
        eng, _key = engineer_with_key
        now = datetime.now(UTC)
        team = db_session.query(Team).filter(Team.id == eng.team_id).one()
        peer_one, _peer_key = _make_engineer(db_session, team, name="Peer One")
        peer_two, _peer_key_two = _make_engineer(db_session, team, name="Peer Two")

        target_session = _create_session(
            db_session,
            eng,
            started_at=now - timedelta(hours=1),
            project_name="primer",
        )
        db_session.add(
            SessionFacets(
                session_id=target_session.id,
                session_type="debugging",
                outcome="partial",
                friction_counts={"context_switching": 1},
            )
        )
        db_session.add(ToolUsage(session_id=target_session.id, tool_name="Read", call_count=2))

        for idx, peer in enumerate((peer_one, peer_two, peer_one), start=1):
            session = _create_session(
                db_session,
                peer,
                started_at=now - timedelta(hours=idx + 1),
                project_name="primer" if idx < 3 else "sdk",
                duration_seconds=1800 + (idx * 120),
            )
            db_session.add(
                SessionFacets(
                    session_id=session.id,
                    session_type="implementation",
                    outcome="success",
                    friction_counts=({"context_switching": 1} if idx == 3 else {}),
                )
            )
            db_session.add(ToolUsage(session_id=session.id, tool_name="Grep", call_count=2))
            db_session.add(ToolUsage(session_id=session.id, tool_name="Read", call_count=3))
            db_session.add(ToolUsage(session_id=session.id, tool_name="Edit", call_count=2))
            db_session.add(ToolUsage(session_id=session.id, tool_name="Bash", call_count=1))

        db_session.flush()

        response = client.get(
            f"/api/v1/analytics/engineers/{eng.id}/profile",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["workflow_playbooks"]) == 1
        playbook = data["workflow_playbooks"][0]
        assert playbook["scope"] == "team"
        assert playbook["adoption_state"] == "not_used"
        assert playbook["session_type"] == "implementation"
        assert playbook["steps"] == ["search", "read", "edit", "execute"]
        assert playbook["supporting_session_count"] == 3
        assert playbook["supporting_peer_count"] == 2
        assert playbook["success_rate"] == 1.0
        assert playbook["friction_free_rate"] == 0.667
        assert playbook["recommended_tools"][:3] == ["Read", "Grep", "Edit"]
        assert playbook["caution_friction_types"] == ["context_switching"]
        assert playbook["example_projects"] == ["primer", "sdk"]

    def test_profile_overview_treats_legacy_outcomes_as_canonical(
        self, client, db_session, engineer_with_key, admin_headers
    ):
        eng, _key = engineer_with_key
        now = datetime.now(UTC)

        success_session = _create_session(
            db_session,
            eng,
            started_at=now - timedelta(hours=2),
        )
        db_session.add(
            SessionFacets(
                session_id=success_session.id,
                session_type="feature",
                outcome="fully_achieved",
            )
        )

        failure_session = _create_session(
            db_session,
            eng,
            started_at=now - timedelta(hours=1),
        )
        db_session.add(
            SessionFacets(
                session_id=failure_session.id,
                session_type="debugging",
                outcome="failure",
            )
        )
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/engineers/{eng.id}/profile",
            headers=admin_headers,
        )
        assert r.status_code == 200
        overview = r.json()["overview"]

        assert overview["outcome_counts"]["success"] == 1
        assert overview["outcome_counts"]["failure"] == 1
        assert overview["success_rate"] == 0.5


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
        assert data["tool_rankings"] == []

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
