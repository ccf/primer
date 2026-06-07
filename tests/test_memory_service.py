"""Tests for the memory store service layer (Plan 2a: scopes + sketches)."""

import pytest
import sqlalchemy.exc

from primer.common.config import settings
from primer.common.models import (
    GitRepository,
    MemoryEntry,
    MemoryEvent,
    MemoryEvidence,
    MemoryScope,
)
from primer.server.services.memory_service import (
    create_sketch,
    get_or_create_project_scope,
    memory_capture_active,
)


def test_memory_disabled_by_default():
    assert settings.memory_enabled is False
    assert memory_capture_active() is False


def test_memory_requires_redaction(monkeypatch):
    monkeypatch.setattr(settings, "memory_enabled", True)
    monkeypatch.setattr(settings, "redaction_enabled", False)
    assert memory_capture_active() is False


def test_memory_active_when_enabled_with_redaction(monkeypatch):
    monkeypatch.setattr(settings, "memory_enabled", True)
    monkeypatch.setattr(settings, "redaction_enabled", True)
    assert memory_capture_active() is True


def test_memory_models_roundtrip(db_session):
    repo = GitRepository(full_name="acme/widgets")
    db_session.add(repo)
    db_session.flush()

    scope = MemoryScope(kind="project", name="widgets", repository_id=repo.id)
    db_session.add(scope)
    db_session.flush()

    entry = MemoryEntry(
        scope_id=scope.id,
        kind="project_fact",
        title="Tests use SQLite in-memory",
        body="Tests use SQLite in-memory; Postgres is CI-only.",
        content_hash="a" * 64,
    )
    db_session.add(entry)
    db_session.flush()
    assert entry.status == "sketch"
    assert entry.export_status == "none"
    assert entry.confidence_score == 0.0
    assert entry.corroboration_count == 0

    evidence = MemoryEvidence(
        memory_id=entry.id,
        evidence_kind="transcript_citation",
        independent=True,
        payload={"excerpt": "pytest uses sqlite"},
    )
    event = MemoryEvent(memory_id=entry.id, event_kind="sketch_created", actor="system")
    db_session.add_all([evidence, event])
    db_session.flush()

    fetched = db_session.query(MemoryEntry).filter(MemoryEntry.id == entry.id).one()
    assert fetched.evidence[0].evidence_kind == "transcript_citation"
    assert fetched.events[0].event_kind == "sketch_created"
    assert fetched.scope.repository_id == repo.id


def test_memory_entry_unique_hash_per_scope(db_session):
    repo = GitRepository(full_name="acme/unique")
    db_session.add(repo)
    db_session.flush()
    scope = MemoryScope(kind="project", name="unique", repository_id=repo.id)
    db_session.add(scope)
    db_session.flush()

    db_session.add(
        MemoryEntry(scope_id=scope.id, kind="project_fact", title="t", body="b", content_hash="h1")
    )
    db_session.flush()
    db_session.add(
        MemoryEntry(
            scope_id=scope.id, kind="project_fact", title="t2", body="b2", content_hash="h1"
        )
    )
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db_session.flush()


def _repo_and_scope(db_session, full_name="acme/svc"):
    repo = GitRepository(full_name=full_name)
    db_session.add(repo)
    db_session.flush()
    return repo


def _engineer(db_session, email="m@x.io"):
    from primer.common.models import Engineer

    eng = Engineer(name="Mem", email=email)
    db_session.add(eng)
    db_session.flush()
    return eng


def test_get_or_create_project_scope_idempotent(db_session):
    repo = _repo_and_scope(db_session)
    s1 = get_or_create_project_scope(db_session, repo.id)
    s2 = get_or_create_project_scope(db_session, repo.id)
    assert s1.id == s2.id
    assert s1.kind == "project"
    assert s1.name == "acme/svc"


def test_create_sketch_persists_card_with_evidence_and_event(db_session):
    repo = _repo_and_scope(db_session)
    eng = _engineer(db_session)
    scope = get_or_create_project_scope(db_session, repo.id)

    entry = create_sketch(
        db_session,
        scope=scope,
        card={
            "kind": "project_fact",
            "title": "Tests use SQLite",
            "body": "Tests use SQLite in-memory; Postgres is CI-only.",
            "concepts": ["testing"],
            "files": ["tests/conftest.py"],
        },
        origin="passive_extraction",
        engineer_id=eng.id,
        session_id=None,
        citation={"excerpt": "conftest creates sqlite engine"},
    )
    assert entry is not None
    assert entry.status == "sketch"
    assert entry.origin == "passive_extraction"
    assert entry.created_by_engineer_id == eng.id
    assert len(entry.content_hash) == 64
    assert entry.evidence[0].evidence_kind == "transcript_citation"
    assert entry.evidence[0].engineer_id == eng.id
    assert entry.events[0].event_kind == "sketch_created"


def test_create_sketch_exact_duplicate_accretes_evidence(db_session):
    repo = _repo_and_scope(db_session)
    eng1 = _engineer(db_session, "a@x.io")
    eng2 = _engineer(db_session, "b@x.io")
    scope = get_or_create_project_scope(db_session, repo.id)
    card = {"kind": "project_fact", "title": "T", "body": "Same body."}

    first = create_sketch(
        db_session,
        scope=scope,
        card=card,
        origin="passive_extraction",
        engineer_id=eng1.id,
        session_id=None,
        citation={"excerpt": "x"},
    )
    second = create_sketch(
        db_session,
        scope=scope,
        card=card,
        origin="passive_extraction",
        engineer_id=eng2.id,
        session_id=None,
        citation={"excerpt": "y"},
    )
    assert second.id == first.id  # no new entry
    assert len(first.evidence) == 2  # evidence accreted


def test_create_sketch_skips_rejected_duplicates(db_session):
    repo = _repo_and_scope(db_session)
    eng = _engineer(db_session)
    scope = get_or_create_project_scope(db_session, repo.id)
    card = {"kind": "project_fact", "title": "T", "body": "Rejected body."}

    first = create_sketch(
        db_session,
        scope=scope,
        card=card,
        origin="passive_extraction",
        engineer_id=eng.id,
        session_id=None,
        citation={"excerpt": "x"},
    )
    first.status = "rejected"
    db_session.flush()

    result = create_sketch(
        db_session,
        scope=scope,
        card=card,
        origin="passive_extraction",
        engineer_id=eng.id,
        session_id=None,
        citation={"excerpt": "y"},
    )
    assert result is None  # sticky rejection: dropped silently
    assert len(first.evidence) == 1


def test_create_sketch_respects_paused_scope(db_session):
    repo = _repo_and_scope(db_session)
    eng = _engineer(db_session)
    scope = get_or_create_project_scope(db_session, repo.id)
    from datetime import datetime

    scope.memory_paused_at = datetime(2026, 1, 1)
    db_session.flush()

    result = create_sketch(
        db_session,
        scope=scope,
        card={"kind": "project_fact", "title": "T", "body": "B."},
        origin="passive_extraction",
        engineer_id=eng.id,
        session_id=None,
        citation={"excerpt": "x"},
    )
    assert result is None
