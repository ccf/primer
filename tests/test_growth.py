import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt

from primer.common.models import Engineer, Session, SessionFacets, Team, ToolUsage


def _create_session(db_session, engineer, **kwargs):
    sid = str(uuid.uuid4())
    session = Session(
        id=sid,
        engineer_id=engineer.id,
        message_count=kwargs.pop("message_count", 10),
        user_message_count=5,
        assistant_message_count=5,
        tool_call_count=kwargs.pop("tool_call_count", 3),
        input_tokens=1000,
        output_tokens=500,
        duration_seconds=kwargs.pop("duration_seconds", 120.0),
        **kwargs,
    )
    db_session.add(session)
    db_session.flush()
    return session


def _create_team_engineers(db_session, count, team_name=None):
    """Create a team with N engineers. Returns (team, list[engineer])."""
    team = Team(name=team_name or f"Growth Team {uuid.uuid4().hex[:6]}")
    db_session.add(team)
    db_session.flush()

    engineers = []
    for i in range(count):
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
    return team, engineers


# ---------------------------------------------------------------------------
# Learning Paths
# ---------------------------------------------------------------------------


class TestLearningPaths:
    def test_empty_state(self, client, admin_headers):
        r = client.get("/api/v1/analytics/learning-paths", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["sessions_analyzed"] == 0
        assert data["engineer_paths"] == []
        assert data["team_skill_universe"] == {}

    def test_session_type_gap_detected(self, client, db_session, admin_headers):
        """Engineer missing session types used by >=50% of team gets recommendation."""
        team, engineers = _create_team_engineers(db_session, 3)
        now = datetime.now(UTC)

        # Eng 0 and 1 do "debugging" sessions, Eng 2 does not
        for eng in engineers[:2]:
            s = _create_session(db_session, eng, started_at=now - timedelta(hours=1))
            db_session.add(
                SessionFacets(session_id=s.id, session_type="debugging", outcome="success")
            )
            db_session.add(ToolUsage(session_id=s.id, tool_name="Read", call_count=5))

        # Eng 2 only does "feature"
        s2 = _create_session(db_session, engineers[2], started_at=now - timedelta(hours=1))
        db_session.add(SessionFacets(session_id=s2.id, session_type="feature", outcome="success"))
        db_session.add(ToolUsage(session_id=s2.id, tool_name="Read", call_count=5))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/learning-paths?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["sessions_analyzed"] == 3

        # Eng 2 should have a session_type_gap recommendation for "debugging"
        eng2_path = next(p for p in data["engineer_paths"] if p["engineer_id"] == engineers[2].id)
        gap_recs = [r for r in eng2_path["recommendations"] if r["category"] == "session_type_gap"]
        assert len(gap_recs) >= 1
        assert any("debugging" in r["skill_area"] for r in gap_recs)

    def test_tool_gap_detected(self, client, db_session, admin_headers):
        """Engineer missing tools used by >=40% of team gets tool_gap recommendation."""
        team, engineers = _create_team_engineers(db_session, 3)
        now = datetime.now(UTC)

        # Eng 0 and 1 use Grep, Eng 2 does not
        for eng in engineers[:2]:
            s = _create_session(db_session, eng, started_at=now - timedelta(hours=1))
            db_session.add(ToolUsage(session_id=s.id, tool_name="Grep", call_count=10))
            db_session.add(ToolUsage(session_id=s.id, tool_name="Read", call_count=10))

        s2 = _create_session(db_session, engineers[2], started_at=now - timedelta(hours=1))
        db_session.add(ToolUsage(session_id=s2.id, tool_name="Read", call_count=10))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/learning-paths?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        eng2_path = next(p for p in data["engineer_paths"] if p["engineer_id"] == engineers[2].id)
        tool_recs = [r for r in eng2_path["recommendations"] if r["category"] == "tool_gap"]
        assert len(tool_recs) >= 1
        assert any("Grep" in r["skill_area"] for r in tool_recs)

    def test_complexity_trend_increasing(self, client, db_session, admin_headers):
        """Rising tool_call_count + message_count over time → increasing trend."""
        team, engineers = _create_team_engineers(db_session, 1)
        eng = engineers[0]
        now = datetime.now(UTC)

        # First 5 sessions: low complexity
        for i in range(5):
            _create_session(
                db_session,
                eng,
                started_at=now - timedelta(days=20 - i),
                tool_call_count=3,
                message_count=5,
            )

        # Recent 5 sessions: high complexity
        for i in range(5):
            _create_session(
                db_session,
                eng,
                started_at=now - timedelta(days=5 - i),
                tool_call_count=20,
                message_count=30,
            )
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/learning-paths?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        path = data["engineer_paths"][0]
        assert path["complexity_trend"] == "increasing"

    def test_coverage_score(self, client, db_session, admin_headers):
        """Engineer with fewer skills has lower coverage score."""
        team, engineers = _create_team_engineers(db_session, 2)
        now = datetime.now(UTC)

        # Eng 0: uses 3 tools, 2 session types
        s1 = _create_session(db_session, engineers[0], started_at=now - timedelta(hours=2))
        db_session.add(SessionFacets(session_id=s1.id, session_type="debugging"))
        db_session.add(ToolUsage(session_id=s1.id, tool_name="Read", call_count=5))
        db_session.add(ToolUsage(session_id=s1.id, tool_name="Grep", call_count=5))
        db_session.add(ToolUsage(session_id=s1.id, tool_name="Bash", call_count=5))
        s1b = _create_session(db_session, engineers[0], started_at=now - timedelta(hours=1))
        db_session.add(SessionFacets(session_id=s1b.id, session_type="feature"))

        # Eng 1: uses 1 tool, 1 session type
        s2 = _create_session(db_session, engineers[1], started_at=now - timedelta(hours=1))
        db_session.add(SessionFacets(session_id=s2.id, session_type="debugging"))
        db_session.add(ToolUsage(session_id=s2.id, tool_name="Read", call_count=5))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/learning-paths?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        eng0_path = next(p for p in data["engineer_paths"] if p["engineer_id"] == engineers[0].id)
        eng1_path = next(p for p in data["engineer_paths"] if p["engineer_id"] == engineers[1].id)
        assert eng0_path["coverage_score"] > eng1_path["coverage_score"]

    def test_requires_auth(self, client):
        r = client.get("/api/v1/analytics/learning-paths")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Pattern Sharing
# ---------------------------------------------------------------------------


class TestPatternSharing:
    def test_empty_state(self, client, admin_headers):
        r = client.get("/api/v1/analytics/pattern-sharing", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["sessions_analyzed"] == 0
        assert data["patterns"] == []
        assert data["total_clusters_found"] == 0

    def test_session_type_project_cluster(self, client, db_session, admin_headers):
        """3 engineers working on same session_type+project creates a cluster."""
        team, engineers = _create_team_engineers(db_session, 3)
        now = datetime.now(UTC)

        for eng in engineers:
            s = _create_session(
                db_session,
                eng,
                started_at=now - timedelta(hours=1),
                project_name="my-project",
                duration_seconds=60.0,
            )
            db_session.add(
                SessionFacets(session_id=s.id, session_type="debugging", outcome="success")
            )
            db_session.add(ToolUsage(session_id=s.id, tool_name="Read", call_count=5))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/pattern-sharing?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total_clusters_found"] >= 1

        cluster = data["patterns"][0]
        assert cluster["engineer_count"] == 3
        assert cluster["session_count"] == 3

    def test_best_approach_selects_fastest_successful(self, client, db_session, admin_headers):
        """Best approach = successful session with shortest duration."""
        team, engineers = _create_team_engineers(db_session, 2)
        now = datetime.now(UTC)

        # Eng 0: success, 200s
        s0 = _create_session(
            db_session,
            engineers[0],
            started_at=now - timedelta(hours=2),
            project_name="proj",
            duration_seconds=200.0,
        )
        db_session.add(SessionFacets(session_id=s0.id, session_type="feature", outcome="success"))

        # Eng 1: success, 60s (should be best)
        s1 = _create_session(
            db_session,
            engineers[1],
            started_at=now - timedelta(hours=1),
            project_name="proj",
            duration_seconds=60.0,
        )
        db_session.add(SessionFacets(session_id=s1.id, session_type="feature", outcome="success"))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/pattern-sharing?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        # Find the session_type cluster
        type_clusters = [p for p in data["patterns"] if p["cluster_type"] == "session_type"]
        assert len(type_clusters) >= 1
        best = type_clusters[0]["best_approach"]
        assert best is not None
        assert best["engineer_id"] == engineers[1].id

    def test_single_engineer_no_cluster(self, client, db_session, admin_headers):
        """A single engineer working alone doesn't create clusters."""
        team, engineers = _create_team_engineers(db_session, 1)
        now = datetime.now(UTC)

        s = _create_session(
            db_session,
            engineers[0],
            started_at=now - timedelta(hours=1),
            project_name="solo-proj",
        )
        db_session.add(SessionFacets(session_id=s.id, session_type="debugging", outcome="success"))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/pattern-sharing?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total_clusters_found"] == 0

    def test_requires_auth(self, client):
        r = client.get("/api/v1/analytics/pattern-sharing")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Onboarding Acceleration
# ---------------------------------------------------------------------------


class TestOnboardingAcceleration:
    def test_empty_state(self, client, admin_headers):
        r = client.get("/api/v1/analytics/onboarding-acceleration", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["sessions_analyzed"] == 0
        assert data["cohorts"] == []
        assert data["new_hire_progress"] == []
        assert data["experienced_benchmark"] is None

    def test_cohort_segmentation(self, client, db_session, admin_headers):
        """Engineers segmented by first session date into new_hire/ramping/experienced."""
        team, engineers = _create_team_engineers(db_session, 3)
        now = datetime.now(UTC)

        # Eng 0: first session 5 days ago → new_hire
        _create_session(
            db_session,
            engineers[0],
            started_at=now - timedelta(days=5),
        )
        # Eng 1: first session 60 days ago → ramping
        _create_session(
            db_session,
            engineers[1],
            started_at=now - timedelta(days=60),
        )
        # Eng 2: first session 120 days ago → experienced
        _create_session(
            db_session,
            engineers[2],
            started_at=now - timedelta(days=120),
        )
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/onboarding-acceleration?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        cohort_labels = {c["cohort_label"] for c in data["cohorts"]}
        assert "new_hire" in cohort_labels
        assert "ramping" in cohort_labels
        assert "experienced" in cohort_labels

    def test_new_hire_velocity_with_lagging(self, client, db_session, admin_headers):
        """New hire with limited skills has velocity < 100 and lagging areas."""
        team, engineers = _create_team_engineers(db_session, 2)
        now = datetime.now(UTC)

        # Experienced engineer (120 days ago, diverse tools)
        for i in range(5):
            s = _create_session(
                db_session,
                engineers[0],
                started_at=now - timedelta(days=120 - i),
                duration_seconds=60.0,
            )
            db_session.add(SessionFacets(session_id=s.id, outcome="success"))
            db_session.add(ToolUsage(session_id=s.id, tool_name="Read", call_count=10))
            db_session.add(ToolUsage(session_id=s.id, tool_name="Grep", call_count=5))
            db_session.add(ToolUsage(session_id=s.id, tool_name="Bash", call_count=3))
            db_session.add(ToolUsage(session_id=s.id, tool_name="Write", call_count=2))

        # New hire (5 days ago, limited)
        s_new = _create_session(
            db_session,
            engineers[1],
            started_at=now - timedelta(days=5),
            duration_seconds=300.0,
        )
        db_session.add(SessionFacets(session_id=s_new.id, outcome="failure"))
        db_session.add(ToolUsage(session_id=s_new.id, tool_name="Read", call_count=2))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/onboarding-acceleration?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert len(data["new_hire_progress"]) == 1
        nhp = data["new_hire_progress"][0]
        assert nhp["velocity_score"] < 100
        assert nhp["engineer_id"] == engineers[1].id

    def test_friction_recommendation(self, client, db_session, admin_headers):
        """High new hire friction vs experienced triggers friction recommendation."""
        team, engineers = _create_team_engineers(db_session, 2)
        now = datetime.now(UTC)

        # Experienced: low friction
        for i in range(3):
            s = _create_session(
                db_session,
                engineers[0],
                started_at=now - timedelta(days=120 - i),
            )
            db_session.add(
                SessionFacets(session_id=s.id, outcome="success", friction_counts={"minor": 1})
            )

        # New hire: high friction
        for i in range(3):
            s = _create_session(
                db_session,
                engineers[1],
                started_at=now - timedelta(days=5 - i),
            )
            db_session.add(
                SessionFacets(
                    session_id=s.id,
                    outcome="failure",
                    friction_counts={"permission_denied": 5, "timeout": 3},
                )
            )
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/onboarding-acceleration?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        friction_recs = [r for r in data["recommendations"] if r["category"] == "friction"]
        assert len(friction_recs) >= 1

    def test_all_new_hires_no_crash(self, client, db_session, admin_headers):
        """When all engineers are new hires, experienced_benchmark is None and no crash."""
        team, engineers = _create_team_engineers(db_session, 2)
        now = datetime.now(UTC)

        for eng in engineers:
            s = _create_session(
                db_session,
                eng,
                started_at=now - timedelta(days=5),
            )
            db_session.add(SessionFacets(session_id=s.id, outcome="success"))
        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/onboarding-acceleration?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["experienced_benchmark"] is None
        assert len(data["cohorts"]) >= 1

    def test_requires_auth(self, client):
        r = client.get("/api/v1/analytics/onboarding-acceleration")
        assert r.status_code == 401
