"""Tests for the conversational data explorer."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from primer.common.models import (
    Engineer,
    GitRepository,
    PullRequest,
    SessionCommit,
    SessionFacets,
    Team,
    ToolUsage,
)
from primer.common.models import Session as SessionModel
from primer.server.services.auth_service import create_access_token


@pytest.fixture
def team(db_session):
    t = Team(name=f"Explorer-Team-{uuid.uuid4().hex[:6]}")
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture
def engineer(db_session, team):
    eng = Engineer(
        name="Explorer Tester",
        email=f"explorer-{uuid.uuid4().hex[:6]}@example.com",
        api_key_hash="",
        team_id=team.id,
        role="engineer",
    )
    db_session.add(eng)
    db_session.flush()
    return eng


@pytest.fixture
def admin_engineer(db_session, team):
    eng = Engineer(
        name="Explorer Admin",
        email=f"admin-explorer-{uuid.uuid4().hex[:6]}@example.com",
        api_key_hash="",
        team_id=team.id,
        role="admin",
    )
    db_session.add(eng)
    db_session.flush()
    return eng


def _jwt_cookie(eng):
    return {"primer_access": create_access_token(eng)}


def _seed_sessions(db, engineer_id, count=3):
    """Seed sessions for explorer tests."""
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
            project_name="test-project",
            first_prompt="Fix the login bug",
        )
        db.add(s)
        db.flush()

        facets = SessionFacets(
            session_id=sid,
            outcome="success" if i % 2 == 0 else "partial",
            session_type="debugging",
            friction_counts={"tool_error": 1} if i == 0 else None,
        )
        db.add(facets)

        tool = ToolUsage(session_id=sid, tool_name="Read", call_count=5)
        db.add(tool)

    db.flush()


class TestExplorerEndpoint:
    def test_auth_required(self, client):
        """No auth → 401."""
        resp = client.post(
            "/api/v1/explorer/chat",
            json={"messages": [{"role": "user", "content": "hello"}]},
        )
        assert resp.status_code == 401

    def test_returns_streaming_response(self, client, engineer, db_session):
        """POST with auth returns text/event-stream content type."""
        _seed_sessions(db_session, engineer.id)
        cookies = _jwt_cookie(engineer)

        # Mock the Anthropic streaming call
        with patch("primer.server.services.explorer_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            mock_settings.explorer_model = "claude-sonnet-4-6"
            mock_settings.explorer_max_tool_rounds = 5

            resp = client.post(
                "/api/v1/explorer/chat",
                json={"messages": [{"role": "user", "content": "How am I doing?"}]},
                cookies=cookies,
            )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

    def test_no_api_key_returns_error_event(self, client, engineer, db_session):
        """When no Anthropic API key is configured, returns an error SSE event."""
        _seed_sessions(db_session, engineer.id)
        cookies = _jwt_cookie(engineer)

        with patch("primer.server.services.explorer_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            mock_settings.explorer_model = "claude-sonnet-4-6"
            mock_settings.explorer_max_tool_rounds = 5

            resp = client.post(
                "/api/v1/explorer/chat",
                json={"messages": [{"role": "user", "content": "test"}]},
                cookies=cookies,
            )

        assert resp.status_code == 200
        body = resp.text
        assert "event: error" in body
        assert "not configured" in body

    def test_admin_auth_works(self, client, admin_headers, db_session):
        """Admin key auth works for explorer."""
        with patch("primer.server.services.explorer_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            mock_settings.explorer_model = "claude-sonnet-4-6"
            mock_settings.explorer_max_tool_rounds = 5

            resp = client.post(
                "/api/v1/explorer/chat",
                json={"messages": [{"role": "user", "content": "test"}]},
                headers=admin_headers,
            )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")


class TestToolExecution:
    def test_get_overview_stats(self, db_session, engineer):
        """Tool executor returns valid JSON for get_overview_stats."""
        _seed_sessions(db_session, engineer.id)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_overview_stats",
            {},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert "total_sessions" in data
        assert data["total_sessions"] == 3

    def test_get_friction_report(self, db_session, engineer):
        """Tool executor returns valid JSON for get_friction_report."""
        _seed_sessions(db_session, engineer.id)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_friction_report",
            {},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert isinstance(data, list)

    def test_get_cost_breakdown(self, db_session, engineer):
        """Tool executor returns valid JSON for get_cost_breakdown."""
        _seed_sessions(db_session, engineer.id)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_cost_breakdown",
            {},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert "total_estimated_cost" in data

    def test_get_tool_rankings(self, db_session, engineer):
        """Tool executor returns valid JSON for get_tool_rankings."""
        _seed_sessions(db_session, engineer.id)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_tool_rankings",
            {"limit": 5},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["tool_name"] == "Read"

    def test_get_engineer_leaderboard(self, db_session, engineer):
        """Tool executor returns valid JSON for get_engineer_leaderboard."""
        _seed_sessions(db_session, engineer.id)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_engineer_leaderboard",
            {"sort_by": "total_sessions", "limit": 10},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert "engineers" in data

    def test_get_daily_trends(self, db_session, engineer):
        """Tool executor returns valid JSON for get_daily_trends."""
        _seed_sessions(db_session, engineer.id)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_daily_trends",
            {"days": 7},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert isinstance(data, list)

    def test_get_session_health(self, db_session, engineer):
        """Tool executor returns valid JSON for get_session_health."""
        _seed_sessions(db_session, engineer.id)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_session_health",
            {},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert "sessions_analyzed" in data

    def test_get_productivity(self, db_session, engineer):
        """Tool executor returns valid JSON for get_productivity."""
        _seed_sessions(db_session, engineer.id)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_productivity",
            {},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert "adoption_rate" in data

    def test_search_sessions(self, db_session, engineer):
        """Tool executor search_sessions returns matching sessions."""
        _seed_sessions(db_session, engineer.id)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "search_sessions",
            {"project": "test-project"},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_search_sessions_by_keyword(self, db_session, engineer):
        """Tool executor search_sessions filters by keyword."""
        _seed_sessions(db_session, engineer.id)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "search_sessions",
            {"keyword": "login"},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_get_session_detail(self, db_session, engineer):
        """Tool executor returns session detail for valid ID."""
        _seed_sessions(db_session, engineer.id)

        # Get a session ID
        session = (
            db_session.query(SessionModel).filter(SessionModel.engineer_id == engineer.id).first()
        )

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_session_detail",
            {"session_id": session.id},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert data["id"] == session.id
        assert data["project_name"] == "test-project"
        assert data["facets"] is not None
        assert len(data["tools"]) > 0

    def test_get_session_detail_not_found(self, db_session, engineer):
        """Tool executor returns error for unknown session ID."""
        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_session_detail",
            {"session_id": "nonexistent"},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert "error" in data

    def test_unknown_tool(self, db_session, engineer):
        """Tool executor handles unknown tool names gracefully."""
        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "nonexistent_tool",
            {},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert "error" in data

    def test_role_scoping_engineer(self, db_session, engineer, team):
        """Engineer scope restricts to own data."""
        # Create another engineer with sessions
        other = Engineer(
            name="Other Engineer",
            email=f"other-{uuid.uuid4().hex[:6]}@example.com",
            api_key_hash="",
            team_id=team.id,
            role="engineer",
        )
        db_session.add(other)
        db_session.flush()
        _seed_sessions(db_session, other.id, count=5)
        _seed_sessions(db_session, engineer.id, count=2)

        from primer.server.services.explorer_service import _execute_tool

        # Engineer only sees own sessions
        result = _execute_tool(
            "get_overview_stats",
            {},
            db_session,
            team_id=None,
            engineer_id=engineer.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert data["total_sessions"] == 2


class TestSummarizeResult:
    def test_overview_summary(self):
        from primer.server.services.explorer_service import _summarize_result

        data = json.dumps({"total_sessions": 42, "success_rate": 0.85, "estimated_cost": 12.50})
        summary = _summarize_result(data)
        assert "42 sessions" in summary
        assert "$12.50" in summary

    def test_cost_summary(self):
        from primer.server.services.explorer_service import _summarize_result

        data = json.dumps({"total_estimated_cost": 99.99})
        summary = _summarize_result(data)
        assert "$99.99" in summary

    def test_list_summary(self):
        from primer.server.services.explorer_service import _summarize_result

        data = json.dumps([{"a": 1}, {"a": 2}, {"a": 3}])
        summary = _summarize_result(data)
        assert "3 items" in summary

    def test_error_summary(self):
        from primer.server.services.explorer_service import _summarize_result

        data = json.dumps({"error": "not found"})
        summary = _summarize_result(data)
        assert "Error" in summary


class TestSSEFormat:
    def test_sse_event_format(self):
        from primer.server.services.explorer_service import _sse_event

        event = _sse_event("text", {"content": "hello"})
        assert event.startswith("event: text\n")
        assert 'data: {"content": "hello"}' in event
        assert event.endswith("\n\n")

    def test_sse_event_done(self):
        from primer.server.services.explorer_service import _sse_event

        event = _sse_event("done", {})
        assert "event: done\n" in event
        assert "data: {}" in event


def _seed_github_data(db, engineer, team):
    """Seed GitHub repos, PRs, and session commits for explorer GitHub tool tests."""
    repo = GitRepository(
        full_name="acme/webapp",
        has_claude_md=True,
        has_agents_md=False,
        has_claude_dir=True,
        ai_readiness_score=0.75,
    )
    repo2 = GitRepository(
        full_name="acme/api",
        has_claude_md=False,
        has_agents_md=True,
        has_claude_dir=False,
        ai_readiness_score=0.40,
    )
    db.add_all([repo, repo2])
    db.flush()

    # Create a session for linking commits
    session_id = str(uuid.uuid4())
    session = SessionModel(
        id=session_id,
        engineer_id=engineer.id,
        message_count=5,
        user_message_count=3,
        assistant_message_count=2,
        tool_call_count=1,
        input_tokens=500,
        output_tokens=250,
        duration_seconds=60.0,
        started_at=datetime.now(UTC) - timedelta(days=1),
        primary_model="claude-sonnet-4-6",
        project_name="webapp",
    )
    db.add(session)
    db.flush()

    # Claude-assisted PR (has SessionCommit linked to a session)
    pr_claude = PullRequest(
        repository_id=repo.id,
        engineer_id=engineer.id,
        github_pr_number=1,
        title="Add login feature",
        state="merged",
        additions=200,
        deletions=50,
        review_comments_count=3,
        pr_created_at=datetime.now(UTC) - timedelta(days=5),
        merged_at=datetime.now(UTC) - timedelta(days=3),
    )
    # Non-Claude PR
    pr_regular = PullRequest(
        repository_id=repo.id,
        engineer_id=engineer.id,
        github_pr_number=2,
        title="Fix CSS styles",
        state="merged",
        additions=30,
        deletions=10,
        review_comments_count=1,
        pr_created_at=datetime.now(UTC) - timedelta(days=4),
        merged_at=datetime.now(UTC) - timedelta(days=2),
    )
    # Open PR on repo2
    pr_open = PullRequest(
        repository_id=repo2.id,
        engineer_id=engineer.id,
        github_pr_number=10,
        title="Add API endpoint",
        state="open",
        additions=100,
        deletions=20,
        review_comments_count=0,
        pr_created_at=datetime.now(UTC) - timedelta(days=1),
    )
    db.add_all([pr_claude, pr_regular, pr_open])
    db.flush()

    # Link pr_claude to session via SessionCommit
    commit = SessionCommit(
        session_id=session_id,
        repository_id=repo.id,
        pull_request_id=pr_claude.id,
        commit_sha="abc123def456",
        lines_added=200,
        lines_deleted=50,
    )
    db.add(commit)
    db.flush()

    return {
        "repo": repo,
        "repo2": repo2,
        "session": session,
        "pr_claude": pr_claude,
        "pr_regular": pr_regular,
        "pr_open": pr_open,
        "commit": commit,
    }


class TestGitHubTools:
    def test_get_pr_comparison(self, db_session, engineer, team):
        """get_pr_comparison returns Claude vs non-Claude metrics."""
        _seed_github_data(db_session, engineer, team)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_pr_comparison",
            {},
            db_session,
            team_id=team.id,
            engineer_id=None,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert data["total_prs_analyzed"] == 3
        assert data["claude_assisted"]["pr_count"] == 1
        assert data["non_claude"]["pr_count"] == 2

    def test_get_repo_readiness(self, db_session, engineer, team):
        """get_repo_readiness returns repos ordered by score."""
        _seed_github_data(db_session, engineer, team)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_repo_readiness",
            {},
            db_session,
            team_id=team.id,
            engineer_id=None,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 2
        # Highest score first
        assert data[0]["full_name"] == "acme/webapp"
        assert data[0]["ai_readiness_score"] == 0.75
        assert data[0]["has_claude_md"] is True
        assert data[1]["full_name"] == "acme/api"

    def test_get_repo_readiness_with_limit(self, db_session, engineer, team):
        """get_repo_readiness respects limit parameter."""
        _seed_github_data(db_session, engineer, team)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "get_repo_readiness",
            {"limit": 1},
            db_session,
            team_id=team.id,
            engineer_id=None,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert len(data) == 1

    def test_search_pull_requests(self, db_session, engineer, team):
        """search_pull_requests returns all PRs for the engineer."""
        _seed_github_data(db_session, engineer, team)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "search_pull_requests",
            {},
            db_session,
            team_id=team.id,
            engineer_id=None,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_search_pull_requests_by_repo(self, db_session, engineer, team):
        """search_pull_requests filters by repo name."""
        _seed_github_data(db_session, engineer, team)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "search_pull_requests",
            {"repo": "api"},
            db_session,
            team_id=team.id,
            engineer_id=None,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["repository"] == "acme/api"

    def test_search_pull_requests_by_state(self, db_session, engineer, team):
        """search_pull_requests filters by state."""
        _seed_github_data(db_session, engineer, team)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "search_pull_requests",
            {"state": "open"},
            db_session,
            team_id=team.id,
            engineer_id=None,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["state"] == "open"

    def test_search_pull_requests_by_author(self, db_session, engineer, team):
        """search_pull_requests filters by author name."""
        _seed_github_data(db_session, engineer, team)

        from primer.server.services.explorer_service import _execute_tool

        result = _execute_tool(
            "search_pull_requests",
            {"author": "Explorer Tester"},
            db_session,
            team_id=team.id,
            engineer_id=None,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert len(data) == 3

    def test_scope_isolation_engineer(self, db_session, team):
        """Engineer scope restricts PR search to own PRs."""
        eng1 = Engineer(
            name="Engineer A",
            email=f"eng-a-{uuid.uuid4().hex[:6]}@example.com",
            api_key_hash="",
            team_id=team.id,
            role="engineer",
        )
        eng2 = Engineer(
            name="Engineer B",
            email=f"eng-b-{uuid.uuid4().hex[:6]}@example.com",
            api_key_hash="",
            team_id=team.id,
            role="engineer",
        )
        db_session.add_all([eng1, eng2])
        db_session.flush()

        repo = GitRepository(full_name=f"acme/scope-test-{uuid.uuid4().hex[:6]}")
        db_session.add(repo)
        db_session.flush()

        # PR for eng1
        pr1 = PullRequest(
            repository_id=repo.id,
            engineer_id=eng1.id,
            github_pr_number=100,
            title="Eng1 PR",
            state="merged",
            additions=10,
            deletions=5,
            pr_created_at=datetime.now(UTC),
        )
        # PR for eng2
        pr2 = PullRequest(
            repository_id=repo.id,
            engineer_id=eng2.id,
            github_pr_number=101,
            title="Eng2 PR",
            state="open",
            additions=20,
            deletions=10,
            pr_created_at=datetime.now(UTC),
        )
        db_session.add_all([pr1, pr2])
        db_session.flush()

        from primer.server.services.explorer_service import _execute_tool

        # eng1 should only see their own PR
        result = _execute_tool(
            "search_pull_requests",
            {},
            db_session,
            team_id=None,
            engineer_id=eng1.id,
            start_date=None,
            end_date=None,
        )
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["title"] == "Eng1 PR"
