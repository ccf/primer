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


def _create_engineer_with_key(db_session, *, team_name: str, name: str, email: str):
    raw_key = f"primer_{secrets.token_urlsafe(16)}"
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()

    team = Team(name=team_name)
    db_session.add(team)
    db_session.flush()

    engineer = Engineer(name=name, email=email, team_id=team.id, api_key_hash=hashed)
    db_session.add(engineer)
    db_session.flush()

    return engineer, raw_key


def test_recommendation_low_facet_coverage(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    # >10 sessions, most without facets -> low coverage recommendation
    for _ in range(11):
        _ingest_session(client, api_key)

    r = client.get("/api/v1/analytics/recommendations", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert any(rec["category"] == "data_quality" for rec in data)


def test_recommendation_surfaces_measurement_integrity_evidence(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key

    for idx in range(11):
        _ingest_session(
            client,
            api_key,
            session_id=str(uuid.uuid4()),
            messages=[
                {"ordinal": 0, "role": "human", "content_text": f"Investigate issue {idx}"},
                {"ordinal": 1, "role": "assistant", "content_text": "Looking into it."},
            ],
            facets={
                "underlying_goal": "Improve measurement integrity",
                "goal_categories": ["fix_bug"],
                "outcome": "success",
                "confidence_score": 0.4 if idx < 8 else 0.95,
            },
        )

    r = client.get("/api/v1/analytics/recommendations", headers=admin_headers)
    assert r.status_code == 200

    data = r.json()
    rec = next(rec for rec in data if rec["category"] == "data_quality")
    assert rec["evidence"]["facet_coverage_pct"] == 100.0
    assert rec["evidence"]["transcript_coverage_pct"] == 100.0
    assert rec["evidence"]["low_confidence_sessions"] == 8
    assert rec["evidence"]["remaining_legacy_rows"] == 0


def test_recommendation_surfaces_missing_confidence_sessions_in_evidence_and_description(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key

    for idx in range(11):
        _ingest_session(
            client,
            api_key,
            session_id=str(uuid.uuid4()),
            messages=[
                {
                    "ordinal": 0,
                    "role": "human",
                    "content_text": f"Investigate missing confidence {idx}",
                },
                {"ordinal": 1, "role": "assistant", "content_text": "Looking into it."},
            ],
            facets={
                "underlying_goal": "Improve measurement integrity",
                "goal_categories": ["fix_bug"],
                "outcome": "success",
                "confidence_score": None if idx < 3 else 0.95,
            },
        )

    r = client.get("/api/v1/analytics/recommendations", headers=admin_headers)
    assert r.status_code == 200

    data = r.json()
    rec = next(rec for rec in data if rec["category"] == "data_quality")
    assert rec["evidence"]["facet_coverage_pct"] == 100.0
    assert rec["evidence"]["missing_confidence_sessions"] == 3
    assert "missing confidence" in rec["description"]


def test_recommendation_scopes_measurement_integrity_evidence_by_team(
    client, engineer_with_key, admin_headers, db_session
):
    eng_a, api_key_a = engineer_with_key
    _eng_b, api_key_b = _create_engineer_with_key(
        db_session,
        team_name="Other Team",
        name="Other Engineer",
        email="other@example.com",
    )

    for idx in range(11):
        _ingest_session(
            client,
            api_key_a,
            session_id=str(uuid.uuid4()),
            messages=[
                {"ordinal": 0, "role": "human", "content_text": f"Scoped team A issue {idx}"},
                {"ordinal": 1, "role": "assistant", "content_text": "Looking into it."},
            ],
            facets={
                "goal_categories": ["fix_bug"],
                "outcome": "success",
                "confidence_score": 0.4 if idx < 2 else 0.95,
            },
        )

    for idx in range(11):
        _ingest_session(
            client,
            api_key_b,
            session_id=str(uuid.uuid4()),
            messages=[
                {"ordinal": 0, "role": "human", "content_text": f"Scoped team B issue {idx}"},
                {"ordinal": 1, "role": "assistant", "content_text": "Looking into it."},
            ],
            facets={
                "goal_categories": ["fix_bug"],
                "outcome": "success",
                "confidence_score": 0.4 if idx < 8 else 0.95,
            },
        )

    r = client.get(
        f"/api/v1/analytics/recommendations?team_id={eng_a.team_id}",
        headers=admin_headers,
    )
    assert r.status_code == 200

    data = r.json()
    rec = next(rec for rec in data if rec["category"] == "data_quality")
    assert rec["evidence"]["total_sessions"] == 11
    assert rec["evidence"]["low_confidence_sessions"] == 2
    assert rec["evidence"]["facet_coverage_pct"] == 100.0
    assert rec["evidence"]["transcript_coverage_pct"] == 100.0
    assert rec["evidence"]["remaining_legacy_rows"] == 0


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
