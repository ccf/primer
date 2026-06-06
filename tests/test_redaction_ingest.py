"""Integration tests: redaction at the server ingest chokepoint."""

import uuid

from primer.common.config import settings
from primer.common.models import BackgroundJob, SessionMessage
from primer.common.models import Session as SessionModel


def _secret_session_payload(api_key: str) -> dict:
    return {
        "session_id": str(uuid.uuid4()),
        "api_key": api_key,
        "agent_type": "claude_code",
        "first_prompt": "configure sk-ant-api03-AbCdEf123456789012345 now",
        "message_count": 1,
        "messages": [
            {
                "ordinal": 0,
                "role": "human",
                "content_text": "token ghp_abcdefghijklmnopqrstuvwxyz0123456789AB",
            }
        ],
    }


def test_sync_ingest_stores_redacted_messages(client, engineer_with_key, db_session):
    _engineer, api_key = engineer_with_key
    payload = _secret_session_payload(api_key)

    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 200

    session = db_session.query(SessionModel).filter(SessionModel.id == payload["session_id"]).one()
    assert "sk-ant-api03" not in (session.first_prompt or "")
    assert "[REDACTED:anthropic-key]" in session.first_prompt

    msg = (
        db_session.query(SessionMessage)
        .filter(SessionMessage.session_id == payload["session_id"])
        .one()
    )
    assert "ghp_" not in (msg.content_text or "")


def test_async_ingest_job_payload_is_redacted(client, engineer_with_key, db_session, monkeypatch):
    """The background_jobs table must never contain unredacted secrets."""
    monkeypatch.setattr(settings, "background_jobs_enabled", True)
    _engineer, api_key = engineer_with_key
    payload = _secret_session_payload(api_key)

    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 202

    job = (
        db_session.query(BackgroundJob)
        .filter(BackgroundJob.job_type == "session_ingest")
        .order_by(BackgroundJob.enqueued_at.desc())
        .first()
    )
    assert job is not None
    serialized = str(job.payload)
    assert "sk-ant-api03" not in serialized
    assert "ghp_" not in serialized


def test_bulk_ingest_stores_redacted_messages(client, engineer_with_key, db_session):
    _engineer, api_key = engineer_with_key
    payload = _secret_session_payload(api_key)

    r = client.post("/api/v1/ingest/bulk", json={"api_key": api_key, "sessions": [payload]})
    assert r.status_code == 200

    session = db_session.query(SessionModel).filter(SessionModel.id == payload["session_id"]).one()
    assert "sk-ant-api03" not in (session.first_prompt or "")


def test_redaction_disabled_passes_through(client, engineer_with_key, db_session, monkeypatch):
    monkeypatch.setattr(settings, "redaction_enabled", False)
    _engineer, api_key = engineer_with_key
    payload = _secret_session_payload(api_key)

    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 200

    session = db_session.query(SessionModel).filter(SessionModel.id == payload["session_id"]).one()
    assert "sk-ant-api03" in session.first_prompt


def test_redaction_failure_strips_content_not_500(
    client, engineer_with_key, db_session, monkeypatch
):
    """A redaction crash must not 500 or persist unredacted text."""
    import primer.server.routers.ingest as ingest_module

    def _boom(*args, **kwargs):
        raise RuntimeError("redaction exploded")

    monkeypatch.setattr(ingest_module, "redact_ingest_dict", _boom)
    _engineer, api_key = engineer_with_key
    payload = _secret_session_payload(api_key)

    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 200

    session = db_session.query(SessionModel).filter(SessionModel.id == payload["session_id"]).one()
    assert session.first_prompt is None
    assert session.message_count == 1  # metrics survive
    msgs = (
        db_session.query(SessionMessage)
        .filter(SessionMessage.session_id == payload["session_id"])
        .all()
    )
    assert msgs == []
