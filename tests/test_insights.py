import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt

from primer.common.models import (
    Engineer,
    ModelUsage,
    Session,
    SessionCustomization,
    SessionFacets,
    SessionWorkflowProfile,
    Team,
    ToolUsage,
)


def _create_session(db_session, engineer, **kwargs):
    sid = str(uuid.uuid4())
    session = Session(
        id=sid,
        engineer_id=engineer.id,
        message_count=10,
        user_message_count=5,
        assistant_message_count=5,
        tool_call_count=kwargs.pop("tool_call_count", 3),
        input_tokens=1000,
        output_tokens=500,
        duration_seconds=120.0,
        **kwargs,
    )
    db_session.add(session)
    db_session.flush()
    return session


# ---------------------------------------------------------------------------
# Config Optimization
# ---------------------------------------------------------------------------


class TestConfigOptimization:
    def test_empty_state(self, client, admin_headers):
        r = client.get("/api/v1/analytics/config-optimization", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["sessions_analyzed"] == 0
        assert data["suggestions"] == []

    def test_repeated_session_type_hook_suggestion(
        self, client, db_session, engineer_with_key, admin_headers
    ):
        eng, _key = engineer_with_key
        now = datetime.now(UTC)
        for i in range(6):
            s = _create_session(db_session, eng, started_at=now - timedelta(hours=i))
            db_session.add(
                SessionFacets(session_id=s.id, session_type="testing", outcome="success")
            )
        db_session.flush()

        r = client.get("/api/v1/analytics/config-optimization", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["sessions_analyzed"] == 6
        hook_suggestions = [s for s in data["suggestions"] if s["category"] == "hook"]
        assert len(hook_suggestions) >= 1
        assert "testing" in hook_suggestions[0]["title"]

    def test_conservative_permission_mode_suggestion(
        self, client, db_session, engineer_with_key, admin_headers
    ):
        eng, _key = engineer_with_key
        now = datetime.now(UTC)
        for i in range(4):
            _create_session(
                db_session,
                eng,
                started_at=now - timedelta(hours=i),
                permission_mode="default",
                tool_call_count=30,
            )
        db_session.flush()

        r = client.get("/api/v1/analytics/config-optimization", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        perm_suggestions = [s for s in data["suggestions"] if s["category"] == "permission"]
        assert len(perm_suggestions) >= 1

    def test_expensive_model_for_simple_tasks(
        self, client, db_session, engineer_with_key, admin_headers
    ):
        eng, _key = engineer_with_key
        now = datetime.now(UTC)
        for i in range(4):
            _create_session(
                db_session,
                eng,
                started_at=now - timedelta(hours=i),
                primary_model="claude-opus-4",
                tool_call_count=2,
            )
        db_session.flush()

        r = client.get("/api/v1/analytics/config-optimization", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        model_suggestions = [s for s in data["suggestions"] if s["category"] == "model"]
        assert len(model_suggestions) >= 1

    def test_requires_auth(self, client):
        r = client.get("/api/v1/analytics/config-optimization")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Personalized Tips
# ---------------------------------------------------------------------------


class TestPersonalizedTips:
    def test_empty_state(self, client, admin_headers):
        r = client.get("/api/v1/analytics/personalized-tips", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["sessions_analyzed"] == 0
        assert data["tips"] == []

    def test_tool_gap_tip(self, client, db_session, admin_headers):
        """Engineer missing tools that teammates use gets tool_gap tip."""
        import secrets

        import bcrypt

        from primer.common.models import Engineer, Team

        team = Team(name=f"Tips Team {uuid.uuid4().hex[:6]}")
        db_session.add(team)
        db_session.flush()

        # Create 3 engineers on same team
        engineers = []
        for i in range(3):
            raw_key = f"primer_{secrets.token_urlsafe(32)}"
            hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
            e = Engineer(
                name=f"Eng {i}",
                email=f"eng{i}_{uuid.uuid4().hex[:6]}@test.com",
                team_id=team.id,
                api_key_hash=hashed,
            )
            db_session.add(e)
            db_session.flush()
            engineers.append(e)

        now = datetime.now(UTC)
        # Engineer 0 and 1 use Grep, Engineer 2 does not
        for eng in engineers[:2]:
            s = _create_session(db_session, eng, started_at=now - timedelta(hours=1))
            db_session.add(ToolUsage(session_id=s.id, tool_name="Grep", call_count=5))
            db_session.add(ToolUsage(session_id=s.id, tool_name="Read", call_count=10))

        # Engineer 2 only uses Read
        s2 = _create_session(db_session, engineers[2], started_at=now - timedelta(hours=1))
        db_session.add(ToolUsage(session_id=s2.id, tool_name="Read", call_count=10))
        db_session.flush()

        # Query tips scoped to engineer 2's team
        r = client.get(
            f"/api/v1/analytics/personalized-tips?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        # Admin sees all team data but tips are generated for the whole scope

    def test_low_diversity_tip(self, client, db_session, engineer_with_key, admin_headers):
        eng, _key = engineer_with_key
        now = datetime.now(UTC)
        for i in range(4):
            s = _create_session(db_session, eng, started_at=now - timedelta(hours=i))
            db_session.add(ToolUsage(session_id=s.id, tool_name="Read", call_count=10))
        db_session.flush()

        r = client.get("/api/v1/analytics/personalized-tips", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        diversity_tips = [t for t in data["tips"] if t["category"] == "diversity"]
        # With only 1 tool across 4 sessions, should trigger diversity tip
        assert len(diversity_tips) >= 1

    def test_requires_auth(self, client):
        r = client.get("/api/v1/analytics/personalized-tips")
        assert r.status_code == 401

    def test_date_filtering(self, client, db_session, engineer_with_key, admin_headers):
        eng, _key = engineer_with_key
        old_date = datetime(2024, 1, 1, tzinfo=UTC)
        s = _create_session(db_session, eng, started_at=old_date)
        db_session.add(ToolUsage(session_id=s.id, tool_name="Read", call_count=5))
        db_session.flush()

        r = client.get(
            "/api/v1/analytics/personalized-tips?start_date=2025-01-01T00:00:00",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["sessions_analyzed"] == 0


# ---------------------------------------------------------------------------
# Skill Inventory
# ---------------------------------------------------------------------------


class TestSkillInventory:
    def test_empty_state(self, client, admin_headers):
        r = client.get("/api/v1/analytics/skill-inventory", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total_engineers"] == 0
        assert data["total_session_types"] == 0
        assert data["total_tools_used"] == 0
        assert data["engineer_profiles"] == []
        assert data["team_skill_gaps"] == []
        assert data["reusable_assets"] == []
        assert data["underused_reusable_assets"] == []

    def test_profiles_with_varied_sessions(
        self, client, db_session, engineer_with_key, admin_headers
    ):
        eng, _key = engineer_with_key
        now = datetime.now(UTC)

        # Session with debugging type
        s1 = _create_session(db_session, eng, started_at=now - timedelta(hours=3))
        db_session.add(SessionFacets(session_id=s1.id, session_type="debugging", outcome="success"))
        db_session.add(ToolUsage(session_id=s1.id, tool_name="Read", call_count=30))
        db_session.add(ToolUsage(session_id=s1.id, tool_name="Bash", call_count=25))

        # Session with feature type
        s2 = _create_session(
            db_session, eng, started_at=now - timedelta(hours=2), project_name="project-a"
        )
        db_session.add(SessionFacets(session_id=s2.id, session_type="feature", outcome="success"))
        db_session.add(ToolUsage(session_id=s2.id, tool_name="Read", call_count=25))
        db_session.add(ToolUsage(session_id=s2.id, tool_name="Write", call_count=3))

        db_session.flush()

        r = client.get("/api/v1/analytics/skill-inventory", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total_engineers"] == 1
        assert data["total_session_types"] == 2
        assert data["total_tools_used"] >= 2

        profile = data["engineer_profiles"][0]
        assert profile["name"] == "Test Engineer"
        assert profile["total_sessions"] == 2
        assert profile["session_types"]["debugging"] == 1
        assert profile["session_types"]["feature"] == 1
        assert profile["diversity_score"] > 0  # entropy > 0 with 2 types

    def test_skill_gaps_below_threshold(self, client, db_session, admin_headers):
        """Skills used by <30% of engineers are flagged as gaps."""
        import secrets

        import bcrypt

        from primer.common.models import Engineer, Team

        team = Team(name=f"Skill Team {uuid.uuid4().hex[:6]}")
        db_session.add(team)
        db_session.flush()

        now = datetime.now(UTC)
        engineers = []
        for i in range(5):
            raw_key = f"primer_{secrets.token_urlsafe(32)}"
            hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
            e = Engineer(
                name=f"SkillEng {i}",
                email=f"skilleng{i}_{uuid.uuid4().hex[:6]}@test.com",
                team_id=team.id,
                api_key_hash=hashed,
            )
            db_session.add(e)
            db_session.flush()
            engineers.append(e)

        # All 5 engineers use Read
        for eng in engineers:
            s = _create_session(db_session, eng, started_at=now - timedelta(hours=1))
            db_session.add(ToolUsage(session_id=s.id, tool_name="Read", call_count=10))

        # Only 1 engineer uses RareTool (20% coverage -> gap)
        s_rare = _create_session(db_session, engineers[0], started_at=now - timedelta(hours=2))
        db_session.add(ToolUsage(session_id=s_rare.id, tool_name="RareTool", call_count=5))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/skill-inventory?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        gap_skills = [g["skill"] for g in data["team_skill_gaps"]]
        assert "RareTool" in gap_skills
        assert "Read" not in gap_skills

    def test_tool_proficiency_levels(self, client, db_session, engineer_with_key, admin_headers):
        eng, _key = engineer_with_key
        now = datetime.now(UTC)

        s = _create_session(db_session, eng, started_at=now - timedelta(hours=1))
        db_session.add(ToolUsage(session_id=s.id, tool_name="Read", call_count=60))
        db_session.add(ToolUsage(session_id=s.id, tool_name="Write", call_count=25))
        db_session.add(ToolUsage(session_id=s.id, tool_name="Grep", call_count=10))
        db_session.add(ToolUsage(session_id=s.id, tool_name="Bash", call_count=2))
        db_session.flush()

        r = client.get("/api/v1/analytics/skill-inventory", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()

        profile = data["engineer_profiles"][0]
        assert profile["tool_proficiency"]["Read"] == "expert"
        assert profile["tool_proficiency"]["Write"] == "proficient"
        assert profile["tool_proficiency"]["Grep"] == "moderate"
        assert profile["tool_proficiency"]["Bash"] == "novice"

    def test_reuse_analytics_tracks_reusable_assets_by_workflow_and_outcome(
        self, client, db_session, admin_headers
    ):
        team = Team(name=f"Reuse Team {uuid.uuid4().hex[:6]}")
        db_session.add(team)
        db_session.flush()

        engineers = []
        for i in range(2):
            raw_key = f"primer_{secrets.token_urlsafe(32)}"
            hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
            engineer = Engineer(
                name=f"Reuse Eng {i}",
                email=f"reuse{i}_{uuid.uuid4().hex[:6]}@test.com",
                team_id=team.id,
                api_key_hash=hashed,
            )
            db_session.add(engineer)
            db_session.flush()
            engineers.append(engineer)

        now = datetime.now(UTC)
        s1 = _create_session(
            db_session,
            engineers[0],
            started_at=now - timedelta(hours=3),
            project_name="primer",
        )
        s2 = _create_session(
            db_session,
            engineers[1],
            started_at=now - timedelta(hours=2),
            project_name="primer",
        )
        s3 = _create_session(
            db_session,
            engineers[0],
            started_at=now - timedelta(hours=1),
            project_name="sdk",
        )

        db_session.add_all(
            [
                SessionFacets(session_id=s1.id, session_type="debugging", outcome="success"),
                SessionFacets(session_id=s2.id, session_type="debugging", outcome="success"),
                SessionFacets(session_id=s3.id, session_type="feature", outcome="success"),
                SessionWorkflowProfile(session_id=s1.id, archetype="debugging"),
                SessionWorkflowProfile(session_id=s2.id, archetype="debugging"),
                SessionWorkflowProfile(session_id=s3.id, archetype="feature_delivery"),
                ModelUsage(
                    session_id=s1.id,
                    model_name="claude-sonnet-4-5-20250929",
                    input_tokens=1000,
                    output_tokens=500,
                    cache_read_tokens=0,
                    cache_creation_tokens=0,
                ),
                ModelUsage(
                    session_id=s2.id,
                    model_name="claude-sonnet-4-5-20250929",
                    input_tokens=1000,
                    output_tokens=500,
                    cache_read_tokens=0,
                    cache_creation_tokens=0,
                ),
                ModelUsage(
                    session_id=s3.id,
                    model_name="claude-haiku-4-5-20251001",
                    input_tokens=500,
                    output_tokens=200,
                    cache_read_tokens=0,
                    cache_creation_tokens=0,
                ),
                SessionCustomization(
                    session_id=s1.id,
                    customization_type="skill",
                    state="invoked",
                    identifier="review-pr",
                    provenance="repo_defined",
                    source_classification="custom",
                    invocation_count=3,
                ),
                SessionCustomization(
                    session_id=s2.id,
                    customization_type="skill",
                    state="invoked",
                    identifier="review-pr",
                    provenance="repo_defined",
                    source_classification="custom",
                    invocation_count=2,
                ),
                SessionCustomization(
                    session_id=s3.id,
                    customization_type="template",
                    state="invoked",
                    identifier="bugfix",
                    provenance="repo_defined",
                    source_classification="custom",
                    invocation_count=1,
                ),
            ]
        )
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/skill-inventory?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        assets = {asset["identifier"]: asset for asset in data["reusable_assets"]}
        review_pr = assets["review-pr"]
        assert review_pr["customization_type"] == "skill"
        assert review_pr["engineer_count"] == 2
        assert review_pr["session_count"] == 2
        assert review_pr["adoption_rate"] == 1.0
        assert review_pr["success_rate"] == 1.0
        assert review_pr["primary_workflow_archetype"] == "debugging"
        assert review_pr["workflow_archetypes"] == ["debugging"]
        assert review_pr["top_projects"] == ["primer"]
        assert review_pr["cost_per_successful_outcome"] is not None

        underused = {asset["identifier"]: asset for asset in data["underused_reusable_assets"]}
        bugfix = underused["bugfix"]
        assert bugfix["customization_type"] == "template"
        assert bugfix["engineer_count"] == 1
        assert bugfix["adoption_rate"] == 0.5
        assert bugfix["success_rate"] == 1.0
        assert bugfix["workflow_archetypes"] == ["feature_delivery"]

    def test_requires_auth(self, client):
        r = client.get("/api/v1/analytics/skill-inventory")
        assert r.status_code == 401
