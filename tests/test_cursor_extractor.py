import json
from pathlib import Path

from primer.hook.cursor_extractor import CursorExtractor


def _write_json(tmp_path, data: dict, name: str = "cursor-bundle.json") -> str:
    path = tmp_path / name
    path.write_text(json.dumps(data))
    return str(path)


def _setup_cursor_workspace_json(
    tmp_path,
    session_id: str,
    project_path: Path,
    *,
    workspace_id: str = "workspace-1",
    name: str = "extension-state.json",
) -> Path:
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
    (workspace_dir / "workspace.json").write_text(json.dumps({"folder": project_path.as_uri()}))
    native_path = workspace_dir / name
    native_path.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "started_at": "2026-03-08T11:00:00Z",
                "ended_at": "2026-03-08T11:02:00Z",
                "messages": [
                    {"role": "user", "content_text": "Not a validated transcript"},
                    {"role": "assistant", "content_text": "Still not trustworthy"},
                ],
            }
        )
    )
    return native_path


def test_extract_cursor_bundle_reads_core_metadata(tmp_path):
    project_path = tmp_path / "demo"
    bundle = {
        "session_id": "cursor-sess-1",
        "project_path": str(project_path),
        "agent_version": "cursor-1.0.0",
        "started_at": "2026-03-08T10:00:00Z",
        "ended_at": "2026-03-08T10:05:00Z",
        "permission_mode": "workspace-write",
        "primary_model": "gpt-4.1",
        "summary": "Imported Cursor session bundle",
        "messages": [
            {"role": "user", "content_text": "Fix the failing test"},
            {"role": "model", "content_text": "I'll inspect the suite."},
        ],
        "tool_usages": [
            {"tool_name": "Read", "call_count": 2},
            {"tool_name": "Edit", "call_count": 1},
        ],
        "model_usages": [
            {
                "model_name": "gpt-4.1",
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_read_tokens": 10,
                "cache_creation_tokens": 5,
            },
            {
                "model_name": "gpt-4.1",
                "input_tokens": 40,
                "output_tokens": 20,
            },
        ],
    }

    extractor = CursorExtractor()
    meta = extractor.extract(_write_json(tmp_path, bundle))

    assert meta.session_id == "cursor-sess-1"
    assert meta.agent_type == "cursor"
    assert meta.project_path == str(project_path)
    assert meta.project_name == "demo"
    assert meta.agent_version == "cursor-1.0.0"
    assert meta.permission_mode == "workspace-write"
    assert meta.primary_model == "gpt-4.1"
    assert meta.summary == "Imported Cursor session bundle"
    assert meta.started_at.isoformat() == "2026-03-08T10:00:00+00:00"
    assert meta.ended_at.isoformat() == "2026-03-08T10:05:00+00:00"
    assert meta.duration_seconds == 300.0
    assert meta.messages == [
        {"ordinal": 0, "role": "human", "content_text": "Fix the failing test"},
        {"ordinal": 1, "role": "assistant", "content_text": "I'll inspect the suite."},
    ]
    assert meta.message_count == 2
    assert meta.user_message_count == 1
    assert meta.assistant_message_count == 1
    assert meta.first_prompt == "Fix the failing test"
    assert meta.tool_call_count == 3
    assert meta.tool_counts == {"Read": 2, "Edit": 1}
    assert meta.input_tokens == 140
    assert meta.output_tokens == 70
    assert meta.cache_read_tokens == 10
    assert meta.cache_creation_tokens == 5
    assert meta.model_tokens == {
        "gpt-4.1": {
            "input": 140,
            "output": 70,
            "cache_read": 10,
            "cache_creation": 5,
        }
    }


def test_extract_cursor_bundle_gracefully_handles_missing_optional_sections(tmp_path):
    project_path = tmp_path / "another-demo"
    bundle = {
        "session_id": "cursor-sess-2",
        "project_path": str(project_path),
        "messages": [
            {"role": "assistant", "content_text": "Ready when you are."},
        ],
    }

    extractor = CursorExtractor()
    meta = extractor.extract(_write_json(tmp_path, bundle, name="cursor-sparse.json"))

    assert meta.session_id == "cursor-sess-2"
    assert meta.agent_type == "cursor"
    assert meta.project_path == str(project_path)
    assert meta.project_name == "another-demo"
    assert meta.messages == [
        {"ordinal": 0, "role": "assistant", "content_text": "Ready when you are."},
    ]
    assert meta.message_count == 1
    assert meta.user_message_count == 0
    assert meta.assistant_message_count == 1
    assert meta.first_prompt == ""
    assert meta.started_at is None
    assert meta.ended_at is None
    assert meta.duration_seconds is None
    assert meta.tool_call_count == 0
    assert meta.tool_counts == {}
    assert meta.model_tokens == {}
    assert meta.input_tokens == 0
    assert meta.output_tokens == 0
    assert meta.cache_read_tokens == 0
    assert meta.cache_creation_tokens == 0
    assert meta.primary_model == ""
    assert meta.permission_mode == ""
    assert meta.summary == ""


