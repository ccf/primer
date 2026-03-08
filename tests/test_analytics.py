import uuid

from primer.common.models import SessionFacets


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
        facets={
            "outcome": "success",
            "session_type": "feature",
        },
    )
    _ingest_session(
        client,
        api_key,
        facets={
            "outcome": "success",
            "session_type": "debugging",
        },
    )
    _ingest_session(
        client,
        api_key,
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


def test_daily_stats_endpoint(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        started_at="2025-01-15T10:00:00",
        message_count=10,
        tool_call_count=5,
    )
    _ingest_session(
        client,
        api_key,
        started_at="2025-01-15T14:00:00",
        message_count=8,
        tool_call_count=3,
    )
    _ingest_session(
        client,
        api_key,
        started_at="2025-01-16T09:00:00",
        message_count=12,
        tool_call_count=7,
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
    sid = _ingest_session(client, api_key, project_name="my-project")

    r = client.get("/api/v1/sessions", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()["items"]
    assert any(s["id"] == sid for s in data)


def test_session_detail(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    sid = _ingest_session(
        client,
        api_key,
        tool_usages=[{"tool_name": "Read", "call_count": 5}],
        facets={"outcome": "success", "brief_summary": "Fixed it"},
    )

    r = client.get(f"/api/v1/sessions/{sid}", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == sid
    assert data["has_facets"] is True
    assert data["facets"]["outcome"] == "success"
    assert len(data["tool_usages"]) == 1


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
    _ingest_session(client, api_key, started_at="2025-01-10T10:00:00", message_count=5)
    _ingest_session(client, api_key, started_at="2025-01-20T10:00:00", message_count=10)
    _ingest_session(client, api_key, started_at="2025-02-01T10:00:00", message_count=15)

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
