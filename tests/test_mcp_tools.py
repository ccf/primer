import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest

from primer.common.schemas import LiveSessionSignal, LiveSessionSignalsResponse


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    monkeypatch.setattr("primer.mcp.tools.API_KEY", "test-key")
    monkeypatch.setattr("primer.mcp.tools.ADMIN_API_KEY", "")
    monkeypatch.setattr("primer.mcp.tools.SERVER_URL", "http://test:8000")


def test_admin_headers():
    from primer.mcp.tools import _admin_headers

    headers = _admin_headers()
    assert headers == {"x-admin-key": "test-key", "x-api-key": "test-key"}


# --- primer_sync ---


def test_primer_sync_no_api_key(monkeypatch):
    monkeypatch.setattr("primer.mcp.tools.API_KEY", "")
    from primer.mcp.tools import primer_sync

    result = primer_sync()
    assert "Error" in result


@patch("primer.mcp.tools.sync_sessions")
def test_primer_sync_success(mock_sync):
    mock_sync.return_value = {"synced": 2, "errors": 0}
    from primer.mcp.tools import primer_sync

    result = primer_sync()
    data = json.loads(result)
    assert data["synced"] == 2
    mock_sync.assert_called_once_with("http://test:8000", "test-key")


# --- primer_my_stats ---


def test_primer_my_stats_no_api_key(monkeypatch):
    monkeypatch.setattr("primer.mcp.tools.API_KEY", "")
    from primer.mcp.tools import primer_my_stats

    result = primer_my_stats()
    assert "Error" in result


@patch("primer.mcp.tools.httpx.get")
def test_primer_my_stats_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"total_sessions": 5}
    mock_get.return_value = mock_resp

    from primer.mcp.tools import primer_my_stats

    result = primer_my_stats(days=7)
    data = json.loads(result)
    assert data["total_sessions"] == 5


@patch("primer.mcp.tools.httpx.get")
def test_primer_my_stats_http_error(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_get.return_value = mock_resp

    from primer.mcp.tools import primer_my_stats

    result = primer_my_stats()
    assert "500" in result


@patch("primer.mcp.tools.httpx.get")
def test_primer_my_stats_request_error(mock_get):
    mock_get.side_effect = httpx.RequestError("connection failed")

    from primer.mcp.tools import primer_my_stats

    result = primer_my_stats()
    assert "Error connecting" in result


# --- primer_team_overview ---


@patch("primer.mcp.tools.httpx.get")
def test_primer_team_overview_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"total_sessions": 10}
    mock_get.return_value = mock_resp

    from primer.mcp.tools import primer_team_overview

    result = primer_team_overview()
    data = json.loads(result)
    assert data["total_sessions"] == 10
    # No params passed when team_id is None
    mock_get.assert_called_once()
    call_kwargs = mock_get.call_args
    assert call_kwargs.kwargs.get("params") == {} or call_kwargs[1].get("params") == {}


@patch("primer.mcp.tools.httpx.get")
def test_primer_team_overview_with_team_id(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"total_sessions": 3}
    mock_get.return_value = mock_resp

    from primer.mcp.tools import primer_team_overview

    result = primer_team_overview(team_id="team-123")
    data = json.loads(result)
    assert data["total_sessions"] == 3
    call_kwargs = mock_get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
    assert params == {"team_id": "team-123"}


def test_primer_team_overview_no_api_key(monkeypatch):
    monkeypatch.setattr("primer.mcp.tools.API_KEY", "")
    from primer.mcp.tools import primer_team_overview

    result = primer_team_overview()
    assert "Error" in result


# --- primer_friction_report ---


@patch("primer.mcp.tools.httpx.get")
def test_primer_friction_report_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"friction_type": "tool_error", "count": 5}]
    mock_get.return_value = mock_resp

    from primer.mcp.tools import primer_friction_report

    result = primer_friction_report()
    data = json.loads(result)
    assert data[0]["friction_type"] == "tool_error"


