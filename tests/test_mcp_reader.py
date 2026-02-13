import json

import primer.mcp.reader as reader


def test_list_local_sessions_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(reader, "get_usage_data_dir", lambda: tmp_path / "usage-data")
    result = reader.list_local_sessions()
    assert result == []


def test_list_local_sessions(tmp_path, monkeypatch):
    usage_dir = tmp_path / "usage-data"
    sessions_dir = usage_dir / "sessions"
    facets_dir = usage_dir / "facets"
    sessions_dir.mkdir(parents=True)
    facets_dir.mkdir(parents=True)

    # Create two sessions, one with facets
    (sessions_dir / "sess-1.jsonl").write_text('{"type":"human"}\n')
    (sessions_dir / "sess-2.jsonl").write_text('{"type":"human"}\n')
    (facets_dir / "sess-1.json").write_text('{"outcome":"success"}')

    monkeypatch.setattr(reader, "get_usage_data_dir", lambda: usage_dir)
    result = reader.list_local_sessions()

    assert len(result) == 2
    ids = {s.session_id for s in result}
    assert ids == {"sess-1", "sess-2"}

    sess1 = next(s for s in result if s.session_id == "sess-1")
    assert sess1.has_facets is True
    assert sess1.facets_path is not None

    sess2 = next(s for s in result if s.session_id == "sess-2")
    assert sess2.has_facets is False
    assert sess2.facets_path is None


def test_get_local_session_ids(tmp_path, monkeypatch):
    usage_dir = tmp_path / "usage-data"
    sessions_dir = usage_dir / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "abc.jsonl").write_text("")
    (sessions_dir / "def.jsonl").write_text("")

    monkeypatch.setattr(reader, "get_usage_data_dir", lambda: usage_dir)
    ids = reader.get_local_session_ids()
    assert ids == {"abc", "def"}


def test_read_local_stats_nonexistent(tmp_path, monkeypatch):
    monkeypatch.setattr(reader, "get_usage_data_dir", lambda: tmp_path / "usage-data")
    result = reader.read_local_stats()
    assert result == {}


def test_read_local_stats(tmp_path, monkeypatch):
    usage_dir = tmp_path / "usage-data"
    usage_dir.mkdir(parents=True)
    stats = {"total_sessions": 42, "total_tokens": 100000}
    (usage_dir / "stats.json").write_text(json.dumps(stats))

    monkeypatch.setattr(reader, "get_usage_data_dir", lambda: usage_dir)
    result = reader.read_local_stats()
    assert result["total_sessions"] == 42
