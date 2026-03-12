import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from primer.common.models import Session as SessionModel
from primer.common.models import SessionChangeShape, SessionExecutionEvidence, SessionFacets
from primer.common.schemas import SessionFacetsPayload, SessionResponse
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


def test_ingest_session_accepts_cursor_agent_type_and_persists(
    client, engineer_with_key, db_session
):
    _eng, api_key = engineer_with_key
    session_id = str(uuid.uuid4())
    payload = {
        "session_id": session_id,
        "api_key": api_key,
        "agent_type": "cursor",
        "project_name": "cursor-project",
        "message_count": 2,
        "user_message_count": 1,
        "assistant_message_count": 1,
        "tool_call_count": 0,
        "input_tokens": 120,
        "output_tokens": 45,
        "primary_model": "gpt-4.1",
        "first_prompt": "Imported from Cursor",
        "messages": [
            {"ordinal": 0, "role": "human", "content_text": "Imported from Cursor"},
            {"ordinal": 1, "role": "assistant", "content_text": "Ready to help"},
        ],
    }

    r = client.post("/api/v1/ingest/session", json=payload)

    assert r.status_code == 200
    assert r.json() == {"status": "ok", "session_id": session_id, "created": True}

    stored = db_session.query(SessionModel).filter(SessionModel.id == session_id).one()
    assert stored.agent_type == "cursor"
    assert stored.project_name == "cursor-project"
    assert stored.message_count == 2
    assert stored.user_message_count == 1
    assert stored.assistant_message_count == 1
    assert stored.primary_model == "gpt-4.1"
    assert stored.first_prompt == "Imported from Cursor"
    assert stored.has_facets is False


def test_ingest_session_auto_extracts_facets_for_codex_transcripts(
    client, engineer_with_key, monkeypatch
):
    from primer.server.routers import ingest as ingest_router
    from primer.server.services import facet_extraction_service

    _eng, api_key = engineer_with_key
    session_id = str(uuid.uuid4())
    observed: list[tuple[str, list[dict]]] = []

    monkeypatch.setattr(ingest_router.settings, "facet_extraction_enabled", True)
    monkeypatch.setattr(ingest_router.settings, "anthropic_api_key", "test-key")

    def fake_extract_and_store_facets(target_session_id: str, messages: list[dict]) -> bool:
        observed.append((target_session_id, messages))
        return True

    monkeypatch.setattr(
        facet_extraction_service,
        "extract_and_store_facets",
        fake_extract_and_store_facets,
    )

    payload = {
        "session_id": session_id,
        "api_key": api_key,
        "agent_type": "codex_cli",
        "project_name": "codex-project",
        "message_count": 2,
        "user_message_count": 1,
        "assistant_message_count": 1,
        "messages": [
            {"ordinal": 0, "role": "human", "content_text": "Fix the sync bug"},
            {"ordinal": 1, "role": "assistant", "content_text": "I found the API limit issue"},
        ],
    }

    response = client.post("/api/v1/ingest/session", json=payload)

    assert response.status_code == 200
    assert len(observed) == 1
    observed_session_id, observed_messages = observed[0]
    assert observed_session_id == session_id
    assert [msg["content_text"] for msg in observed_messages] == [
        "Fix the sync bug",
        "I found the API limit issue",
    ]
    assert [msg["role"] for msg in observed_messages] == ["human", "assistant"]


