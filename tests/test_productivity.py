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


def test_productivity_empty(client, admin_headers):
    r = client.get("/api/v1/analytics/productivity", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_cost"] == 0
    assert data["adoption_rate"] == 0


def test_productivity_with_data(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        started_at="2025-06-01T10:00:00",
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1000,
                "output_tokens": 500,
            },
        ],
        facets={"outcome": "success"},
    )
    _ingest_session(
        client,
        api_key,
        started_at="2025-06-01T14:00:00",
        model_usages=[
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 2000,
                "output_tokens": 1000,
            },
        ],
        facets={"outcome": "partial"},
    )

    r = client.get(
        "/api/v1/analytics/productivity?start_date=2025-06-01T00:00:00&end_date=2025-06-02T00:00:00",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_cost"] > 0
    assert data["total_engineers_in_scope"] >= 1
    assert data["adoption_rate"] > 0
    assert data["cost_per_successful_outcome"] is not None
    assert data["estimated_time_saved_hours"] is not None


def test_productivity_adoption_rate(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(client, api_key, started_at="2025-07-01T10:00:00")

    r = client.get(
        "/api/v1/analytics/productivity?start_date=2025-07-01T00:00:00&end_date=2025-07-02T00:00:00",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["adoption_rate"] > 0
    assert data["sessions_per_engineer_per_day"] > 0


def test_productivity_rbac_engineer(client, engineer_with_key):
    _eng, api_key = engineer_with_key
    _ingest_session(client, api_key, started_at="2025-08-01T10:00:00")

    r = client.get(
        "/api/v1/analytics/productivity",
        headers={"x-api-key": api_key},
    )
    assert r.status_code == 200
