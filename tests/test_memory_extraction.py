"""Tests for passive memory-card extraction (mirrors facet extraction patterns)."""

import json

from primer.server.services.memory_extraction_service import (
    _parse_cards_response,
    session_has_substance,
)
from primer.server.services.memory_service import scrub_identity


def test_parse_cards_response_valid():
    text = (
        'Here you go:\n[{"kind": "project_fact", "title": "T", "body": "B",'
        ' "concepts": [], "files": ["src/x.py"]}]'
    )
    cards = _parse_cards_response(text)
    assert len(cards) == 1
    assert cards[0]["title"] == "T"


def test_parse_cards_response_caps_at_max(monkeypatch):
    from primer.common.config import settings

    monkeypatch.setattr(settings, "memory_max_cards_per_session", 2)
    text = json.dumps(
        [{"kind": "project_fact", "title": f"T{i}", "body": f"B{i}"} for i in range(5)]
    )
    assert len(_parse_cards_response(text)) == 2


def test_parse_cards_response_garbage_returns_empty():
    assert _parse_cards_response("no json here") == []
    assert _parse_cards_response('{"not": "a list"}') == []


def test_scrub_identity_removes_names_and_paths():
    body = "Alice fixed this in /Users/alice/git/svc/config/x.py per alice@example.com"
    scrubbed = scrub_identity(body, engineer_names=["Alice"])
    assert "Alice" not in scrubbed
    assert "alice@example.com" not in scrubbed
    assert "/Users/alice" not in scrubbed
    assert "config/x.py" in scrubbed  # non-src tail survives, username stripped


def test_scrub_identity_case_insensitive_names():
    scrubbed = scrub_identity("casey and CASEY both broke it", engineer_names=["Casey"])
    assert "casey" not in scrubbed.lower().replace("an engineer", "")


def test_session_has_substance_thresholds(db_session, monkeypatch):
    from primer.common.config import settings
    from primer.common.models import Engineer
    from primer.common.models import Session as SessionModel

    monkeypatch.setattr(settings, "memory_extraction_min_substance", 5)
    eng = Engineer(name="E", email="e@x.io")
    db_session.add(eng)
    db_session.flush()
    thin = SessionModel(id="thin-1", engineer_id=eng.id, tool_call_count=2)
    rich = SessionModel(id="rich-1", engineer_id=eng.id, tool_call_count=9)
    db_session.add_all([thin, rich])
    db_session.flush()
    assert session_has_substance(thin) is False
    assert session_has_substance(rich) is True


# --- Integration tests (mocked Anthropic) ---

import json as _json  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

from primer.common.config import settings as _settings  # noqa: E402
from primer.common.models import GitRepository, SessionMessage  # noqa: E402
from primer.server.services import memory_extraction_service  # noqa: E402


def _seed_rich_session(db_session):
    from primer.common.models import Engineer
    from primer.common.models import Session as SessionModel

    eng = Engineer(name="Casey", email="c@x.io")
    repo = GitRepository(full_name="acme/api")
    db_session.add_all([eng, repo])
    db_session.flush()
    sess = SessionModel(
        id="mem-rich-1", engineer_id=eng.id, repository_id=repo.id, tool_call_count=12
    )
    db_session.add(sess)
    db_session.add(
        SessionMessage(
            session_id="mem-rich-1",
            ordinal=0,
            role="human",
            content_text="run alembic upgrade head before make build",
        )
    )
    db_session.flush()
    return eng, repo, sess


def test_extract_memory_for_session_end_to_end(db_session, monkeypatch):
    monkeypatch.setattr(_settings, "memory_enabled", True)
    monkeypatch.setattr(_settings, "redaction_enabled", True)
    monkeypatch.setattr(_settings, "anthropic_api_key", "test-key")
    _seed_rich_session(db_session)
    # Patch SessionLocal to return the test session instead of opening a new one.
    # Neutralize close/commit so the test transaction stays intact (mirrors
    # the established pattern in tests/test_facet_extraction.py).
    db_session.close = MagicMock()
    db_session.commit = MagicMock()

    api_response = {
        "content": [
            {
                "type": "text",
                "text": _json.dumps(
                    [
                        {
                            "kind": "anti_pattern",
                            "title": "Casey says: run migrations before build",
                            "body": "Don't run make build without alembic upgrade head first.",
                            "concepts": ["build"],
                            "files": [],
                        }
                    ]
                ),
            }
        ]
    }
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = api_response

    svc = "primer.server.services.memory_extraction_service"
    with (
        patch(f"{svc}.SessionLocal", return_value=db_session),
        patch.object(memory_extraction_service.httpx.Client, "post", return_value=mock_resp),
    ):
        result = memory_extraction_service.extract_memory_for_session("mem-rich-1")

    assert result == "done"
    from primer.common.models import MemoryEntry

    entries = db_session.query(MemoryEntry).all()
    assert len(entries) == 1
    assert entries[0].status == "sketch"
    assert "Casey" not in entries[0].title  # identity scrubbed
    assert entries[0].evidence[0].session_id == "mem-rich-1"


