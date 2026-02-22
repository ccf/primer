"""Tests for LLM-generated narrative insights."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from primer.common.models import Engineer, SessionFacets, Team, ToolUsage
from primer.common.models import Session as SessionModel
from primer.server.services.auth_service import create_access_token


@pytest.fixture
def team(db_session):
    t = Team(name=f"Narrative-Team-{uuid.uuid4().hex[:6]}")
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture
def engineer(db_session, team):
    eng = Engineer(
        name="Narrative Tester",
        email=f"narrative-{uuid.uuid4().hex[:6]}@example.com",
        api_key_hash="",
        team_id=team.id,
        role="engineer",
    )
    db_session.add(eng)
    db_session.flush()
    return eng


@pytest.fixture
def team_lead(db_session, team):
    eng = Engineer(
        name="Narrative Lead",
        email=f"lead-{uuid.uuid4().hex[:6]}@example.com",
        api_key_hash="",
        team_id=team.id,
        role="team_lead",
    )
    db_session.add(eng)
    db_session.flush()
    return eng


@pytest.fixture
def admin_engineer(db_session, team):
    eng = Engineer(
        name="Narrative Admin",
        email=f"admin-{uuid.uuid4().hex[:6]}@example.com",
        api_key_hash="",
        team_id=team.id,
        role="admin",
    )
    db_session.add(eng)
    db_session.flush()
    return eng


def _jwt_cookie(eng):
    return {"primer_access": create_access_token(eng)}


def _seed_sessions(db, engineer_id, count=6):
    """Seed enough sessions for narrative generation (>= MIN_SESSIONS)."""
    for i in range(count):
        sid = str(uuid.uuid4())
        s = SessionModel(
            id=sid,
            engineer_id=engineer_id,
            message_count=10,
            user_message_count=5,
            assistant_message_count=5,
            tool_call_count=3,
            input_tokens=1000,
            output_tokens=500,
            duration_seconds=120.0,
            started_at=datetime.now(UTC) - timedelta(days=i),
            primary_model="claude-sonnet-4-6",
        )
        db.add(s)
        db.flush()

        facets = SessionFacets(
            session_id=sid,
            outcome="success" if i % 2 == 0 else "partial",
            session_type="feature" if i % 3 == 0 else "debugging",
            friction_counts={"tool_error": 1} if i == 0 else None,
        )
        db.add(facets)

        tool = ToolUsage(session_id=sid, tool_name="Read", call_count=5)
        db.add(tool)

    db.flush()


MOCK_ANTHROPIC_RESPONSE = {
    "content": [
        {
            "type": "text",
            "text": json.dumps(
                [
                    {"title": "At a Glance", "content": "You had **6 sessions** this period."},
                    {"title": "How You Use Claude Code", "content": "Your primary tool is Read."},
                    {"title": "Impressive Things You Did", "content": "Good success rate."},
                    {"title": "Where Things Go Wrong", "content": "Some tool errors."},
                    {"title": "New Usage Patterns", "content": "Emerging patterns."},
                    {"title": "On the Horizon", "content": "Try more tools."},
                    {"title": "Memorable Moment", "content": "Keep going!"},
                ]
            ),
        }
    ],
    "model": "claude-sonnet-4-6",
    "usage": {"input_tokens": 1500, "output_tokens": 800},
}


@pytest.fixture
def mock_anthropic():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_ANTHROPIC_RESPONSE

    with patch("primer.server.services.narrative_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_api_key():
    with patch("primer.server.services.narrative_service.settings") as mock_settings:
        mock_settings.anthropic_api_key = "test-api-key"
        mock_settings.productivity_time_multiplier = 3.0
        mock_settings.productivity_hourly_rate = 75.0
        mock_settings.narrative_cache_ttl_hours = 24
        yield mock_settings


class TestNarrativeStatus:
    def test_status_unavailable_without_key(self, client, admin_headers):
        with patch("primer.server.routers.analytics.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            mock_settings.admin_api_key = "primer-admin-dev-key"
            r = client.get("/api/v1/analytics/narrative/status", headers=admin_headers)
            assert r.status_code == 200
            data = r.json()
            assert data["available"] is False
            assert "not configured" in data["reason"]

    def test_status_available_with_key(self, client, admin_headers):
        with patch("primer.server.routers.analytics.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.admin_api_key = "primer-admin-dev-key"
            r = client.get("/api/v1/analytics/narrative/status", headers=admin_headers)
            assert r.status_code == 200
            assert r.json()["available"] is True


class TestNarrativeEndpoint:
    def test_engineer_scope(self, client, db_session, engineer, mock_anthropic, mock_api_key):
        _seed_sessions(db_session, engineer.id)
        r = client.get(
            "/api/v1/analytics/narrative?scope=engineer",
            cookies=_jwt_cookie(engineer),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["scope"] == "engineer"
        assert data["scope_label"] == "Narrative Tester"
        assert len(data["sections"]) == 7
        assert data["cached"] is False
        assert data["model_used"] == "claude-sonnet-4-6"
        assert "total_sessions" in data["data_summary"]

    def test_team_scope(
        self, client, db_session, team, team_lead, engineer, mock_anthropic, mock_api_key
    ):
        _seed_sessions(db_session, engineer.id)
        r = client.get(
            "/api/v1/analytics/narrative?scope=team",
            cookies=_jwt_cookie(team_lead),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["scope"] == "team"

    def test_org_scope_requires_admin_or_lead(
        self, client, db_session, engineer, mock_anthropic, mock_api_key
    ):
        _seed_sessions(db_session, engineer.id)
        r = client.get(
            "/api/v1/analytics/narrative?scope=org",
            cookies=_jwt_cookie(engineer),
        )
        assert r.status_code == 403

    def test_org_scope_with_admin(
        self, client, db_session, admin_engineer, engineer, mock_anthropic, mock_api_key
    ):
        _seed_sessions(db_session, engineer.id)
        r = client.get(
            "/api/v1/analytics/narrative?scope=org",
            cookies=_jwt_cookie(admin_engineer),
        )
        assert r.status_code == 200
        assert r.json()["scope"] == "org"

    def test_invalid_scope(self, client, admin_headers):
        r = client.get(
            "/api/v1/analytics/narrative?scope=invalid",
            headers=admin_headers,
        )
        assert r.status_code == 422

    def test_insufficient_data(self, client, db_session, engineer, mock_api_key):
        # No sessions seeded — should get 422
        r = client.get(
            "/api/v1/analytics/narrative?scope=engineer",
            cookies=_jwt_cookie(engineer),
        )
        assert r.status_code == 422
        assert "Insufficient data" in r.json()["detail"]

    def test_api_key_not_configured(self, client, db_session, engineer):
        _seed_sessions(db_session, engineer.id)
        with patch("primer.server.services.narrative_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            r = client.get(
                "/api/v1/analytics/narrative?scope=engineer",
                cookies=_jwt_cookie(engineer),
            )
            assert r.status_code == 503
            assert "not configured" in r.json()["detail"]


class TestNarrativeCaching:
    def test_cache_hit(self, client, db_session, engineer, mock_anthropic, mock_api_key):
        _seed_sessions(db_session, engineer.id)

        # First call — should hit the API
        r1 = client.get(
            "/api/v1/analytics/narrative?scope=engineer",
            cookies=_jwt_cookie(engineer),
        )
        assert r1.status_code == 200
        assert r1.json()["cached"] is False

        # Second call — should return from cache
        r2 = client.get(
            "/api/v1/analytics/narrative?scope=engineer",
            cookies=_jwt_cookie(engineer),
        )
        assert r2.status_code == 200
        assert r2.json()["cached"] is True
        # API should only have been called once
        assert mock_anthropic.post.call_count == 1

    def test_force_refresh(self, client, db_session, engineer, mock_anthropic, mock_api_key):
        _seed_sessions(db_session, engineer.id)

        # First call
        r1 = client.get(
            "/api/v1/analytics/narrative?scope=engineer",
            cookies=_jwt_cookie(engineer),
        )
        assert r1.status_code == 200

        # Force refresh — should call API again
        r2 = client.get(
            "/api/v1/analytics/narrative?scope=engineer&force_refresh=true",
            cookies=_jwt_cookie(engineer),
        )
        assert r2.status_code == 200
        assert r2.json()["cached"] is False
        assert mock_anthropic.post.call_count == 2


class TestNarrativeService:
    def test_call_anthropic_error(self, db_session, engineer, mock_api_key):
        """Test that API errors are raised as RuntimeError."""
        _seed_sessions(db_session, engineer.id)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("primer.server.services.narrative_service.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_cls.return_value = mock_client

            from primer.server.services.narrative_service import generate_narrative

            with pytest.raises(RuntimeError, match="Anthropic API returned 500"):
                generate_narrative(db_session, scope="engineer", engineer_id=engineer.id)

    def test_gather_data_returns_dict(self, db_session, engineer):
        """Test that _gather_data returns expected keys."""
        _seed_sessions(db_session, engineer.id)

        from primer.server.services.narrative_service import _gather_data

        data = _gather_data(db_session, "engineer", engineer_id=engineer.id)
        assert "total_sessions" in data
        assert data["total_sessions"] >= 5
        assert "top_tools" in data
        assert "top_friction" in data
        assert "config_suggestions" in data  # engineer-specific

    def test_gather_data_team_includes_engineers(self, db_session, team, engineer):
        """Test that team scope includes top_engineers."""
        _seed_sessions(db_session, engineer.id)

        from primer.server.services.narrative_service import _gather_data

        data = _gather_data(db_session, "team", team_id=team.id)
        assert "top_engineers" in data

    def test_build_prompt_sections(self):
        """Test that prompt contains expected sections."""
        from primer.server.services.narrative_service import _build_prompt

        system, user = _build_prompt("engineer", "Alice", {"total_sessions": 10})
        assert "JSON array" in system
        assert "At a Glance" in user
        assert "Memorable Moment" in user
        assert "Alice" in user
        # Engineer scope includes formatting instructions
        assert "What's working:" in user

        system, user = _build_prompt("team", "Platform", {"total_sessions": 50})
        assert "Team Overview" in user

        system, user = _build_prompt("org", "Organization", {"total_sessions": 200})
        assert "Organization Health" in user


class TestNarrativeEngineerIdParam:
    """Tests for admin/team_lead viewing another engineer's narrative."""

    def test_admin_can_view_other_engineer(
        self, client, db_session, admin_engineer, engineer, mock_anthropic, mock_api_key
    ):
        _seed_sessions(db_session, engineer.id)
        r = client.get(
            f"/api/v1/analytics/narrative?scope=engineer&engineer_id={engineer.id}",
            cookies=_jwt_cookie(admin_engineer),
        )
        assert r.status_code == 200
        assert r.json()["scope"] == "engineer"
        assert r.json()["scope_label"] == "Narrative Tester"

    def test_team_lead_can_view_own_team_engineer(
        self, client, db_session, team_lead, engineer, mock_anthropic, mock_api_key
    ):
        _seed_sessions(db_session, engineer.id)
        r = client.get(
            f"/api/v1/analytics/narrative?scope=engineer&engineer_id={engineer.id}",
            cookies=_jwt_cookie(team_lead),
        )
        assert r.status_code == 200

    def test_team_lead_blocked_other_team_engineer(
        self, client, db_session, team_lead, mock_api_key
    ):
        """Team lead cannot view engineer from another team."""
        other_team = Team(name="Other-Team")
        db_session.add(other_team)
        db_session.flush()

        other_eng = Engineer(
            name="Other Eng",
            email=f"other-{uuid.uuid4().hex[:6]}@example.com",
            api_key_hash="",
            team_id=other_team.id,
            role="engineer",
        )
        db_session.add(other_eng)
        db_session.flush()
        _seed_sessions(db_session, other_eng.id)

        r = client.get(
            f"/api/v1/analytics/narrative?scope=engineer&engineer_id={other_eng.id}",
            cookies=_jwt_cookie(team_lead),
        )
        assert r.status_code == 403

    def test_regular_engineer_blocked(
        self, client, db_session, engineer, admin_engineer, mock_api_key
    ):
        """Regular engineer cannot view another engineer's narrative."""
        _seed_sessions(db_session, admin_engineer.id)
        r = client.get(
            f"/api/v1/analytics/narrative?scope=engineer&engineer_id={admin_engineer.id}",
            cookies=_jwt_cookie(engineer),
        )
        assert r.status_code == 403

    def test_engineer_can_view_own_via_engineer_id(
        self, client, db_session, engineer, mock_anthropic, mock_api_key
    ):
        """Engineer can view their own narrative when passing their own engineer_id."""
        _seed_sessions(db_session, engineer.id)
        r = client.get(
            f"/api/v1/analytics/narrative?scope=engineer&engineer_id={engineer.id}",
            cookies=_jwt_cookie(engineer),
        )
        assert r.status_code == 200
        assert r.json()["scope"] == "engineer"


