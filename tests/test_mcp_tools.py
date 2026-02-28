import json
from unittest.mock import MagicMock, patch

import httpx
import pytest


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