def test_extract_memory_scrubs_card_file_paths(db_session, monkeypatch):
    # Passive extraction must scrub identity-bearing paths in the card `files`
    # field (not just title/body) before persisting.
    monkeypatch.setattr(_settings, "memory_enabled", True)
    monkeypatch.setattr(_settings, "redaction_enabled", True)
    monkeypatch.setattr(_settings, "anthropic_api_key", "test-key")
    _seed_rich_session(db_session)
    db_session.close = MagicMock()
    db_session.commit = MagicMock()

    api_response = {
        "content": [
            {
                "type": "text",
                "text": _json.dumps(
                    [
                        {
                            "kind": "project_fact",
                            "title": "config lives under src",
                            "body": "The build config is checked in.",
                            "concepts": ["build"],
                            "files": ["/Users/casey/git/api/src/config.py"],
                        }
                    ]
                ),
            }
        ]
    }
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = api_response

    svc = "primer.server.services.memory_extraction_service"
    with (
        patch(f"{svc}.SessionLocal", return_value=db_session),
        patch.object(memory_extraction_service.httpx.Client, "post", return_value=mock_resp),
    ):
        result = memory_extraction_service.extract_memory_for_session("mem-rich-1")

    assert result == "done"
    from primer.common.models import MemoryEntry

    entry = db_session.query(MemoryEntry).one()
    # username/home prefix stripped (PII gone), path tail preserved
    assert entry.files == ["git/api/src/config.py"]
    assert "casey" not in str(entry.files)
    assert "/Users/" not in str(entry.files)


def test_extract_skips_when_memory_disabled(db_session, monkeypatch):
    monkeypatch.setattr(_settings, "memory_enabled", False)
    assert memory_extraction_service.extract_memory_for_session("whatever") == "skipped"


def test_extract_is_idempotent_for_already_extracted_session(db_session, monkeypatch):
    # A session already carrying transcript_citation evidence is skipped without
    # an LLM call — the post-ingest path fires on every ingest + retries, so this
    # prevents redundant extraction of identical (capped) transcript content.
    from primer.common.models import MemoryEntry, MemoryEvidence, MemoryScope

    monkeypatch.setattr(_settings, "memory_enabled", True)
    monkeypatch.setattr(_settings, "redaction_enabled", True)
    monkeypatch.setattr(_settings, "anthropic_api_key", "test-key")
    _eng, repo, _sess = _seed_rich_session(db_session)
    scope = MemoryScope(kind="project", name="acme/api", repository_id=repo.id)
    db_session.add(scope)
    db_session.flush()
    entry = MemoryEntry(
        scope_id=scope.id, kind="project_fact", title="t", body="b", content_hash="h"
    )
    db_session.add(entry)
    db_session.flush()
    db_session.add(
        MemoryEvidence(
            memory_id=entry.id, evidence_kind="transcript_citation", session_id="mem-rich-1"
        )
    )
    db_session.commit()

    api_called = []
    with (
        patch(
            "primer.server.services.memory_extraction_service.SessionLocal",
            return_value=db_session,
        ),
        patch.object(
            memory_extraction_service.httpx.Client,
            "post",
            side_effect=lambda *a, **k: api_called.append(1),
        ),
    ):
        db_session.close = MagicMock()
        result = memory_extraction_service.extract_memory_for_session("mem-rich-1")

    assert result == "skipped"
    assert api_called == []  # no LLM call made


def test_extract_memory_returns_failed_on_api_error(db_session, monkeypatch):
    import primer.server.services.memory_extraction_service as mes
    from primer.common.config import settings as _s
    from primer.common.models import Engineer, GitRepository, MemoryEntry, SessionMessage
    from primer.common.models import Session as SessionModel

    monkeypatch.setattr(_s, "memory_enabled", True)
    monkeypatch.setattr(_s, "redaction_enabled", True)
    monkeypatch.setattr(_s, "anthropic_api_key", "k")
    eng = Engineer(name="D", email="d@x.io")
    repo = GitRepository(full_name="acme/f")
    db_session.add_all([eng, repo])
    db_session.flush()
    db_session.add(
        SessionModel(id="fail-1", engineer_id=eng.id, repository_id=repo.id, tool_call_count=10)
    )
    db_session.add(
        SessionMessage(session_id="fail-1", ordinal=0, role="human", content_text="do x")
    )
    db_session.commit()
    monkeypatch.setattr(mes, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    def _boom(*a, **k):
        raise RuntimeError("api down")

    monkeypatch.setattr(mes, "_call_extraction_api", _boom)
    assert mes.extract_memory_for_session("fail-1") == "failed"
    assert db_session.query(MemoryEntry).count() == 0