def test_ingest_session_derives_execution_evidence_from_terminal_messages(
    client, engineer_with_key, db_session
):
    _eng, api_key = engineer_with_key
    session_id = str(uuid.uuid4())
    payload = {
        "session_id": session_id,
        "api_key": api_key,
        "project_name": "execution-project",
        "message_count": 7,
        "user_message_count": 1,
        "assistant_message_count": 4,
        "messages": [
            {
                "ordinal": 0,
                "role": "assistant",
                "tool_calls": [{"name": "Bash", "input_preview": '{"command":"pytest -q"}'}],
            },
            {
                "ordinal": 1,
                "role": "tool_result",
                "tool_results": [{"name": "Bash", "output_preview": "2 passed in 0.12s"}],
            },
            {
                "ordinal": 2,
                "role": "assistant",
                "tool_calls": [{"name": "Bash", "input_preview": '{"command":"ruff check ."}'}],
            },
            {
                "ordinal": 3,
                "role": "tool_result",
                "tool_results": [{"name": "Bash", "output_preview": "Found 1 error"}],
            },
            {
                "ordinal": 4,
                "role": "assistant",
                "tool_calls": [{"name": "Bash", "input_preview": '{"command":"npm run build"}'}],
            },
            {
                "ordinal": 5,
                "role": "tool_result",
                "tool_results": [
                    {"name": "Bash", "output_preview": "Build completed successfully"}
                ],
            },
            {
                "ordinal": 6,
                "role": "assistant",
                "tool_calls": [
                    {"name": "Bash", "input_preview": '{"command":"cargo check"}'},
                    {"name": "Write", "input_preview": '{"file_path":"src/auth.py"}'},
                    {"name": "Edit", "input_preview": '{"path":"src/auth.py"}'},
                ],
            },
        ],
        "commits": [
            {
                "sha": "abc123",
                "message": "Update auth flow",
                "files_changed": 2,
                "lines_added": 10,
                "lines_deleted": 2,
            }
        ],
    }

    response = client.post("/api/v1/ingest/session", json=payload)

    assert response.status_code == 200

    evidence = (
        db_session.query(SessionExecutionEvidence)
        .filter(SessionExecutionEvidence.session_id == session_id)
        .order_by(SessionExecutionEvidence.ordinal)
        .all()
    )

    assert [(row.evidence_type, row.status, row.command) for row in evidence] == [
        ("test", "passed", "pytest -q"),
        ("lint", "failed", "ruff check ."),
        ("build", "passed", "npm run build"),
        ("verification", "unknown", "cargo check"),
    ]
    assert evidence[0].output_preview == "2 passed in 0.12s"
    assert evidence[1].output_preview == "Found 1 error"

    change_shape = (
        db_session.query(SessionChangeShape)
        .filter(SessionChangeShape.session_id == session_id)
        .one()
    )
    assert change_shape.files_touched_count == 2
    assert change_shape.named_touched_files == ["src/auth.py"]
    assert change_shape.commit_files_changed == 2
    assert change_shape.lines_added == 10
    assert change_shape.lines_deleted == 2
    assert change_shape.edit_operations == 2
    assert change_shape.rewrite_indicator is True


def test_session_response_accepts_cursor_agent_type():
    response = SessionResponse(
        id=str(uuid.uuid4()),
        engineer_id=str(uuid.uuid4()),
        agent_type="cursor",
        project_path="/workspace/demo",
        project_name="demo",
        git_branch=None,
        agent_version="cursor-1.0.0",
        permission_mode=None,
        end_reason=None,
        started_at=datetime(2026, 3, 8, 10, 0, 0),
        ended_at=datetime(2026, 3, 8, 10, 5, 0),
        duration_seconds=300.0,
        message_count=2,
        user_message_count=1,
        assistant_message_count=1,
        tool_call_count=0,
        input_tokens=0,
        output_tokens=0,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        primary_model="gpt-4.1",
        first_prompt="Imported from Cursor",
        summary=None,
        has_facets=False,
        created_at=datetime(2026, 3, 8, 10, 5, 1),
    )

    assert response.agent_type == "cursor"


def test_session_response_rejects_unknown_agent_type():
    with pytest.raises(ValidationError):
        SessionResponse(
            id=str(uuid.uuid4()),
            engineer_id=str(uuid.uuid4()),
            agent_type="unknown_agent",
            project_path=None,
            project_name=None,
            git_branch=None,
            agent_version=None,
            permission_mode=None,
            end_reason=None,
            started_at=None,
            ended_at=None,
            duration_seconds=None,
            message_count=0,
            user_message_count=0,
            assistant_message_count=0,
            tool_call_count=0,
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            primary_model=None,
            first_prompt=None,
            summary=None,
            has_facets=False,
            created_at=datetime(2026, 3, 8, 10, 0, 0),
        )


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


