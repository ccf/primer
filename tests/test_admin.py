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


def test_system_stats(client, admin_headers, engineer_with_key):
    _eng, api_key = engineer_with_key
    _ingest_session(client, api_key)

    r = client.get("/api/v1/admin/system-stats", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_engineers"] >= 1
    assert data["active_engineers"] >= 1
    assert data["total_teams"] >= 1
    assert data["total_sessions"] >= 1
    assert data["total_ingest_events"] >= 1
    assert "database_type" in data


def test_system_stats_requires_admin(client, engineer_with_key):
    _eng, api_key = engineer_with_key
    r = client.get("/api/v1/admin/system-stats", headers={"x-api-key": api_key})
    assert r.status_code == 403


def test_ingest_events(client, admin_headers, engineer_with_key):
    _eng, api_key = engineer_with_key
    _ingest_session(client, api_key)

    r = client.get("/api/v1/admin/ingest-events", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()["items"]
    assert len(data) >= 1
    assert data[0]["status"] == "ok"


def test_ingest_events_filter_by_engineer(client, admin_headers, engineer_with_key):
    eng, api_key = engineer_with_key
    _ingest_session(client, api_key)

    r = client.get(f"/api/v1/admin/ingest-events?engineer_id={eng.id}", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()["items"]
    assert all(e["engineer_id"] == eng.id for e in data)


def test_deactivate_engineer(client, admin_headers, engineer_with_key):
    eng, _api_key = engineer_with_key

    r = client.delete(f"/api/v1/engineers/{eng.id}", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["is_active"] is False


def test_deactivate_not_found(client, admin_headers):
    r = client.delete("/api/v1/engineers/nonexistent", headers=admin_headers)
    assert r.status_code == 404


def test_rotate_api_key(client, admin_headers, engineer_with_key):
    eng, old_key = engineer_with_key

    r = client.post(f"/api/v1/engineers/{eng.id}/rotate-key", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "api_key" in data
    assert data["api_key"] != old_key
    assert data["api_key"].startswith("primer_")

    # New key should work for ingest
    r = client.post(
        "/api/v1/ingest/session",
        json={
            "session_id": str(uuid.uuid4()),
            "api_key": data["api_key"],
            "message_count": 1,
        },
    )
    assert r.status_code == 200


def test_update_team_name(client, admin_headers, engineer_with_key):
    eng, _api_key = engineer_with_key

    r = client.patch(
        f"/api/v1/teams/{eng.team_id}",
        json={"name": "Renamed Team"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed Team"


def test_update_team_duplicate_name(client, admin_headers, db_session):
    from primer.common.models import Team

    t1 = Team(name="Team Alpha")
    t2 = Team(name="Team Beta")
    db_session.add_all([t1, t2])
    db_session.flush()

    r = client.patch(
        f"/api/v1/teams/{t2.id}",
        json={"name": "Team Alpha"},
        headers=admin_headers,
    )
    assert r.status_code == 409
