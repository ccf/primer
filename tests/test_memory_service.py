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
from primer.server.services.memory_service import memory_capture_active


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