@patch("primer.mcp.tools.httpx.get")
def test_primer_friction_report_non_200(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = "Forbidden"
    mock_get.return_value = mock_resp

    from primer.mcp.tools import primer_friction_report

    result = primer_friction_report()
    assert "403" in result


def test_primer_friction_report_no_api_key(monkeypatch):
    monkeypatch.setattr("primer.mcp.tools.API_KEY", "")
    from primer.mcp.tools import primer_friction_report

    result = primer_friction_report()
    assert "Error" in result


# --- primer_recommendations ---


@patch("primer.mcp.tools.httpx.get")
def test_primer_recommendations_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"category": "friction", "title": "Fix it"}]
    mock_get.return_value = mock_resp

    from primer.mcp.tools import primer_recommendations

    result = primer_recommendations()
    data = json.loads(result)
    assert data[0]["category"] == "friction"


@patch("primer.mcp.tools.httpx.get")
def test_primer_recommendations_request_error(mock_get):
    mock_get.side_effect = httpx.RequestError("timeout")

    from primer.mcp.tools import primer_recommendations

    result = primer_recommendations()
    assert "Error connecting" in result


def test_primer_recommendations_no_api_key(monkeypatch):
    monkeypatch.setattr("primer.mcp.tools.API_KEY", "")
    from primer.mcp.tools import primer_recommendations

    result = primer_recommendations()
    assert "Error" in result


# --- primer_coaching ---


@patch("primer.mcp.tools.httpx.get")
def test_primer_coaching_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "brief_type": "retrospective",
        "status_summary": "12 sessions · 80% success rate",
        "sections": [{"title": "Top recommendations", "items": ["Try the workflow playbook"]}],
    }
    mock_get.return_value = mock_resp

    from primer.mcp.tools import primer_coaching

    result = primer_coaching(days=14)
    assert "Your Primer Coaching Brief" in result
    assert "Try the workflow playbook" in result


# --- primer_session_start_coaching ---


@patch("primer.mcp.tools.httpx.get")
def test_primer_session_start_coaching_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "brief_type": "session_start",
        "status_summary": "Session-start brief · 12 sessions in view",
        "context_summary": "Project: api-server · Workflow: debugging · Task: Fix auth regression",
        "sections": [
            {"title": "How to start this session", "items": ["Start with the debugging playbook"]},
        ],
    }
    mock_get.return_value = mock_resp

    from primer.mcp.tools import primer_session_start_coaching

    result = primer_session_start_coaching(
        project_name="api-server",
        workflow_hint="debugging",
        task_hint="Fix auth regression",
        days=7,
    )

    assert "Your Primer Session-Start Brief" in result
    assert "Project: api-server" in result
    assert "Start with the debugging playbook" in result
    params = mock_get.call_args.kwargs["params"]
    assert params == {
        "project_name": "api-server",
        "workflow_hint": "debugging",
        "task_hint": "Fix auth regression",
        "days": 7,
    }


def test_primer_session_start_coaching_no_api_key(monkeypatch):
    monkeypatch.setattr("primer.mcp.tools.API_KEY", "")
    from primer.mcp.tools import primer_session_start_coaching

    result = primer_session_start_coaching(project_name="api-server")
    assert "Error" in result


# --- primer_live_session_signals ---


@patch("primer.mcp.tools.get_live_session_signals")
def test_primer_live_session_signals_success(mock_get_signals):
    mock_get_signals.return_value = SimpleNamespace(
        risk_level="high",
        satisfaction_signal="negative",
        project_name="api-server",
        session_id="session-123",
        agent_type="claude_code",
        signals=[
            SimpleNamespace(
                severity="warning",
                title="Verification is failing",
                detail="Recent test commands are failing.",
            )
        ],
    )

    from primer.mcp.tools import primer_live_session_signals

    result = primer_live_session_signals(session_id="session-123")
    assert "Live Session Signals" in result
    assert "Verification is failing" in result
    mock_get_signals.assert_called_once_with(
        session_id="session-123",
        transcript_path=None,
    )


@patch("primer.mcp.tools.get_live_session_signals")
def test_primer_live_session_signals_error(mock_get_signals):
    mock_get_signals.side_effect = ValueError("No local sessions found")

    from primer.mcp.tools import primer_live_session_signals

    result = primer_live_session_signals()
    assert "No local sessions found" in result


# --- primer_in_session_nudges ---


