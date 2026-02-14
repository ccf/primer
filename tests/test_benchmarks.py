import secrets
import uuid

import bcrypt

from primer.common.models import Engineer, Team


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


def _create_engineer(db_session, team, name, email):
    raw_key = f"primer_{secrets.token_urlsafe(32)}"
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    eng = Engineer(name=name, email=email, team_id=team.id, api_key_hash=hashed)
    db_session.add(eng)
    db_session.flush()
    return eng, raw_key


def test_benchmarks_requires_team_lead(client, engineer_with_key):
    _eng, api_key = engineer_with_key
    r = client.get(
        "/api/v1/analytics/engineers/benchmarks",
        headers={"x-api-key": api_key},
    )
    assert r.status_code == 403


def test_benchmarks_empty(client, admin_headers):
    r = client.get("/api/v1/analytics/engineers/benchmarks", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["engineers"]) == 0


def test_benchmarks_multiple_engineers(client, db_session, admin_headers):
    team = Team(name="Benchmark Team")
    db_session.add(team)
    db_session.flush()

    _eng1, key1 = _create_engineer(db_session, team, "Alice", "alice@bench.com")
    _eng2, key2 = _create_engineer(db_session, team, "Bob", "bob@bench.com")

    # Alice: 3 sessions
    for i in range(3):
        _ingest_session(
            client,
            key1,
            started_at=f"2025-05-01T{10 + i}:00:00",
            model_usages=[
                {
                    "model_name": "claude-sonnet-4-5-20250929",
                    "input_tokens": 1000,
                    "output_tokens": 500,
                },
            ],
            facets={"outcome": "success"},
        )

    # Bob: 1 session
    _ingest_session(
        client,
        key2,
        started_at="2025-05-01T10:00:00",
        model_usages=[
            {"model_name": "claude-sonnet-4-5-20250929", "input_tokens": 500, "output_tokens": 250},
        ],
        facets={"outcome": "partial"},
    )

    r = client.get(
        f"/api/v1/analytics/engineers/benchmarks?team_id={team.id}&start_date=2025-05-01T00:00:00&end_date=2025-05-02T00:00:00",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["engineers"]) == 2
    assert data["benchmark"]["team_avg_sessions"] == 2.0

    # Alice should have higher percentile
    alice = next(e for e in data["engineers"] if e["name"] == "Alice")
    bob = next(e for e in data["engineers"] if e["name"] == "Bob")
    assert alice["percentile_sessions"] > bob["percentile_sessions"]
    assert alice["total_sessions"] == 3
    assert bob["total_sessions"] == 1

    # vs_team_avg should show Alice above and Bob below
    assert alice["vs_team_avg"]["sessions"] > 0
    assert bob["vs_team_avg"]["sessions"] < 0
