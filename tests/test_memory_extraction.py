"""Tests for passive memory-card extraction (mirrors facet extraction patterns)."""

import json

from primer.server.services.memory_extraction_service import (
    _parse_cards_response,
    _scrub_identity,
    session_has_substance,
)


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
    body = "Alice fixed this in /Users/alice/git/svc/src/x.py per alice@example.com"
    scrubbed = _scrub_identity(body, engineer_names=["Alice"])
    assert "Alice" not in scrubbed
    assert "alice@example.com" not in scrubbed
    assert "/Users/alice" not in scrubbed
    assert "src/x.py" in scrubbed  # repo-relative tail survives


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
