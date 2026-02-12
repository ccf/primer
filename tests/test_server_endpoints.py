import uuid

from primer.common.database import get_db


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


def test_overview_with_team_filter(client, engineer_with_key, admin_headers):
    eng, api_key = engineer_with_key
    _ingest_session(client, api_key)

    r = client.get(
        "/api/v1/analytics/overview",
        headers=admin_headers,
        params={"team_id": eng.team_id},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_sessions"] >= 1


def test_tool_rankings_with_team_filter(client, engineer_with_key, admin_headers):
    eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        tool_usages=[{"tool_name": "Read", "call_count": 10}],
    )

    r = client.get(
        "/api/v1/analytics/tools",
        headers=admin_headers,
        params={"team_id": eng.team_id},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1


def test_friction_with_team_filter(client, engineer_with_key, admin_headers):
    eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        facets={
            "friction_counts": {"tool_error": 2},
            "friction_detail": "Something broke",
        },
    )

    r = client.get(
        "/api/v1/analytics/friction",
        headers=admin_headers,
        params={"team_id": eng.team_id},
    )
    assert r.status_code == 200


def test_list_sessions_filter_engineer(client, engineer_with_key, admin_headers):
    eng, api_key = engineer_with_key
    _ingest_session(client, api_key)

    r = client.get(
        "/api/v1/sessions",
        headers=admin_headers,
        params={"engineer_id": eng.id},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert all(s["engineer_id"] == eng.id for s in data)


def test_list_sessions_filter_dates(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        started_at="2025-01-15T10:00:00",
    )

    r = client.get(
        "/api/v1/sessions",
        headers=admin_headers,
        params={"start_date": "2025-01-01T00:00:00", "end_date": "2025-12-31T23:59:59"},
    )
    assert r.status_code == 200


def test_session_not_found(client, admin_headers):
    r = client.get("/api/v1/sessions/nonexistent-id", headers=admin_headers)
    assert r.status_code == 404


def test_create_engineer_duplicate_email(client, admin_headers):
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    r1 = client.post(
        "/api/v1/engineers",
        json={"name": "First", "email": email},
        headers=admin_headers,
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/api/v1/engineers",
        json={"name": "Second", "email": email},
        headers=admin_headers,
    )
    assert r2.status_code == 409


def test_engineer_sessions_not_found(client, admin_headers):
    r = client.get("/api/v1/engineers/nonexistent-id/sessions", headers=admin_headers)
    assert r.status_code == 404


def test_create_team_duplicate_name(client, admin_headers):
    name = f"Team-{uuid.uuid4().hex[:8]}"
    r1 = client.post("/api/v1/teams", json={"name": name}, headers=admin_headers)
    assert r1.status_code == 200

    r2 = client.post("/api/v1/teams", json={"name": name}, headers=admin_headers)
    assert r2.status_code == 409


def test_get_db_generator():
    """Test that get_db() yields a session and closes it."""
    import contextlib

    gen = get_db()
    session = next(gen)
    assert session is not None
    with contextlib.suppress(StopIteration):
        gen.send(None)
