import uuid


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
    data = r.json()
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
