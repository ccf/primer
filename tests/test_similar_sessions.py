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
        has_facets=kwargs.pop("has_facets", False),
        **kwargs,
    )
    db_session.add(session)
    db_session.flush()
    return session


class TestSimilarSessions:
    def _setup_team_and_engineers(self, db_session, n=2):
        """Create a team with n engineers, return (team, [(eng, key), ...])."""
        team = Team(name=f"Sim Team {uuid.uuid4().hex[:6]}")
        db_session.add(team)
        db_session.flush()

        pairs = []
        for i in range(n):
            eng, key = _make_engineer(db_session, team, name=f"SimEng {i}")
            pairs.append((eng, key))
        return team, pairs

    def test_similar_same_type_project(self, client, db_session, admin_headers):
        """Two sessions with same type + project are found as similar."""
        _team, pairs = self._setup_team_and_engineers(db_session, n=2)
        eng1, _ = pairs[0]
        eng2, _ = pairs[1]
        now = datetime.now(UTC)

        # Target session
        target = _create_session(
            db_session,
            eng1,
            started_at=now - timedelta(hours=3),
            project_name="acme-api",
            has_facets=True,
        )
        db_session.add(
            SessionFacets(
                session_id=target.id,
                session_type="feature",
                outcome="success",
            )
        )

        # Candidate: same type + project, different engineer
        cand = _create_session(
            db_session,
            eng2,
            started_at=now - timedelta(hours=2),
            project_name="acme-api",
            has_facets=True,
        )
        db_session.add(
            SessionFacets(
                session_id=cand.id,
                session_type="feature",
                outcome="partial",
            )
        )
        db_session.add(ToolUsage(session_id=cand.id, tool_name="Read", call_count=5))
        db_session.flush()

        r = client.get(
            f"/api/v1/sessions/{target.id}/similar",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["total_found"] >= 1
        assert data["target_session_type"] == "feature"
        assert data["target_project"] == "acme-api"

        found_ids = [s["session_id"] for s in data["similar_sessions"]]
        assert cand.id in found_ids

        # Check the reason for the match
        match = next(s for s in data["similar_sessions"] if s["session_id"] == cand.id)
        assert match["similarity_reason"] == "same_type_and_project"

    def test_similar_same_type_only(self, client, db_session, admin_headers):
        """Match on session type alone (different project)."""
        _team, pairs = self._setup_team_and_engineers(db_session, n=2)
        eng1, _ = pairs[0]
        eng2, _ = pairs[1]
        now = datetime.now(UTC)

        target = _create_session(
            db_session,
            eng1,
            started_at=now - timedelta(hours=3),
            project_name="proj-alpha",
            has_facets=True,
        )
        db_session.add(
            SessionFacets(session_id=target.id, session_type="debugging", outcome="success")
        )

        cand = _create_session(
            db_session,
            eng2,
            started_at=now - timedelta(hours=2),
            project_name="proj-beta",
            has_facets=True,
        )
        db_session.add(
            SessionFacets(session_id=cand.id, session_type="debugging", outcome="success")
        )
        db_session.flush()

        r = client.get(
            f"/api/v1/sessions/{target.id}/similar",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["total_found"] >= 1
        found = next((s for s in data["similar_sessions"] if s["session_id"] == cand.id), None)
        assert found is not None
        assert found["similarity_reason"] == "same_type"

    def test_similar_same_goal(self, client, db_session, admin_headers):
        """Match on overlapping goal_categories."""
        _team, pairs = self._setup_team_and_engineers(db_session, n=2)
        eng1, _ = pairs[0]
        eng2, _ = pairs[1]
        now = datetime.now(UTC)

        target = _create_session(
            db_session,
            eng1,
            started_at=now - timedelta(hours=3),
            project_name="proj-x",
            has_facets=True,
        )
        db_session.add(
            SessionFacets(
                session_id=target.id,
                session_type="exploration",
                outcome="success",
                goal_categories=["performance", "refactoring"],
            )
        )

        # Candidate has overlapping goal but different type
        cand = _create_session(
            db_session,
            eng2,
            started_at=now - timedelta(hours=2),
            project_name="proj-y",
            has_facets=True,
        )
        db_session.add(
            SessionFacets(
                session_id=cand.id,
                session_type="feature",
                outcome="partial",
                goal_categories=["performance", "testing"],
            )
        )
        db_session.flush()

        r = client.get(
            f"/api/v1/sessions/{target.id}/similar",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["total_found"] >= 1
        found = next((s for s in data["similar_sessions"] if s["session_id"] == cand.id), None)
        assert found is not None
        assert found["similarity_reason"] == "same_goal"

    def test_similar_excludes_self(self, client, db_session, admin_headers):
        """Target session must not appear in its own similar results."""
        _team, pairs = self._setup_team_and_engineers(db_session, n=2)
        eng1, _ = pairs[0]
        eng2, _ = pairs[1]
        now = datetime.now(UTC)

        target = _create_session(
            db_session,
            eng1,
            started_at=now - timedelta(hours=3),
            project_name="self-test-proj",
            has_facets=True,
        )
        db_session.add(
            SessionFacets(session_id=target.id, session_type="feature", outcome="success")
        )

        # Another session with same type so there are results
        cand = _create_session(
            db_session,
            eng2,
            started_at=now - timedelta(hours=2),
            project_name="self-test-proj",
            has_facets=True,
        )
        db_session.add(SessionFacets(session_id=cand.id, session_type="feature", outcome="success"))
        db_session.flush()

        r = client.get(
            f"/api/v1/sessions/{target.id}/similar",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        found_ids = [s["session_id"] for s in data["similar_sessions"]]
        assert target.id not in found_ids

    def test_similar_cross_team_excluded(self, client, db_session, admin_headers):
        """Sessions from a different team are not returned."""
        # Team A
        team_a = Team(name=f"Team A {uuid.uuid4().hex[:6]}")
        db_session.add(team_a)
        db_session.flush()
        eng_a, _ = _make_engineer(db_session, team_a, name="EngA")

        # Team B
        team_b = Team(name=f"Team B {uuid.uuid4().hex[:6]}")
        db_session.add(team_b)
        db_session.flush()
        eng_b, _ = _make_engineer(db_session, team_b, name="EngB")

        now = datetime.now(UTC)

        target = _create_session(
            db_session,
            eng_a,
            started_at=now - timedelta(hours=3),
            project_name="shared-proj",
            has_facets=True,
        )
        db_session.add(
            SessionFacets(session_id=target.id, session_type="feature", outcome="success")
        )

        # Session from Team B with identical attributes
        cross = _create_session(
            db_session,
            eng_b,
            started_at=now - timedelta(hours=2),
            project_name="shared-proj",
            has_facets=True,
        )
        db_session.add(
            SessionFacets(session_id=cross.id, session_type="feature", outcome="success")
        )
        db_session.flush()

        r = client.get(
            f"/api/v1/sessions/{target.id}/similar",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        found_ids = [s["session_id"] for s in data["similar_sessions"]]
        assert cross.id not in found_ids

    def test_similar_empty(self, client, db_session, admin_headers):
        """A unique session with no matching candidates returns empty."""
        _team, pairs = self._setup_team_and_engineers(db_session, n=1)
        eng1, _ = pairs[0]
        now = datetime.now(UTC)

        target = _create_session(
            db_session,
            eng1,
            started_at=now - timedelta(hours=1),
            project_name="unique-proj",
            has_facets=True,
        )
        db_session.add(
            SessionFacets(
                session_id=target.id,
                session_type="one_off_type",
                outcome="success",
                goal_categories=["niche_goal"],
            )
        )
        db_session.flush()

        r = client.get(
            f"/api/v1/sessions/{target.id}/similar",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["total_found"] == 0
        assert data["similar_sessions"] == []