def test_extract_cursor_bundle_rewrites_mixed_ordinals_sequentially_and_clamps_bad_tokens(
    tmp_path,
):
    bundle = {
        "session_id": "cursor-sess-3",
        "messages": [
            {"ordinal": 7, "role": "human", "content_text": "First in bundle"},
            {"role": "assistant", "content_text": "Second in bundle"},
            {"ordinal": 2, "role": "user", "content_text": "Third in bundle"},
        ],
        "model_usages": [
            {
                "model_name": "gpt-4.1-mini",
                "input_tokens": -5,
                "output_tokens": "12",
                "cache_read_tokens": -1,
                "cache_creation_tokens": "3",
            }
        ],
    }

    extractor = CursorExtractor()
    meta = extractor.extract(_write_json(tmp_path, bundle, name="cursor-bad-tokens.json"))

    assert meta.messages == [
        {"ordinal": 0, "role": "human", "content_text": "First in bundle"},
        {"ordinal": 1, "role": "assistant", "content_text": "Second in bundle"},
        {"ordinal": 2, "role": "human", "content_text": "Third in bundle"},
    ]
    assert [message["content_text"] for message in meta.messages] == [
        "First in bundle",
        "Second in bundle",
        "Third in bundle",
    ]
    assert meta.first_prompt == "First in bundle"
    assert meta.input_tokens == 0
    assert meta.output_tokens == 12
    assert meta.cache_read_tokens == 0
    assert meta.cache_creation_tokens == 3
    assert meta.model_tokens == {
        "gpt-4.1-mini": {
            "input": 0,
            "output": 12,
            "cache_read": 0,
            "cache_creation": 3,
        }
    }


def test_discover_sessions_skips_bad_bundle_and_keeps_valid_one(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    sessions_dir = tmp_path / ".primer" / "cursor" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    good_bundle_path = sessions_dir / "good.json"
    good_bundle_path.write_text(
        json.dumps(
            {
                "session_id": "cursor-good",
                "project_path": str(tmp_path / "demo"),
                "messages": [{"role": "human", "content_text": "Valid bundle"}],
            }
        )
    )
    bad_bundle_path = sessions_dir / "bad.json"
    bad_bundle_path.write_text("{not valid json")

    original_extract = CursorExtractor.extract

    def extract_with_bad_file(self, transcript_path: str):
        if transcript_path == str(bad_bundle_path):
            raise ValueError("bad imported bundle")
        return original_extract(self, transcript_path)

    monkeypatch.setattr(CursorExtractor, "extract", extract_with_bad_file)

    sessions = CursorExtractor().discover_sessions()

    assert [(session.session_id, session.transcript_path) for session in sessions] == [
        ("cursor-good", str(good_bundle_path))
    ]


def test_discover_sessions_ignores_generic_workspace_storage_json(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    project_path = tmp_path / "native-project"
    _setup_cursor_workspace_json(tmp_path, "cursor-native-1", project_path)

    sessions = CursorExtractor().discover_sessions()

    assert sessions == []


def test_extract_cursor_bundle_clamps_negative_duration_to_none(tmp_path):
    bundle = {
        "session_id": "cursor-sess-negative-duration",
        "started_at": "2026-03-08T10:05:00Z",
        "ended_at": "2026-03-08T10:00:00Z",
        "messages": [{"role": "human", "content_text": "Time went backwards"}],
    }

    extractor = CursorExtractor()
    meta = extractor.extract(_write_json(tmp_path, bundle, name="cursor-negative-duration.json"))

    assert meta.started_at.isoformat() == "2026-03-08T10:05:00+00:00"
    assert meta.ended_at.isoformat() == "2026-03-08T10:00:00+00:00"
    assert meta.duration_seconds is None