class TestConfigurableTTL:
    def test_ttl_reflected_in_cache(self, db_session, engineer, mock_anthropic, mock_api_key):
        """Cache expiry should use the configurable TTL."""
        from primer.common.models import NarrativeCache
        from primer.server.services.narrative_service import generate_narrative

        mock_api_key.narrative_cache_ttl_hours = 48
        _seed_sessions(db_session, engineer.id)

        generate_narrative(db_session, scope="engineer", engineer_id=engineer.id)

        cached = (
            db_session.query(NarrativeCache)
            .filter(
                NarrativeCache.scope == "engineer",
                NarrativeCache.scope_id == engineer.id,
            )
            .first()
        )
        assert cached is not None
        hours_diff = (cached.expires_at - cached.created_at).total_seconds() / 3600
        assert abs(hours_diff - 48) < 0.1


class TestRefreshAllNarratives:
    def test_refresh_discovers_scopes(self, db_session, engineer, mock_anthropic, mock_api_key):
        """refresh_all_narratives finds engineers/teams/org and returns count."""
        from primer.server.services.narrative_service import refresh_all_narratives

        _seed_sessions(db_session, engineer.id)

        count = refresh_all_narratives(db_session)
        # Should have refreshed at least: 1 engineer + 1 team + 1 org
        assert count >= 3
