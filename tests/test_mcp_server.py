from unittest.mock import patch


@patch("primer.mcp.server.primer_sync")
def test_sync_tool(mock_sync):
    mock_sync.return_value = '{"synced": 1}'

    from primer.mcp.server import sync

    result = sync()
    assert result == '{"synced": 1}'
    mock_sync.assert_called_once()


@patch("primer.mcp.server.primer_my_stats")
def test_my_stats_tool(mock_stats):
    mock_stats.return_value = '{"total_sessions": 5}'

    from primer.mcp.server import my_stats

    result = my_stats(days=7)
    assert result == '{"total_sessions": 5}'
    mock_stats.assert_called_once_with(days=7)


@patch("primer.mcp.server.primer_team_overview")
def test_team_overview_tool(mock_overview):
    mock_overview.return_value = '{"total_sessions": 10}'

    from primer.mcp.server import team_overview

    result = team_overview(team_id="team-1")
    assert result == '{"total_sessions": 10}'
    mock_overview.assert_called_once_with(team_id="team-1")


@patch("primer.mcp.server.primer_friction_report")
def test_friction_report_tool(mock_friction):
    mock_friction.return_value = "[]"

    from primer.mcp.server import friction_report

    result = friction_report()
    assert result == "[]"
    mock_friction.assert_called_once_with(team_id=None)


@patch("primer.mcp.server.primer_recommendations")
def test_recommendations_tool(mock_recs):
    mock_recs.return_value = "[]"

    from primer.mcp.server import recommendations

    result = recommendations(team_id="team-2")
    assert result == "[]"
    mock_recs.assert_called_once_with(team_id="team-2")


@patch("primer.mcp.server.primer_session_start_coaching")
def test_session_start_coaching_tool(mock_session_start):
    mock_session_start.return_value = "brief"

    from primer.mcp.server import session_start_coaching

    result = session_start_coaching(
        project_name="api-server",
        workflow_hint="debugging",
        task_hint="Fix auth regression",
        days=14,
    )
    assert result == "brief"
    mock_session_start.assert_called_once_with(
        project_name="api-server",
        workflow_hint="debugging",
        task_hint="Fix auth regression",
        days=14,
    )


@patch("primer.mcp.server.primer_live_session_signals")
def test_live_session_signals_tool(mock_live_signals):
    mock_live_signals.return_value = "signals"

    from primer.mcp.server import live_session_signals

    result = live_session_signals(session_id="session-123")
    assert result == "signals"
    mock_live_signals.assert_called_once_with(
        session_id="session-123",
        transcript_path=None,
    )


@patch("primer.mcp.server.primer_in_session_nudges")
def test_in_session_nudges_tool(mock_nudges):
    mock_nudges.return_value = "nudges"

    from primer.mcp.server import in_session_nudges

    result = in_session_nudges(
        project_name="api-server",
        workflow_hint="debugging",
        task_hint="Fix auth regression",
        session_id="session-123",
    )
    assert result == "nudges"
    mock_nudges.assert_called_once_with(
        project_name="api-server",
        workflow_hint="debugging",
        task_hint="Fix auth regression",
        session_id="session-123",
        transcript_path=None,
    )
