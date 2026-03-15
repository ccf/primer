import uuid

from primer.common.models import GitRepository, SessionFacets


def _messages(count: int) -> list[dict[str, str | int]]:
    return [
        {
            "ordinal": ordinal,
            "role": "human" if ordinal % 2 == 0 else "assistant",
            "content_text": f"message {ordinal}",
        }
        for ordinal in range(count)
    ]


def _ingest_session(client, api_key, **kwargs):
    session_id = kwargs.pop("session_id", str(uuid.uuid4()))
    payload = {
        "session_id": session_id,
        "api_key": api_key,
        "message_count": 10,
        "user_message_count": 5,
        "assistant_message_count": 5,
        "tool_call_count": 3,
        "input_tokens": 1000,
        "output_tokens": 500,
        "duration_seconds": 120.0,
        **kwargs,
    }
    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 200
    return session_id


def test_overview_empty(client, admin_headers):
    r = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_sessions"] == 0


def test_overview_with_data(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        messages=_messages(10),
        facets={
            "outcome": "success",
            "session_type": "feature",
        },
    )
    _ingest_session(
        client,
        api_key,
        messages=_messages(10),
        facets={
            "outcome": "success",
            "session_type": "debugging",
        },
    )
    _ingest_session(
        client,
        api_key,
        messages=_messages(10),
        facets={
            "outcome": "partial",
            "session_type": "feature",
        },
    )

    r = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_sessions"] == 3
    assert data["total_engineers"] == 1
    assert data["total_messages"] == 30
    assert data["outcome_counts"]["success"] == 2
    assert data["outcome_counts"]["partial"] == 1
    assert data["session_type_counts"]["feature"] == 2


def test_overview_treats_legacy_success_outcomes_as_canonical(
    client, engineer_with_key, admin_headers, db_session
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        facets={
            "outcome": "success",
            "session_type": "feature",
        },
    )
    legacy_sid = _ingest_session(
        client,
        api_key,
        facets={
            "outcome": "success",
            "session_type": "debugging",
        },
    )

    legacy_facets = (
        db_session.query(SessionFacets).filter(SessionFacets.session_id == legacy_sid).one()
    )
    legacy_facets.outcome = "fully_achieved"
    db_session.flush()

    r = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["outcome_counts"]["success"] == 2
    assert data["success_rate"] == 1.0


def test_overview_excludes_cursor_sessions_from_avg_health_score(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        facets={"outcome": "success"},
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
    )

    response = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total_sessions"] == 2
    assert data["avg_health_score"] == 100.0


def test_overview_avg_messages_per_session_requires_actual_message_rows(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        message_count=2,
        user_message_count=1,
        assistant_message_count=1,
        messages=[
            {"ordinal": 0, "role": "human", "content_text": "Investigate failing test"},
            {"ordinal": 1, "role": "assistant", "content_text": "Checking the suite now"},
        ],
    )
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        message_count=10,
        user_message_count=5,
        assistant_message_count=5,
        messages=[],
    )

    response = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total_messages"] == 2
    assert data["avg_messages_per_session"] == 2.0


def test_overview_includes_cursor_facets_when_present(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        facets={"outcome": "success", "session_type": "feature"},
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        facets={"outcome": "failure", "session_type": "debugging"},
    )

    response = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["success_rate"] == 0.5
    assert data["outcome_counts"] == {"success": 1, "failure": 1}
    assert data["session_type_counts"] == {"feature": 1, "debugging": 1}


def test_overview_includes_codex_facets_from_supported_transcript_source(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="codex_cli",
        messages=_messages(6),
        facets={"outcome": "success", "session_type": "feature"},
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        messages=_messages(6),
        facets={"outcome": "failure", "session_type": "debugging"},
    )

    response = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["success_rate"] == 0.5
    assert data["outcome_counts"] == {"success": 1, "failure": 1}
    assert data["session_type_counts"] == {"feature": 1, "debugging": 1}


def test_overview_total_tool_calls_requires_actual_tool_usage_rows(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        tool_call_count=3,
        tool_usages=[
            {"tool_name": "Read", "call_count": 2},
            {"tool_name": "Edit", "call_count": 1},
        ],
    )
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        tool_call_count=9,
        tool_usages=[],
    )

    response = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total_tool_calls"] == 3


