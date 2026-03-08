import uuid

import pytest

from primer.common.models import Session as SessionModel
from primer.common.models import SessionFacets
from primer.common.schemas import SessionFacetsPayload
from primer.server.services.ingest_service import upsert_facets


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_team(client, admin_headers):
    r = client.post("/api/v1/teams", json={"name": "Alpha"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Alpha"


def test_create_engineer(client, admin_headers):
    r = client.post(
        "/api/v1/engineers", json={"name": "Eve", "email": "eve@co.com"}, headers=admin_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert "api_key" in data
    assert data["engineer"]["email"] == "eve@co.com"


def test_ingest_session(client, engineer_with_key):
    _eng, api_key = engineer_with_key
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
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "input_tokens": 1000,
                "output_tokens": 500,
            },
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


def test_ingest_session_normalizes_legacy_facet_payload(client, engineer_with_key, db_session):
    _eng, api_key = engineer_with_key
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
        "facets": {
            "underlying_goal": "Fix a bug",
            "goal_categories": {"fix_bug": 1, "testing": 1},
            "outcome": "mostly_achieved",
            "brief_summary": "Made progress and added coverage",
        },
    }
    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 200

    stored = db_session.query(SessionFacets).filter(SessionFacets.session_id == session_id).one()
    assert stored.goal_categories == ["fix_bug", "testing"]
    assert stored.outcome == "partial"


def test_ingest_session_upsert(client, engineer_with_key):
    _eng, api_key = engineer_with_key
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
    _eng, api_key = engineer_with_key
    sessions = [
        {"session_id": str(uuid.uuid4()), "api_key": api_key, "message_count": i} for i in range(3)
    ]
    r = client.post("/api/v1/ingest/bulk", json={"api_key": api_key, "sessions": sessions})
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 3
    assert all(res["status"] == "ok" for res in data["results"])


def test_ingest_invalid_key(client):
    r = client.post(
        "/api/v1/ingest/session",
        json={
            "session_id": "fake",
            "api_key": "bad_key",
        },
    )
    assert r.status_code == 401


def test_upsert_facets_normalizes_legacy_values_at_write_boundary(db_session, engineer_with_key):
    engineer, _api_key = engineer_with_key
    session_id = str(uuid.uuid4())
    db_session.add(SessionModel(id=session_id, engineer_id=engineer.id))
    db_session.flush()

    facets = SessionFacetsPayload.model_construct(
        underlying_goal="Fix a bug",
        goal_categories={"fix_bug": 1, "testing": 1},
        outcome="mostly_achieved",
        brief_summary="Made progress and added coverage",
    )

    upsert_facets(db_session, session_id, facets)

    stored = db_session.query(SessionFacets).filter(SessionFacets.session_id == session_id).one()
    assert stored.goal_categories == ["fix_bug", "testing"]
    assert stored.outcome == "partial"


def test_upsert_facets_rejects_unknown_outcome_at_write_boundary(db_session, engineer_with_key):
    engineer, _api_key = engineer_with_key
    session_id = str(uuid.uuid4())
    db_session.add(SessionModel(id=session_id, engineer_id=engineer.id))
    db_session.flush()

    facets = SessionFacetsPayload.model_construct(
        underlying_goal="Fix a bug",
        goal_categories=["fix_bug"],
        outcome="unexpected_outcome",
        brief_summary="Bad outcome value",
    )

    with pytest.raises(ValueError, match="outcome"):
        upsert_facets(db_session, session_id, facets)

    stored = db_session.query(SessionFacets).filter(SessionFacets.session_id == session_id).all()
    assert stored == []


def test_upsert_facets_rejects_scalar_goal_categories_at_write_boundary(
    db_session, engineer_with_key
):
    engineer, _api_key = engineer_with_key
    session_id = str(uuid.uuid4())
    db_session.add(SessionModel(id=session_id, engineer_id=engineer.id))
    db_session.flush()

    facets = SessionFacetsPayload.model_construct(
        underlying_goal="Fix a bug",
        goal_categories="fix_bug",
        outcome="success",
        brief_summary="Bad goal categories value",
    )

    with pytest.raises(ValueError, match="goal_categories"):
        upsert_facets(db_session, session_id, facets)

    stored = db_session.query(SessionFacets).filter(SessionFacets.session_id == session_id).all()
    assert stored == []


def test_upsert_facets_rejects_mixed_goal_category_list_at_write_boundary(
    db_session, engineer_with_key
):
    engineer, _api_key = engineer_with_key
    session_id = str(uuid.uuid4())
    db_session.add(SessionModel(id=session_id, engineer_id=engineer.id))
    db_session.flush()

    facets = SessionFacetsPayload.model_construct(
        underlying_goal="Fix a bug",
        goal_categories=["fix_bug", 3],
        outcome="success",
        brief_summary="Mixed goal categories value",
    )

    with pytest.raises(ValueError, match="goal_categories"):
        upsert_facets(db_session, session_id, facets)

    stored = db_session.query(SessionFacets).filter(SessionFacets.session_id == session_id).all()
    assert stored == []


def test_ingest_facets_success(client, engineer_with_key):
    _eng, api_key = engineer_with_key
    session_id = str(uuid.uuid4())
    # First ingest a session
    payload = {
        "session_id": session_id,
        "api_key": api_key,
        "message_count": 5,
    }
    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 200

    # Now ingest facets for that session
    r2 = client.post(
        f"/api/v1/ingest/facets/{session_id}",
        json={"outcome": "success", "brief_summary": "All good"},
        headers={"x-api-key": api_key},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "ok"


def test_ingest_facets_session_not_found(client, engineer_with_key):
    _eng, api_key = engineer_with_key
    r = client.post(
        "/api/v1/ingest/facets/nonexistent-session",
        json={"outcome": "success"},
        headers={"x-api-key": api_key},
    )
    assert r.status_code == 404


def test_ingest_facets_wrong_engineer(client, engineer_with_key, db_session):
    import secrets

    import bcrypt

    from primer.common.models import Engineer

    _eng1, api_key1 = engineer_with_key

    # Create a second engineer
    raw_key2 = f"primer_{secrets.token_urlsafe(32)}"
    hashed2 = bcrypt.hashpw(raw_key2.encode(), bcrypt.gensalt()).decode()
    eng2 = Engineer(
        name="Other", email=f"other-{uuid.uuid4().hex[:8]}@co.com", api_key_hash=hashed2
    )
    db_session.add(eng2)
    db_session.flush()

    # Ingest a session as engineer 1
    session_id = str(uuid.uuid4())
    r = client.post(
        "/api/v1/ingest/session",
        json={"session_id": session_id, "api_key": api_key1, "message_count": 1},
    )
    assert r.status_code == 200

    # Try to ingest facets as engineer 2 -> 403
    r2 = client.post(
        f"/api/v1/ingest/facets/{session_id}",
        json={"outcome": "success"},
        headers={"x-api-key": raw_key2},
    )
    assert r2.status_code == 403
