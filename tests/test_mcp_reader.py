import json
from pathlib import Path

import primer.mcp.reader as reader


def _mock_home(tmp_path, monkeypatch):
    """Point Path.home() at tmp_path so extractors don't find real sessions."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))


def test_list_local_sessions_empty(tmp_path, monkeypatch):
    _mock_home(tmp_path, monkeypatch)
    result = reader.list_local_sessions()
    assert result == []


def _setup_session(tmp_path, monkeypatch, session_id, project_path, *, has_facets=False):
    """Create session-meta JSON, transcript JSONL, and optionally facets."""
    claude_dir = tmp_path / ".claude"
    usage_dir = claude_dir / "usage-data"
    meta_dir = usage_dir / "session-meta"
    facets_dir = usage_dir / "facets"
    meta_dir.mkdir(parents=True, exist_ok=True)
    facets_dir.mkdir(parents=True, exist_ok=True)

    # session-meta/<id>.json
    meta = {"project_path": project_path}
    (meta_dir / f"{session_id}.json").write_text(json.dumps(meta))

    # transcript in projects/<dir>/<id>.jsonl
    dir_name = project_path.replace("/", "-")
    projects_dir = claude_dir / "projects" / dir_name
    projects_dir.mkdir(parents=True, exist_ok=True)
    (projects_dir / f"{session_id}.jsonl").write_text('{"type":"human"}\n')

    if has_facets:
        (facets_dir / f"{session_id}.json").write_text('{"outcome":"success"}')

    _mock_home(tmp_path, monkeypatch)


def _setup_codex_session(tmp_path, session_id, project_path):
    sessions_dir = tmp_path / ".codex" / "sessions" / "2026" / "03" / "08"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    rollout_path = sessions_dir / f"rollout-{session_id}.jsonl"
    rollout_path.write_text(
        json.dumps(
            {
                "SessionMeta": {
                    "id": session_id,
                    "cwd": project_path,
                    "cli_version": "0.1.0",
                    "model": "gpt-4.1",
                }
            }
        )
        + "\n"
    )


def _setup_gemini_session(tmp_path, session_id, project_path):
    chats_dir = tmp_path / ".gemini" / "tmp" / "project-hash" / "chats"
    chats_dir.mkdir(parents=True, exist_ok=True)
    (chats_dir / f"{session_id}.json").write_text(json.dumps({"contents": []}))
    metadata_path = chats_dir.parent / "metadata.json"
    metadata_path.write_text(json.dumps({"project_path": project_path}))


def _setup_cursor_import(tmp_path, session_id, project_path):
    sessions_dir = tmp_path / ".primer" / "cursor" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = sessions_dir / f"{session_id}.json"
    bundle_path.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "project_path": project_path,
                "messages": [{"role": "human", "content_text": "Imported from Cursor"}],
            }
        )
    )
    return bundle_path


def _setup_cursor_workspace_storage_json(
    tmp_path,
    session_id,
    project_path,
    *,
    workspace_id="workspace-1",
):
    workspace_dir = (
        tmp_path
        / "Library"
        / "Application Support"
        / "Cursor"
        / "User"
        / "workspaceStorage"
        / workspace_id
    )
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "workspace.json").write_text(
        json.dumps({"folder": Path(project_path).as_uri()})
    )
    bundle_path = workspace_dir / "extension-state.json"
    bundle_path.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "messages": [
                    {"role": "human", "content_text": "Unrelated workspace storage"},
                    {"role": "assistant", "content_text": "Do not ingest me"},
                ],
            }
        )
    )
    return bundle_path


def test_list_local_sessions(tmp_path, monkeypatch):
    _setup_session(tmp_path, monkeypatch, "sess-1", "/home/user/project", has_facets=True)
    _setup_session(tmp_path, monkeypatch, "sess-2", "/home/user/project", has_facets=False)

    result = reader.list_local_sessions()

    assert len(result) == 2
    ids = {s.session_id for s in result}
    assert ids == {"sess-1", "sess-2"}

    sess1 = next(s for s in result if s.session_id == "sess-1")
    assert sess1.has_facets is True
    assert sess1.facets_path is not None
    assert sess1.project_path == "/home/user/project"

    sess2 = next(s for s in result if s.session_id == "sess-2")
    assert sess2.has_facets is False
    assert sess2.facets_path is None


def test_list_local_sessions_fallback_search(tmp_path, monkeypatch):
    """Transcript found even when session-meta has no project_path."""
    claude_dir = tmp_path / ".claude"
    usage_dir = claude_dir / "usage-data"
    meta_dir = usage_dir / "session-meta"
    meta_dir.mkdir(parents=True)
    (usage_dir / "facets").mkdir()

    # Meta without project_path
    (meta_dir / "orphan.json").write_text("{}")

    # Transcript exists in some project dir
    proj_dir = claude_dir / "projects" / "-home-user-project"
    proj_dir.mkdir(parents=True)
    (proj_dir / "orphan.jsonl").write_text('{"type":"human"}\n')

    _mock_home(tmp_path, monkeypatch)

    result = reader.list_local_sessions()
    assert len(result) == 1
    assert result[0].session_id == "orphan"


def test_get_local_session_ids(tmp_path, monkeypatch):
    _setup_session(tmp_path, monkeypatch, "abc", "/home/user/project")
    _setup_session(tmp_path, monkeypatch, "def", "/home/user/project")

    ids = reader.get_local_session_ids()
    assert ids == {"abc", "def"}


def test_list_local_sessions_includes_imported_cursor_bundles(tmp_path, monkeypatch):
    _setup_session(tmp_path, monkeypatch, "claude-1", "/home/user/claude-project")
    _setup_codex_session(tmp_path, "codex-1", "/home/user/codex-project")
    _setup_gemini_session(tmp_path, "session-gemini-1", "/home/user/gemini-project")
    cursor_bundle = _setup_cursor_import(tmp_path, "cursor-1", "/home/user/cursor-project")

    _mock_home(tmp_path, monkeypatch)
    result = reader.list_local_sessions()

    sessions_by_id = {session.session_id: session for session in result}

    assert set(sessions_by_id) == {"claude-1", "codex-1", "session-gemini-1", "cursor-1"}
    assert sessions_by_id["claude-1"].agent_type == "claude_code"
    assert sessions_by_id["codex-1"].agent_type == "codex_cli"
    assert sessions_by_id["session-gemini-1"].agent_type == "gemini_cli"

    cursor = sessions_by_id["cursor-1"]
    assert cursor.agent_type == "cursor"
    assert cursor.transcript_path == str(cursor_bundle)
    assert cursor.project_path == "/home/user/cursor-project"
    assert cursor.has_facets is False
    assert cursor.facets_path is None


def test_list_local_sessions_ignores_generic_cursor_workspace_storage_json(tmp_path, monkeypatch):
    _setup_cursor_workspace_storage_json(tmp_path, "cursor-native-1", "/home/user/native-cursor")

    _mock_home(tmp_path, monkeypatch)
    result = reader.list_local_sessions()

    assert result == []


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
