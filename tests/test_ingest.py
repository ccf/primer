import uuid


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_team(client, admin_headers):
    r = client.post("/api/v1/teams", json={"name": "Alpha"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Alpha"


def test_create_engineer(client, admin_headers):
    r = client.post("/api/v1/engineers", json={"name": "Eve", "email": "eve@co.com"}, headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "api_key" in data
    assert data["engineer"]["email"] == "eve@co.com"


def test_ingest_session(client, engineer_with_key):
    eng, api_key = engineer_with_key
    session_id = str(uuid.uuid4())
    payload = {
        "session_id": session_id,
        "api_key": api_key,
        "project_name": "test-project",
        "message_count": 10,
        "user_message_count": 5,
        "assistant_message_count": 5,
        "tool_call_count": 3,
        "input_tokens": 1000,
        "output_tokens": 500,
        "primary_model": "claude-sonnet-4-5-20250929",
        "first_prompt": "Help me fix the bug",
        "tool_usages": [
            {"tool_name": "Read", "call_count": 5},
            {"tool_name": "Edit", "call_count": 2},
        ],
        "model_usages": [
            {"model_name": "claude-sonnet-4-5-20250929", "input_tokens": 1000, "output_tokens": 500},
        ],
        "facets": {
            "underlying_goal": "Fix a bug",
            "outcome": "success",
            "session_type": "debugging",
            "brief_summary": "Fixed the null pointer bug",
        },
    }
    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["session_id"] == session_id
    assert data["created"] is True


def test_ingest_session_upsert(client, engineer_with_key):
    eng, api_key = engineer_with_key
    session_id = str(uuid.uuid4())
    payload = {
        "session_id": session_id,
        "api_key": api_key,
        "message_count": 5,
    }
    r1 = client.post("/api/v1/ingest/session", json=payload)
    assert r1.json()["created"] is True

    # Upsert same session
    payload["message_count"] = 10
    r2 = client.post("/api/v1/ingest/session", json=payload)
    assert r2.json()["created"] is False


def test_ingest_bulk(client, engineer_with_key):
    eng, api_key = engineer_with_key
    sessions = [
        {"session_id": str(uuid.uuid4()), "api_key": api_key, "message_count": i}
        for i in range(3)
    ]
    r = client.post("/api/v1/ingest/bulk", json={"api_key": api_key, "sessions": sessions})
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 3
    assert all(res["status"] == "ok" for res in data["results"])


def test_ingest_invalid_key(client):
    r = client.post("/api/v1/ingest/session", json={
        "session_id": "fake",
        "api_key": "bad_key",
    })
    assert r.status_code == 401
