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


def test_recommendation_low_facet_coverage(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    # >10 sessions, most without facets -> low coverage recommendation
    for _ in range(11):
        _ingest_session(client, api_key)

    r = client.get("/api/v1/analytics/recommendations", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert any(rec["category"] == "data_quality" for rec in data)


def test_recommendation_high_token_usage(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    # >5 sessions with high tokens and duration -> cost recommendation
    for _ in range(6):
        _ingest_session(
            client,
            api_key,
            input_tokens=400_000,
            output_tokens=200_000,
            duration_seconds=300.0,
        )

    r = client.get("/api/v1/analytics/recommendations", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert any(rec["category"] == "cost" for rec in data)


def test_recommendation_tool_over_reliance(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    # Sessions where one tool dominates -> workflow recommendation
    for _ in range(3):
        _ingest_session(
            client,
            api_key,
            tool_usages=[
                {"tool_name": "Read", "call_count": 100},
                {"tool_name": "Edit", "call_count": 5},
                {"tool_name": "Bash", "call_count": 3},
            ],
        )

    r = client.get("/api/v1/analytics/recommendations", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert any(rec["category"] == "workflow" for rec in data)
