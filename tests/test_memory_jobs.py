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
    # The enqueue guard also requires an Anthropic key (no point extracting with
    # no LLM to call). Set it explicitly so the test doesn't depend on ambient
    # config — CI has no key, which is why this silently passed only locally.
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
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


def test_backfill_memory_processes_newest_first_with_limit(db_session, monkeypatch):
    from datetime import datetime

    import primer.server.services.memory_extraction_service as mes
    from primer.common.models import Engineer, GitRepository
    from primer.common.models import Session as SessionModel

    monkeypatch.setattr(settings, "memory_enabled", True)
    monkeypatch.setattr(settings, "redaction_enabled", True)
    monkeypatch.setattr(settings, "anthropic_api_key", "k")
    eng = Engineer(name="B", email="b@x.io")
    repo = GitRepository(full_name="acme/bf")
    db_session.add_all([eng, repo])
    db_session.flush()
    for i in range(4):
        db_session.add(
            SessionModel(
                id=f"bf-{i}",
                engineer_id=eng.id,
                repository_id=repo.id,
                tool_call_count=10,
                started_at=datetime(2026, 5, 1 + i),
            )
        )
    db_session.commit()

    processed = []
    monkeypatch.setattr(mes, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(
        mes, "extract_memory_for_session", lambda sid: processed.append(sid) or "done"
    )

    result = mes.backfill_memory(limit=2)
    assert result["processed"] == 2
    assert processed == ["bf-3", "bf-2"]  # newest-first


def test_backfill_memory_scoped_to_repository(db_session, monkeypatch):
    import primer.server.services.memory_extraction_service as mes
    from primer.common.models import Engineer, GitRepository
    from primer.common.models import Session as SessionModel

    monkeypatch.setattr(settings, "memory_enabled", True)
    monkeypatch.setattr(settings, "redaction_enabled", True)
    monkeypatch.setattr(settings, "anthropic_api_key", "k")
    eng = Engineer(name="R", email="r@x.io")
    repo_a = GitRepository(full_name="acme/a")
    repo_b = GitRepository(full_name="acme/b")
    db_session.add_all([eng, repo_a, repo_b])
    db_session.flush()
    db_session.add(
        SessionModel(id="a-1", engineer_id=eng.id, repository_id=repo_a.id, tool_call_count=10)
    )
    db_session.add(
        SessionModel(id="b-1", engineer_id=eng.id, repository_id=repo_b.id, tool_call_count=10)
    )
    db_session.commit()
    processed = []
    monkeypatch.setattr(mes, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(
        mes, "extract_memory_for_session", lambda sid: processed.append(sid) or "done"
    )
    mes.backfill_memory(repository_id=repo_a.id, limit=10)
    assert processed == ["a-1"]  # only repo_a's session, not b-1


def test_backfill_excludes_passively_extracted_but_includes_remember_only(db_session, monkeypatch):
    # A session already passively extracted (transcript_citation evidence) is
    # excluded; a session with only an explicit remember (explicit_remember
    # evidence) is still eligible for passive backfill — the two are complementary.
    import primer.server.services.memory_extraction_service as mes
    from primer.common.models import (
        Engineer,
        GitRepository,
        MemoryEntry,
        MemoryEvidence,
        MemoryScope,
    )
    from primer.common.models import Session as SessionModel

    monkeypatch.setattr(settings, "memory_enabled", True)
    monkeypatch.setattr(settings, "redaction_enabled", True)
    monkeypatch.setattr(settings, "anthropic_api_key", "k")
    eng = Engineer(name="R", email="rr@x.io")
    repo = GitRepository(full_name="acme/c")
    db_session.add_all([eng, repo])
    db_session.flush()
    scope = MemoryScope(kind="project", name="acme/c", repository_id=repo.id)
    db_session.add(scope)
    db_session.flush()
    # passively-extracted session -> has transcript_citation evidence
    db_session.add(
        SessionModel(id="passive-1", engineer_id=eng.id, repository_id=repo.id, tool_call_count=10)
    )
    # remember-only session -> has only explicit_remember evidence
    db_session.add(
        SessionModel(id="remember-1", engineer_id=eng.id, repository_id=repo.id, tool_call_count=10)
    )
    entry = MemoryEntry(
        scope_id=scope.id, kind="project_fact", title="t", body="b", content_hash="h"
    )
    db_session.add(entry)
    db_session.flush()
    db_session.add(
        MemoryEvidence(
            memory_id=entry.id, evidence_kind="transcript_citation", session_id="passive-1"
        )
    )
    db_session.add(
        MemoryEvidence(
            memory_id=entry.id, evidence_kind="explicit_remember", session_id="remember-1"
        )
    )
    db_session.commit()

    processed = []
    monkeypatch.setattr(mes, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(
        mes, "extract_memory_for_session", lambda sid: processed.append(sid) or "done"
    )
    mes.backfill_memory(repository_id=repo.id, limit=10)
    assert processed == ["remember-1"]  # passive-1 excluded, remember-1 still eligible


def test_backfill_skips_sessions_without_repository(db_session, monkeypatch):
    import primer.server.services.memory_extraction_service as mes
    from primer.common.models import Engineer
    from primer.common.models import Session as SessionModel

    monkeypatch.setattr(settings, "memory_enabled", True)
    monkeypatch.setattr(settings, "redaction_enabled", True)
    monkeypatch.setattr(settings, "anthropic_api_key", "k")
    eng = Engineer(name="C", email="cc@x.io")
    db_session.add(eng)
    db_session.flush()
    db_session.add(SessionModel(id="norepo-1", engineer_id=eng.id, tool_call_count=10))
    db_session.commit()

    monkeypatch.setattr(mes, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    called = []
    monkeypatch.setattr(mes, "extract_memory_for_session", lambda sid: called.append(sid))

    result = mes.backfill_memory(limit=10)
    assert result["processed"] == 0
    assert called == []