def test_ingest_session_upsert_clears_related_rows_when_payload_lists_are_empty(
    client, engineer_with_key, db_session
):
    _eng, api_key = engineer_with_key
    session_id = str(uuid.uuid4())

    initial_payload = {
        "session_id": session_id,
        "api_key": api_key,
        "message_count": 2,
        "tool_usages": [{"tool_name": "Read", "call_count": 3}],
        "model_usages": [
            {
                "model_name": "claude-sonnet-4-20250514",
                "input_tokens": 100,
                "output_tokens": 50,
            }
        ],
        "messages": [
            {"ordinal": 0, "role": "human", "content_text": "hello"},
            {"ordinal": 1, "role": "assistant", "content_text": "hi"},
        ],
        "commits": [
            {
                "sha": "abc123",
                "message": "Initial commit",
                "author_name": "Test Engineer",
                "author_email": "test@example.com",
                "committed_at": datetime(2026, 3, 8, 12, 0, 0).isoformat(),
                "files_changed": 1,
                "lines_added": 10,
                "lines_deleted": 2,
            }
        ],
    }
    response = client.post("/api/v1/ingest/session", json=initial_payload)
    assert response.status_code == 200

    empty_payload = {
        "session_id": session_id,
        "api_key": api_key,
        "message_count": 0,
        "tool_usages": [],
        "model_usages": [],
        "messages": [],
        "commits": [],
    }
    response = client.post("/api/v1/ingest/session", json=empty_payload)
    assert response.status_code == 200
    assert response.json()["created"] is False

    stored = db_session.query(SessionModel).filter(SessionModel.id == session_id).one()
    assert stored.tool_usages == []
    assert stored.model_usages == []
    assert stored.messages == []
    assert stored.commits == []


def test_ingest_session_upsert_preserves_related_rows_when_payload_lists_are_omitted(
    client, engineer_with_key, db_session
):
    _eng, api_key = engineer_with_key
    session_id = str(uuid.uuid4())

    initial_payload = {
        "session_id": session_id,
        "api_key": api_key,
        "message_count": 2,
        "tool_usages": [{"tool_name": "Read", "call_count": 3}],
        "model_usages": [
            {
                "model_name": "claude-sonnet-4-20250514",
                "input_tokens": 100,
                "output_tokens": 50,
            }
        ],
        "messages": [
            {"ordinal": 0, "role": "human", "content_text": "hello"},
            {"ordinal": 1, "role": "assistant", "content_text": "hi"},
        ],
        "commits": [
            {
                "sha": "abc123",
                "message": "Initial commit",
                "author_name": "Test Engineer",
                "author_email": "test@example.com",
                "committed_at": datetime(2026, 3, 8, 12, 0, 0).isoformat(),
                "files_changed": 1,
                "lines_added": 10,
                "lines_deleted": 2,
            }
        ],
    }
    response = client.post("/api/v1/ingest/session", json=initial_payload)
    assert response.status_code == 200

    update_payload = {
        "session_id": session_id,
        "api_key": api_key,
        "message_count": 5,
    }
    response = client.post("/api/v1/ingest/session", json=update_payload)
    assert response.status_code == 200
    assert response.json()["created"] is False

    stored = db_session.query(SessionModel).filter(SessionModel.id == session_id).one()
    assert stored.message_count == 5
    assert [(usage.tool_name, usage.call_count) for usage in stored.tool_usages] == [("Read", 3)]
    assert [
        (usage.model_name, usage.input_tokens, usage.output_tokens) for usage in stored.model_usages
    ] == [("claude-sonnet-4-20250514", 100, 50)]
    assert [message.content_text for message in stored.messages] == ["hello", "hi"]
    assert [commit.commit_sha for commit in stored.commits] == ["abc123"]


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