@patch("primer.mcp.tools.httpx.get")
@patch("primer.mcp.tools.get_live_session_signals")
def test_primer_in_session_nudges_success(mock_get_signals, mock_get):
    mock_get_signals.return_value = LiveSessionSignalsResponse(
        session_id="session-123",
        agent_type="claude_code",
        project_name="api-server",
        total_messages=12,
        risk_level="high",
        satisfaction_signal="negative",
        signals=[
            LiveSessionSignal(
                signal_type="recovery_loop",
                severity="critical",
                title="Recovery loop detected",
                detail="The session is repeating the same recovery pattern.",
            )
        ],
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "brief_type": "session_start",
        "status_summary": "Session-start brief",
        "sections": [
            {
                "title": "How to start this session",
                "items": ["**Debugging playbook** — Start with Read, Bash."],
            }
        ],
        "sessions_analyzed": 12,
        "generated_at": "2026-03-26T12:00:00Z",
    }
    mock_get.return_value = mock_resp

    from primer.mcp.tools import primer_in_session_nudges

    result = primer_in_session_nudges(project_name="api-server", workflow_hint="debugging")

    assert "In-Session Workflow Nudges" in result
    assert "Break the recovery loop" in result
    assert "Debugging playbook" in result


@patch("primer.mcp.tools.httpx.get")
@patch("primer.mcp.tools.get_live_session_signals")
def test_primer_in_session_nudges_falls_back_when_coaching_payload_is_invalid(
    mock_get_signals, mock_get
):
    mock_get_signals.return_value = LiveSessionSignalsResponse(
        session_id="session-123",
        agent_type="claude_code",
        project_name="api-server",
        total_messages=12,
        risk_level="high",
        satisfaction_signal="negative",
        signals=[
            LiveSessionSignal(
                signal_type="verification_failure",
                severity="warning",
                title="Verification is failing",
                detail="Recent test runs are failing repeatedly.",
            )
        ],
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"brief_type": "session_start", "sections": "invalid"}
    mock_get.return_value = mock_resp

    from primer.mcp.tools import primer_in_session_nudges

    result = primer_in_session_nudges(project_name="api-server")

    assert "In-Session Workflow Nudges" in result
    assert "Tighten the verification loop" in result


@patch("primer.mcp.tools.get_live_session_signals")
def test_primer_in_session_nudges_error(mock_get_signals):
    mock_get_signals.side_effect = ValueError("No local sessions found")

    from primer.mcp.tools import primer_in_session_nudges

    result = primer_in_session_nudges()
    assert "No local sessions found" in result


# --- primer_personal_recaps ---


@patch("primer.mcp.tools.httpx.get")
def test_primer_personal_recaps_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "daily": {
            "headline": "You logged 2 sessions today",
            "summary": "2 sessions · 50% success · $1.20 estimated spend",
            "wins": ["Closed a tough auth bug quickly."],
            "watchouts": ["tool_error showed up 2 times."],
            "next_steps": [
                "Reuse the debugging playbook — Start with the narrowest regression command first."
            ],
        },
        "weekly": {
            "headline": "Your weekly momentum is improving",
            "summary": "7 sessions · 86% success · $5.40 estimated spend",
            "wins": ["Success rate is climbing week over week."],
            "watchouts": ["No major recurring drag signals stood out in this window."],
            "next_steps": [
                "Keep the delivery loop tight — "
                "Stick with the highest-confidence workflow this week."
            ],
        },
    }
    mock_get.return_value = mock_resp

    from primer.mcp.tools import primer_personal_recaps

    result = primer_personal_recaps()
    assert "## Personal Recaps" in result
    assert "### Daily" in result
    assert "### Weekly" in result
    assert "Your weekly momentum is improving" in result


def test_primer_personal_recaps_invalid_period():
    from primer.mcp.tools import primer_personal_recaps

    result = primer_personal_recaps(period="monthly")
    assert "period must be one of daily, weekly, both" in result


def test_primer_personal_recaps_no_api_key(monkeypatch):
    monkeypatch.setattr("primer.mcp.tools.API_KEY", "")
    from primer.mcp.tools import primer_personal_recaps

    result = primer_personal_recaps()
    assert "Error" in result
