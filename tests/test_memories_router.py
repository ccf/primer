"""Tests for POST /api/v1/memories/remember."""

import pytest

from primer.common.config import settings
from primer.common.models import GitRepository, MemoryEntry


@pytest.fixture(autouse=True)
def _memory_on(monkeypatch):
    monkeypatch.setattr(settings, "memory_enabled", True)
    monkeypatch.setattr(settings, "redaction_enabled", True)


def _seed_session(db_session, engineer, session_id="rem-1"):
    from primer.common.models import Session as SessionModel

    repo = GitRepository(full_name="acme/rem")
    db_session.add(repo)
    db_session.flush()
    db_session.add(SessionModel(id=session_id, engineer_id=engineer.id, repository_id=repo.id))
    db_session.flush()
    return repo


def test_remember_creates_sketch(client, engineer_with_key, db_session):
    engineer, api_key = engineer_with_key
    _seed_session(db_session, engineer)

    r = client.post(
        "/api/v1/memories/remember",
        json={
            "session_id": "rem-1",
            "text": "The staging DB resets nightly at 02:00 UTC.",
            "kind": "project_fact",
        },
        headers={"x-api-key": api_key},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "sketch_created"
    entry = db_session.query(MemoryEntry).one()
    assert entry.origin == "remember_tool"
    assert entry.status == "sketch"
    assert entry.created_by_engineer_id == engineer.id
    assert entry.evidence[0].evidence_kind == "explicit_remember"


def test_remember_rate_limited_per_session(client, engineer_with_key, db_session, monkeypatch):
    monkeypatch.setattr(settings, "memory_remember_per_session", 2)
    engineer, api_key = engineer_with_key
    _seed_session(db_session, engineer, "rem-rl")

    for i in range(2):
        r = client.post(
            "/api/v1/memories/remember",
            json={"session_id": "rem-rl", "text": f"Durable fact number {i} here."},
            headers={"x-api-key": api_key},
        )
        assert r.status_code == 200
    r = client.post(
        "/api/v1/memories/remember",
        json={"session_id": "rem-rl", "text": "One fact too many for this session."},
        headers={"x-api-key": api_key},
    )
    assert r.status_code == 429


def test_remember_unknown_session_404(client, engineer_with_key):
    _engineer, api_key = engineer_with_key
    r = client.post(
        "/api/v1/memories/remember",
        json={"session_id": "nope", "text": "Some durable project fact."},
        headers={"x-api-key": api_key},
    )
    assert r.status_code == 404


def test_remember_memory_disabled_409(client, engineer_with_key, monkeypatch):
    monkeypatch.setattr(settings, "memory_enabled", False)
    _engineer, api_key = engineer_with_key
    r = client.post(
        "/api/v1/memories/remember",
        json={"session_id": "rem-1", "text": "Some durable project fact that is long enough."},
        headers={"x-api-key": api_key},
    )
    assert r.status_code == 409


def test_remember_redacts_text(client, engineer_with_key, db_session):
    engineer, api_key = engineer_with_key
    _seed_session(db_session, engineer, "rem-redact")
    r = client.post(
        "/api/v1/memories/remember",
        json={
            "session_id": "rem-redact",
            "text": "Use key sk-ant-api03-AbCdEf123456789012345 for staging.",
        },
        headers={"x-api-key": api_key},
    )
    assert r.status_code == 200
    entry = db_session.query(MemoryEntry).one()
    assert "sk-ant-api03" not in entry.body


def test_remember_same_text_twice_accretes(client, engineer_with_key, db_session):
    engineer, api_key = engineer_with_key
    _seed_session(db_session, engineer, "rem-accrete")
    text = "The build cache lives under .cache and is safe to delete."

    r1 = client.post(
        "/api/v1/memories/remember",
        json={"session_id": "rem-accrete", "text": text},
        headers={"x-api-key": api_key},
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "sketch_created"

    r2 = client.post(
        "/api/v1/memories/remember",
        json={"session_id": "rem-accrete", "text": text},
        headers={"x-api-key": api_key},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "evidence_accreted"
    assert db_session.query(MemoryEntry).count() == 1


def test_remember_redacts_files(client, engineer_with_key, db_session):
    engineer, api_key = engineer_with_key
    _seed_session(db_session, engineer, "rem-files")
    r = client.post(
        "/api/v1/memories/remember",
        json={
            "session_id": "rem-files",
            "text": "Store the deploy token in the secrets config.",
            "files": ["cfg ghp_abcdefghijklmnopqrstuvwxyz0123456789AB"],
        },
        headers={"x-api-key": api_key},
    )
    assert r.status_code == 200
    entry = db_session.query(MemoryEntry).one()
    assert entry.files is not None
    assert all("ghp_" not in f for f in entry.files)
