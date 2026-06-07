"""Memory job wiring: dispatch + post-ingest enqueue."""

from primer.common.config import settings
from primer.common.models import BackgroundJob
from primer.server.services.background_job_service import (
    JOB_TYPE_MEMORY_BACKFILL,
    JOB_TYPE_MEMORY_EXTRACTION,
    _run_job,
)


def test_job_type_constants_have_expected_values():
    assert JOB_TYPE_MEMORY_EXTRACTION == "memory_extract_session"
    assert JOB_TYPE_MEMORY_BACKFILL == "memory_backfill"


def test_memory_extraction_dispatch(monkeypatch):
    calls = {}

    def fake_extract(session_id):
        calls["session_id"] = session_id
        return "done"

    import primer.server.services.memory_extraction_service as mes

    monkeypatch.setattr(mes, "extract_memory_for_session", fake_extract)
    _run_job(None, JOB_TYPE_MEMORY_EXTRACTION, {"session_id": "s-1"})
    assert calls["session_id"] == "s-1"


def test_memory_extraction_dispatch_raises_on_failed(monkeypatch):
    import pytest

    import primer.server.services.memory_extraction_service as mes

    monkeypatch.setattr(mes, "extract_memory_for_session", lambda sid: "failed")
    with pytest.raises(RuntimeError):
        _run_job(None, JOB_TYPE_MEMORY_EXTRACTION, {"session_id": "s-2"})


def test_ingest_enqueues_memory_extraction(client, engineer_with_key, db_session, monkeypatch):
    monkeypatch.setattr(settings, "background_jobs_enabled", True)
    monkeypatch.setattr(settings, "memory_enabled", True)
    monkeypatch.setattr(settings, "redaction_enabled", True)
    _engineer, api_key = engineer_with_key

    r = client.post(
        "/api/v1/ingest/session",
        json={
            "session_id": "mem-job-1",
            "api_key": api_key,
            "agent_type": "claude_code",
            "message_count": 1,
        },
    )
    assert r.status_code == 202
    # The session_ingest job enqueues memory extraction when it RUNS, not at
    # HTTP time — so assert against the worker path: run the ingest job now.
    job = (
        db_session.query(BackgroundJob)
        .filter(BackgroundJob.job_type == "session_ingest")
        .order_by(BackgroundJob.enqueued_at.desc())
        .first()
    )
    from primer.server.services.ingest_service import process_session_ingest_job

    process_session_ingest_job(db_session, job.payload)
    mem_jobs = (
        db_session.query(BackgroundJob)
        .filter(BackgroundJob.job_type == JOB_TYPE_MEMORY_EXTRACTION)
        .all()
    )
    assert len(mem_jobs) == 1
    assert mem_jobs[0].payload["session_id"] == "mem-job-1"


def test_ingest_does_not_enqueue_when_memory_disabled(
    client, engineer_with_key, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "background_jobs_enabled", True)
    monkeypatch.setattr(settings, "memory_enabled", False)
    _engineer, api_key = engineer_with_key

    r = client.post(
        "/api/v1/ingest/session",
        json={
            "session_id": "mem-job-2",
            "api_key": api_key,
            "agent_type": "claude_code",
            "message_count": 1,
        },
    )
    assert r.status_code == 202
    job = (
        db_session.query(BackgroundJob)
        .filter(BackgroundJob.job_type == "session_ingest")
        .order_by(BackgroundJob.enqueued_at.desc())
        .first()
    )
    from primer.server.services.ingest_service import process_session_ingest_job

    process_session_ingest_job(db_session, job.payload)
    mem_jobs = (
        db_session.query(BackgroundJob)
        .filter(BackgroundJob.job_type == JOB_TYPE_MEMORY_EXTRACTION)
        .all()
    )
    assert mem_jobs == []