def test_overview_model_and_cache_rollups_require_actual_model_usage_rows(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=250,
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_read_tokens": 250,
            }
        ],
    )
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        input_tokens=9000,
        output_tokens=4500,
        cache_read_tokens=1000,
        model_usages=[],
    )

    response = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total_input_tokens"] == 1000
    assert data["total_output_tokens"] == 500
    assert data["cache_hit_rate"] == 0.2


def test_tool_rankings(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        tool_usages=[
            {"tool_name": "Read", "call_count": 10},
            {"tool_name": "Edit", "call_count": 5},
        ],
    )
    _ingest_session(
        client,
        api_key,
        tool_usages=[
            {"tool_name": "Read", "call_count": 8},
            {"tool_name": "Bash", "call_count": 3},
        ],
    )

    r = client.get("/api/v1/analytics/tools", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 2
    assert data[0]["tool_name"] == "Read"
    assert data[0]["total_calls"] == 18


def test_tool_rankings_include_cursor_tool_usage_when_present(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        tool_usages=[{"tool_name": "Read", "call_count": 3}],
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        tool_usages=[
            {"tool_name": "Read", "call_count": 10},
            {"tool_name": "Ghost", "call_count": 7},
        ],
    )

    response = client.get("/api/v1/analytics/tools", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data == [
        {"tool_name": "Read", "total_calls": 13, "session_count": 2},
        {"tool_name": "Ghost", "total_calls": 7, "session_count": 1},
    ]


def test_model_rankings(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1000,
                "output_tokens": 500,
            },
        ],
    )
    _ingest_session(
        client,
        api_key,
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 2000,
                "output_tokens": 1000,
            },
            {"model_name": "claude-haiku-3.5", "input_tokens": 100, "output_tokens": 50},
        ],
    )

    r = client.get("/api/v1/analytics/models", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data[0]["model_name"] == "claude-sonnet-4-5-20250929"
    assert data[0]["total_input_tokens"] == 3000


def test_model_rankings_include_cursor_model_usage_when_present(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1000,
                "output_tokens": 500,
            }
        ],
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 9000,
                "output_tokens": 4500,
            }
        ],
    )

    response = client.get("/api/v1/analytics/models", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data == [
        {
            "model_name": "claude-sonnet-4-5-20250929",
            "total_input_tokens": 10000,
            "total_output_tokens": 5000,
            "session_count": 2,
        }
    ]


def test_friction_report(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        facets={
            "friction_counts": {"tool_error": 3, "permission_denied": 1},
            "friction_detail": "Tool failed on large files",
        },
    )
    _ingest_session(
        client,
        api_key,
        facets={
            "friction_counts": {"tool_error": 2},
            "friction_detail": "Timeout on edit",
        },
    )

    r = client.get("/api/v1/analytics/friction", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    tool_error = next(f for f in data if f["friction_type"] == "tool_error")
    assert tool_error["count"] == 5


def test_friction_report_includes_cursor_facets_when_present(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        facets={
            "friction_counts": {"tool_error": 2},
            "friction_detail": "Supported friction",
        },
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        facets={
            "friction_counts": {"tool_error": 5},
            "friction_detail": "Unsupported cursor friction",
        },
    )

    response = client.get("/api/v1/analytics/friction", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    tool_error = next(f for f in data if f["friction_type"] == "tool_error")
    assert tool_error["count"] == 7
    assert set(tool_error["details"]) == {
        "Supported friction",
        "Unsupported cursor friction",
    }


def test_daily_stats_endpoint(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        started_at="2025-01-15T10:00:00",
        message_count=10,
        tool_call_count=5,
        messages=_messages(10),
        tool_usages=[{"tool_name": "Read", "call_count": 5}],
    )
    _ingest_session(
        client,
        api_key,
        started_at="2025-01-15T14:00:00",
        message_count=8,
        tool_call_count=3,
        messages=_messages(8),
        tool_usages=[{"tool_name": "Edit", "call_count": 3}],
    )
    _ingest_session(
        client,
        api_key,
        started_at="2025-01-16T09:00:00",
        message_count=12,
        tool_call_count=7,
        messages=_messages(12),
        tool_usages=[{"tool_name": "Bash", "call_count": 7}],
    )

    r = client.get("/api/v1/analytics/daily", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 2

    # Results are ordered by date descending
    day_16 = next(d for d in data if d["date"] == "2025-01-16")
    assert day_16["session_count"] == 1
    assert day_16["message_count"] == 12
    assert day_16["tool_call_count"] == 7

    day_15 = next(d for d in data if d["date"] == "2025-01-15")
    assert day_15["session_count"] == 2
    assert day_15["message_count"] == 18
    assert day_15["tool_call_count"] == 8


def test_daily_stats_excludes_sessions_without_supported_tool_telemetry(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        started_at="2025-01-15T10:00:00",
        tool_call_count=5,
        tool_usages=[{"tool_name": "Read", "call_count": 5}],
    )
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        started_at="2025-01-15T12:00:00",
        tool_call_count=4,
        tool_usages=[],
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        started_at="2025-01-15T14:00:00",
        tool_call_count=9,
        tool_usages=[],
    )

    response = client.get("/api/v1/analytics/daily", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    day_15 = next(d for d in data if d["date"] == "2025-01-15")
    assert day_15["session_count"] == 3
    assert day_15["tool_call_count"] == 5


def test_daily_stats_message_count_requires_actual_message_rows(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        started_at="2025-01-15T10:00:00",
        message_count=2,
        user_message_count=1,
        assistant_message_count=1,
        messages=_messages(2),
    )
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        started_at="2025-01-15T12:00:00",
        message_count=10,
        user_message_count=5,
        assistant_message_count=5,
        messages=[],
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        started_at="2025-01-15T14:00:00",
        message_count=9,
        user_message_count=4,
        assistant_message_count=5,
        messages=[],
    )

    response = client.get("/api/v1/analytics/daily", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    day_15 = next(d for d in data if d["date"] == "2025-01-15")
    assert day_15["session_count"] == 3
    assert day_15["message_count"] == 2


def test_daily_stats_success_rate_includes_cursor_facets_when_present(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        started_at="2025-05-01T10:00:00",
        facets={"outcome": "success"},
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        started_at="2025-05-01T14:00:00",
        facets={"outcome": "failure"},
    )

    response = client.get(
        "/api/v1/analytics/daily?start_date=2025-05-01T00:00:00&end_date=2025-05-01T23:59:59",
        headers=admin_headers,
    )
    assert response.status_code == 200

    data = response.json()
    day = data[0]
    assert day["success_rate"] == 0.5


def test_daily_stats_with_team_filter(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(client, api_key, started_at="2025-02-01T10:00:00")

    # Filter by the engineer's team
    r = client.get(
        f"/api/v1/analytics/daily?team_id={_eng.team_id}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1

    # Filter by non-existent team
    r = client.get(
        "/api/v1/analytics/daily?team_id=nonexistent",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json() == []


def test_sessions_list(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    sid = _ingest_session(
        client,
        api_key,
        project_name="my-project",
        tool_usages=[
            {"tool_name": "Read", "call_count": 2},
            {"tool_name": "Edit", "call_count": 1},
        ],
        commits=[
            {
                "sha": "session-list-workflow",
                "message": "feat: workflow session",
                "files_changed": 1,
                "lines_added": 5,
                "lines_deleted": 1,
            }
        ],
    )

    r = client.get("/api/v1/sessions", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()["items"]
    session = next(s for s in data if s["id"] == sid)
    assert session["has_facets"] is False
    assert session["has_workflow_profile"] is True


def test_session_detail(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    sid = _ingest_session(
        client,
        api_key,
        tool_usages=[{"tool_name": "Read", "call_count": 5}],
        messages=[
            {
                "ordinal": 0,
                "role": "assistant",
                "tool_calls": [{"name": "Bash", "input_preview": '{"command":"pytest -q"}'}],
            },
            {
                "ordinal": 1,
                "role": "tool_result",
                "tool_results": [{"name": "Bash", "output_preview": "2 passed in 0.12s"}],
            },
        ],
        facets={"outcome": "success", "brief_summary": "Fixed it"},
    )

    r = client.get(f"/api/v1/sessions/{sid}", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == sid
    assert data["has_facets"] is True
    assert data["facets"]["outcome"] == "success"
    assert len(data["tool_usages"]) == 1
    assert len(data["execution_evidence"]) == 1
    assert data["execution_evidence"][0]["evidence_type"] == "test"
    assert data["execution_evidence"][0]["status"] == "passed"
    assert data["change_shape"] is None
    assert data["recovery_path"] is None


def test_session_detail_includes_change_shape_when_present(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    sid = _ingest_session(
        client,
        api_key,
        messages=[
            {
                "ordinal": 0,
                "role": "assistant",
                "tool_calls": [{"name": "Write", "input_preview": '{"file_path":"src/auth.py"}'}],
            },
            {
                "ordinal": 1,
                "role": "assistant",
                "tool_calls": [
                    {"name": "Bash", "input_preview": '{"command":"git checkout -- src/auth.py"}'}
                ],
            },
        ],
        commits=[
            {
                "sha": "abc123",
                "message": "Update auth flow",
                "files_changed": 1,
                "lines_added": 8,
                "lines_deleted": 2,
            }
        ],
    )

    response = client.get(f"/api/v1/sessions/{sid}", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["change_shape"]["files_touched_count"] == 1
    assert data["change_shape"]["named_touched_files"] == ["src/auth.py"]
    assert data["change_shape"]["diff_size"] == 10
    assert data["change_shape"]["rewrite_indicator"] is True
    assert data["change_shape"]["revert_indicator"] is True


def test_session_detail_includes_recovery_path_when_present(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    sid = _ingest_session(
        client,
        api_key,
        messages=[
            {
                "ordinal": 0,
                "role": "assistant",
                "tool_calls": [{"name": "Bash", "input_preview": '{"command":"pytest -q"}'}],
            },
            {
                "ordinal": 1,
                "role": "tool_result",
                "tool_results": [{"name": "Bash", "output_preview": "2 failed in 0.12s"}],
            },
            {
                "ordinal": 2,
                "role": "assistant",
                "tool_calls": [{"name": "Edit", "input_preview": '{"file_path":"src/auth.py"}'}],
            },
            {
                "ordinal": 3,
                "role": "assistant",
                "tool_calls": [{"name": "Bash", "input_preview": '{"command":"pytest -q"}'}],
            },
            {
                "ordinal": 4,
                "role": "tool_result",
                "tool_results": [{"name": "Bash", "output_preview": "2 passed in 0.10s"}],
            },
        ],
        facets={
            "outcome": "success",
            "friction_counts": {"compile_error": 1},
            "friction_detail": "A test failed before the fix landed",
        },
    )

    response = client.get(f"/api/v1/sessions/{sid}", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["recovery_path"]["recovery_result"] == "recovered"
    assert data["recovery_path"]["recovery_step_count"] == 3
    assert data["recovery_path"]["recovery_strategies"] == ["edit_fix", "rerun_verification"]
    assert data["recovery_path"]["last_verification_status"] == "passed"


def test_session_detail_includes_workflow_profile_when_present(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    sid = _ingest_session(
        client,
        api_key,
        tool_usages=[
            {"tool_name": "Read", "call_count": 2},
            {"tool_name": "Edit", "call_count": 3},
            {"tool_name": "Bash", "call_count": 2},
        ],
        messages=[
            {
                "ordinal": 0,
                "role": "assistant",
                "tool_calls": [{"name": "Bash", "input_preview": '{"command":"pytest -q"}'}],
            },
            {
                "ordinal": 1,
                "role": "tool_result",
                "tool_results": [{"name": "Bash", "output_preview": "2 passed in 0.12s"}],
            },
        ],
        facets={"outcome": "success", "session_type": "implementation"},
        commits=[
            {
                "sha": "abc123",
                "message": "Implement billing export",
                "files_changed": 2,
                "lines_added": 25,
                "lines_deleted": 4,
            }
        ],
    )

    response = client.get(f"/api/v1/sessions/{sid}", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["workflow_profile"]["archetype"] == "feature_delivery"
    assert data["workflow_profile"]["archetype_source"] == "session_type"
    assert data["workflow_profile"]["steps"] == [
        "read",
        "edit",
        "execute",
        "test",
        "ship",
    ]
    assert data["workflow_profile"]["verification_run_count"] == 1


def test_cost_analytics(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1_000_000,
                "output_tokens": 500_000,
            },
        ],
    )
    _ingest_session(
        client,
        api_key,
        model_usages=[
            {
                "model_name": "claude-opus-4-20250514",
                "input_tokens": 100_000,
                "output_tokens": 50_000,
            },
        ],
    )

    r = client.get("/api/v1/analytics/costs", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_estimated_cost"] > 0
    assert len(data["model_breakdown"]) == 2
    # Opus should cost more per token
    opus = next(m for m in data["model_breakdown"] if "opus" in m["model_name"])
    assert opus["estimated_cost"] > 0


def test_cost_analytics_include_cursor_model_usage_when_present(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        started_at="2025-01-15T10:00:00",
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1000,
                "output_tokens": 500,
            }
        ],
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        started_at="2025-01-15T14:00:00",
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 9000,
                "output_tokens": 4500,
            }
        ],
    )

    response = client.get("/api/v1/analytics/costs", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert len(data["model_breakdown"]) == 1
    model = data["model_breakdown"][0]
    assert model["model_name"] == "claude-sonnet-4-5-20250929"
    assert model["input_tokens"] == 10000
    assert model["output_tokens"] == 5000
    assert len(data["daily_costs"]) == 1
    assert data["daily_costs"][0]["session_count"] == 2


def test_tool_adoption_includes_cursor_tool_usage_when_present(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        started_at="2025-01-15T10:00:00",
        tool_usages=[{"tool_name": "Read", "call_count": 3}],
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        started_at="2025-01-15T14:00:00",
        tool_usages=[{"tool_name": "Ghost", "call_count": 7}],
    )

    response = client.get("/api/v1/analytics/tool-adoption", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total_tools_discovered"] == 2
    assert [entry["tool_name"] for entry in data["tool_adoption"]] == ["Ghost", "Read"]
    assert data["tool_adoption"][0]["total_calls"] == 7
    assert data["engineer_profiles"][0]["top_tools"] == ["Ghost", "Read"]
    assert {trend["tool_name"] for trend in data["tool_trends"]} == {"Ghost", "Read"}


def test_overview_includes_estimated_cost(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1000,
                "output_tokens": 500,
            },
        ],
    )
    r = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["estimated_cost"] is not None
    assert data["estimated_cost"] > 0


def test_date_range_filtering(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client, api_key, started_at="2025-01-10T10:00:00", message_count=5, messages=_messages(5)
    )
    _ingest_session(
        client, api_key, started_at="2025-01-20T10:00:00", message_count=10, messages=_messages(10)
    )
    _ingest_session(
        client, api_key, started_at="2025-02-01T10:00:00", message_count=15, messages=_messages(15)
    )

    # Filter to January only
    r = client.get(
        "/api/v1/analytics/overview?start_date=2025-01-01T00:00:00&end_date=2025-01-31T23:59:59",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_sessions"] == 2
    assert data["total_messages"] == 15

    # Filter to February
    r = client.get(
        "/api/v1/analytics/overview?start_date=2025-02-01T00:00:00&end_date=2025-02-28T23:59:59",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_sessions"] == 1
    assert data["total_messages"] == 15


def test_daily_stats_date_range(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(client, api_key, started_at="2025-03-01T10:00:00")
    _ingest_session(client, api_key, started_at="2025-03-15T10:00:00")
    _ingest_session(client, api_key, started_at="2025-04-01T10:00:00")

    r = client.get(
        "/api/v1/analytics/daily?start_date=2025-03-01T00:00:00&end_date=2025-03-31T23:59:59",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2


def test_recommendations(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    # Ingest enough sessions with friction to trigger recommendations
    for _ in range(6):
        _ingest_session(
            client,
            api_key,
            facets={
                "friction_counts": {"tool_error": 2},
                "friction_detail": "Something went wrong",
            },
        )

    r = client.get("/api/v1/analytics/recommendations", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert any(rec["category"] == "friction" for rec in data)


def test_engineer_analytics(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        project_name="test-project",
        facets={"outcome": "success", "session_type": "feature"},
        tool_usages=[{"tool_name": "Read", "call_count": 10}],
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 5000,
                "output_tokens": 2000,
            }
        ],
    )
    _ingest_session(
        client,
        api_key,
        project_name="test-project",
        facets={"outcome": "failure", "session_type": "debugging"},
        tool_usages=[{"tool_name": "Bash", "call_count": 5}],
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 3000,
                "output_tokens": 1000,
            }
        ],
    )

    r = client.get("/api/v1/analytics/engineers", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_count"] >= 1
    eng = data["engineers"][0]
    assert eng["total_sessions"] >= 2
    assert eng["total_tokens"] > 0
    assert eng["estimated_cost"] > 0
    assert eng["success_rate"] is not None
    assert len(eng["top_tools"]) > 0


def test_engineer_analytics_excludes_sessions_without_supported_model_telemetry_from_token_totals(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        project_name="token-safe-project",
        agent_type="claude_code",
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1000,
                "output_tokens": 500,
            }
        ],
    )
    _ingest_session(
        client,
        api_key,
        project_name="token-safe-project",
        agent_type="cursor",
        model_usages=[],
    )

    response = client.get("/api/v1/analytics/engineers", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    engineer = data["engineers"][0]
    assert engineer["total_sessions"] == 2
    assert engineer["total_tokens"] == 1500


def test_project_analytics(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        project_name="analytics-test-proj",
        facets={"outcome": "success"},
        tool_usages=[{"tool_name": "Read", "call_count": 8}],
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 2000,
                "output_tokens": 1000,
            }
        ],
    )
    _ingest_session(
        client,
        api_key,
        project_name="analytics-test-proj",
        facets={"outcome": "partial"},
        tool_usages=[{"tool_name": "Edit", "call_count": 4}],
        model_usages=[
            {"model_name": "claude-sonnet-4-5-20250929", "input_tokens": 1000, "output_tokens": 500}
        ],
    )

    r = client.get("/api/v1/analytics/projects", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_count"] >= 1
    proj = next(p for p in data["projects"] if p["project_name"] == "analytics-test-proj")
    assert proj["total_sessions"] == 2
    assert proj["unique_engineers"] == 1
    assert proj["estimated_cost"] > 0
    assert "success" in proj["outcome_distribution"]
    assert len(proj["top_tools"]) > 0


def test_project_analytics_excludes_sessions_without_supported_model_telemetry_from_token_totals(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        project_name="token-safe-project",
        agent_type="claude_code",
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1000,
                "output_tokens": 500,
            }
        ],
    )
    _ingest_session(
        client,
        api_key,
        project_name="token-safe-project",
        agent_type="cursor",
        model_usages=[],
    )

    response = client.get("/api/v1/analytics/projects", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    project = next(p for p in data["projects"] if p["project_name"] == "token-safe-project")
    assert project["total_sessions"] == 2
    assert project["total_tokens"] == 1500


def test_project_analytics_includes_cursor_facets_when_present(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        project_name="facet-safe-project",
        agent_type="claude_code",
        facets={"outcome": "success"},
    )
    _ingest_session(
        client,
        api_key,
        project_name="facet-safe-project",
        agent_type="cursor",
        facets={"outcome": "failure"},
    )

    response = client.get("/api/v1/analytics/projects", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    project = next(p for p in data["projects"] if p["project_name"] == "facet-safe-project")
    assert project["outcome_distribution"] == {"success": 1, "failure": 1}


def test_project_comparison_ranks_easiest_and_hardest_projects(
    client, engineer_with_key, admin_headers, db_session
):
    _eng, api_key = engineer_with_key
    for _ in range(2):
        _ingest_session(
            client,
            api_key,
            project_name="easy-project",
            agent_type="claude_code",
            messages=_messages(6),
            tool_usages=[
                {"tool_name": "Edit", "call_count": 2},
                {"tool_name": "Bash", "call_count": 1},
            ],
            model_usages=[
                {
                    "model_name": "claude-sonnet-4",
                    "input_tokens": 1200,
                    "output_tokens": 600,
                }
            ],
            git_remote_url="https://github.com/acme/easy-project.git",
            facets={
                "outcome": "success",
                "session_type": "implementation",
                "friction_counts": {},
            },
        )

    for _ in range(2):
        _ingest_session(
            client,
            api_key,
            project_name="hard-project",
            agent_type="cursor",
            messages=_messages(6),
            tool_usages=[
                {"tool_name": "Read", "call_count": 2},
                {"tool_name": "Bash", "call_count": 1},
            ],
            model_usages=[
                {
                    "model_name": "gpt-5-mini",
                    "input_tokens": 900,
                    "output_tokens": 300,
                }
            ],
            git_remote_url="https://github.com/acme/hard-project.git",
            facets={
                "outcome": "failure",
                "session_type": "debugging",
                "friction_counts": {"tool_error": 2},
                "friction_detail": "Tooling kept failing mid-session.",
            },
        )

    easy_repo = (
        db_session.query(GitRepository).filter(GitRepository.full_name == "acme/easy-project").one()
    )
    easy_repo.ai_readiness_score = 90.0
    easy_repo.ai_readiness_checked_at = easy_repo.created_at

    hard_repo = (
        db_session.query(GitRepository).filter(GitRepository.full_name == "acme/hard-project").one()
    )
    hard_repo.ai_readiness_score = 35.0
    hard_repo.ai_readiness_checked_at = hard_repo.created_at
    db_session.flush()

    response = client.get("/api/v1/analytics/projects/comparison", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["compared_projects"] == 2
    assert data["easiest_projects"][0]["project_name"] == "easy-project"
    assert data["hardest_projects"][0]["project_name"] == "hard-project"
    assert data["easiest_projects"][0]["dominant_agent_type"] == "claude_code"
    assert data["hardest_projects"][0]["dominant_agent_type"] == "cursor"
    assert data["easiest_projects"][0]["friction_rate"] == 0.0
    assert (
        data["easiest_projects"][0]["effectiveness_score"]
        > data["hardest_projects"][0]["effectiveness_score"]
    )


def test_activity_heatmap(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(client, api_key, started_at="2025-06-10T14:00:00")  # Tuesday 14:00
    _ingest_session(client, api_key, started_at="2025-06-10T14:30:00")  # Tuesday 14:00

    r = client.get("/api/v1/analytics/activity-heatmap", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["cells"]) >= 1
    assert data["max_count"] >= 2
    # Find the Tuesday 14:00 cell
    tuesday_14 = next((c for c in data["cells"] if c["day_of_week"] == 1 and c["hour"] == 14), None)
    assert tuesday_14 is not None
    assert tuesday_14["count"] >= 2


def test_productivity_excludes_cursor_sessions_without_model_usage_from_avg_cost_per_session(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1_000,
                "output_tokens": 500,
            }
        ],
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        model_usages=[],
    )

    response = client.get("/api/v1/analytics/productivity", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total_cost"] > 0
    assert data["avg_cost_per_session"] == data["total_cost"]


def test_productivity_cost_per_success_requires_measured_cost_sessions(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1_000,
                "output_tokens": 500,
            }
        ],
        facets={"outcome": "success"},
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        facets={"outcome": "success"},
    )

    response = client.get("/api/v1/analytics/productivity", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total_cost"] > 0
    assert data["cost_per_successful_outcome"] == data["total_cost"]


def test_engineer_benchmarks_exclude_sessions_without_supported_model_telemetry_from_token_totals(
    client, db_session, admin_headers
):
    import secrets

    import bcrypt

    from primer.common.models import Engineer, Team

    team = Team(name="Benchmark Token Safety")
    db_session.add(team)
    db_session.flush()

    def _create_engineer(name: str, email: str):
        raw_key = f"primer_{secrets.token_urlsafe(32)}"
        hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
        engineer = Engineer(
            name=name,
            email=email,
            team_id=team.id,
            api_key_hash=hashed,
        )
        db_session.add(engineer)
        db_session.flush()
        return engineer, raw_key

    _eng1, key1 = _create_engineer("Alice Safe", "alice-safe@example.com")
    _eng2, key2 = _create_engineer("Bob Partial", "bob-partial@example.com")

    _ingest_session(
        client,
        key1,
        started_at="2025-05-01T10:00:00",
        agent_type="claude_code",
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1000,
                "output_tokens": 500,
            }
        ],
        facets={"outcome": "success"},
    )
    _ingest_session(
        client,
        key2,
        started_at="2025-05-01T11:00:00",
        agent_type="cursor",
        model_usages=[],
        facets={"outcome": "partial"},
    )

    response = client.get(
        f"/api/v1/analytics/engineers/benchmarks?team_id={team.id}&start_date=2025-05-01T00:00:00&end_date=2025-05-02T00:00:00",
        headers=admin_headers,
    )
    assert response.status_code == 200

    data = response.json()
    alice = next(e for e in data["engineers"] if e["name"] == "Alice Safe")
    bob = next(e for e in data["engineers"] if e["name"] == "Bob Partial")
    assert alice["total_tokens"] == 1500
    assert bob["total_tokens"] == 0
    assert data["benchmark"]["team_avg_tokens"] == 750.0


def test_bottlenecks_include_cursor_facets_when_present(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        agent_type="claude_code",
        project_name="supported-project",
        started_at="2025-06-01T10:00:00",
        facets={
            "outcome": "failure",
            "friction_counts": {"tool_error": 1},
            "friction_detail": "Supported bottleneck",
        },
    )
    _ingest_session(
        client,
        api_key,
        agent_type="cursor",
        project_name="cursor-project",
        started_at="2025-06-01T11:00:00",
        facets={
            "outcome": "failure",
            "friction_counts": {"tool_error": 5},
            "friction_detail": "Unsupported cursor bottleneck",
        },
    )

    response = client.get("/api/v1/analytics/bottlenecks", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total_sessions_analyzed"] == 2
    assert data["sessions_with_any_friction"] == 2
    assert data["overall_friction_rate"] == 1.0
    impact = next(
        item for item in data["friction_impacts"] if item["friction_type"] == "tool_error"
    )
    assert impact["occurrence_count"] == 6
    supported_project = next(
        item for item in data["project_friction"] if item["project_name"] == "supported-project"
    )
    cursor_project = next(
        item for item in data["project_friction"] if item["project_name"] == "cursor-project"
    )
    assert supported_project["total_friction_count"] == 1
    assert cursor_project["total_friction_count"] == 5


def test_overview_with_trends(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        started_at="2025-01-15T10:00:00",
        facets={"outcome": "success"},
    )
    _ingest_session(
        client,
        api_key,
        started_at="2025-01-20T10:00:00",
        facets={"outcome": "failure"},
    )

    r = client.get(
        "/api/v1/analytics/overview?start_date=2025-01-01T00:00:00&end_date=2025-01-31T23:59:59",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success_rate"] is not None
    assert 0 <= data["success_rate"] <= 1


def test_daily_stats_success_rate(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        started_at="2025-05-01T10:00:00",
        facets={"outcome": "success"},
    )
    _ingest_session(
        client,
        api_key,
        started_at="2025-05-01T14:00:00",
        facets={"outcome": "failure"},
    )

    r = client.get(
        "/api/v1/analytics/daily?start_date=2025-05-01T00:00:00&end_date=2025-05-01T23:59:59",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    day = data[0]
    assert day["success_rate"] is not None
    assert day["success_rate"] == 0.5


def test_sessions_filter_by_project(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(client, api_key, project_name="filter-proj-a")
    _ingest_session(client, api_key, project_name="filter-proj-b")

    r = client.get(
        "/api/v1/sessions?project_name=filter-proj-a",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()["items"]
    assert len(data) >= 1
    assert all(s["project_name"] == "filter-proj-a" for s in data)
