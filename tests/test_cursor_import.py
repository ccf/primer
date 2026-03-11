import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from primer.cli.main import cli


def _mock_primer_home(tmp_path, monkeypatch) -> Path:
    primer_home = tmp_path / ".primer"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", primer_home / "config.toml")
    return primer_home


def _write_bundle(tmp_path, bundle: dict, name: str = "cursor-bundle.json") -> Path:
    bundle_path = tmp_path / name
    bundle_path.write_text(json.dumps(bundle))
    return bundle_path


def _write_native_transcript(
    tmp_path,
    session_id: str,
    project_path: Path,
    *,
    name: str | None = None,
) -> Path:
    transcript_path = tmp_path / (name or f"{session_id}.jsonl")
    transcript_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "role": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        f"<git_status>\nGit repo: {project_path}\n</git_status>"
                                    ),
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "role": "assistant",
                        "message": {
                            "content": [{"type": "text", "text": "I found the project context."}]
                        },
                    }
                ),
            ]
        )
        + "\n"
    )
    return transcript_path


def test_cursor_import_copies_valid_bundle_into_primer_store(tmp_path, monkeypatch):
    primer_home = _mock_primer_home(tmp_path, monkeypatch)
    bundle = {
        "session_id": "cursor-sess-1",
        "project_path": str(tmp_path / "demo"),
        "agent_version": "cursor-1.0.0",
        "started_at": "2026-03-08T10:00:00Z",
        "ended_at": "2026-03-08T10:05:00Z",
        "messages": [
            {"role": "human", "content_text": "Fix the failing test"},
            {"role": "assistant", "content_text": "I'll inspect the suite."},
        ],
    }
    bundle_path = _write_bundle(tmp_path, bundle)

    runner = CliRunner()
    result = runner.invoke(cli, ["cursor", "import", str(bundle_path)])

    stored_path = primer_home / "cursor" / "sessions" / "cursor-sess-1.json"
    assert result.exit_code == 0
    assert stored_path.exists()
    assert json.loads(stored_path.read_text()) == bundle


def test_cursor_import_preserves_jsonl_native_transcripts_for_rediscovery(tmp_path, monkeypatch):
    primer_home = _mock_primer_home(tmp_path, monkeypatch)
    project_path = tmp_path / "demo"
    transcript_path = _write_native_transcript(tmp_path, "cursor-native-1", project_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["cursor", "import", str(transcript_path)])

    stored_jsonl = primer_home / "cursor" / "sessions" / "cursor-native-1.jsonl"
    stored_json = primer_home / "cursor" / "sessions" / "cursor-native-1.json"

    assert result.exit_code == 0
    assert stored_jsonl.exists()
    assert not stored_json.exists()

    from primer.hook.cursor_extractor import CursorExtractor

    extractor = CursorExtractor()
    sessions = extractor.discover_sessions()
    assert [
        session.session_id for session in sessions if session.transcript_path == str(stored_jsonl)
    ] == ["cursor-native-1"]

    meta = extractor.extract(str(stored_jsonl))
    assert meta.project_path == str(project_path)
    assert meta.message_count == 2


def test_cursor_import_rejects_missing_session_id(tmp_path, monkeypatch):
    primer_home = _mock_primer_home(tmp_path, monkeypatch)
    bundle_path = _write_bundle(
        tmp_path,
        {
            "project_path": str(tmp_path / "demo"),
            "messages": [{"role": "human", "content_text": "Missing a session id"}],
        },
        name="missing-session-id.json",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["cursor", "import", str(bundle_path)])

    assert result.exit_code != 0
    assert "session_id" in result.output
    assert not (primer_home / "cursor" / "sessions").exists()


def test_cursor_import_wraps_extractor_failures_in_click_exception(tmp_path, monkeypatch):
    _mock_primer_home(tmp_path, monkeypatch)
    bundle_path = _write_bundle(
        tmp_path,
        {
            "session_id": "cursor-bad-1",
            "project_path": str(tmp_path / "demo"),
            "messages": [
                {
                    "role": "human",
                    "content_text": "This bundle triggers an extractor bug",
                }
            ],
        },
        name="extractor-error.json",
    )

    runner = CliRunner()
    with patch(
        "primer.cli.commands.cursor_cmd.CursorExtractor.extract",
        side_effect=RuntimeError("boom"),
    ):
        result = runner.invoke(cli, ["cursor", "import", str(bundle_path)])

    assert result.exit_code != 0
    assert "Invalid Cursor bundle" in result.output
    assert "boom" in result.output


def test_cursor_import_rejects_bundle_with_no_messages(tmp_path, monkeypatch):
    primer_home = _mock_primer_home(tmp_path, monkeypatch)
    bundle_path = _write_bundle(
        tmp_path,
        {
            "session_id": "cursor-empty-1",
            "project_path": str(tmp_path / "demo"),
            "messages": [],
        },
        name="empty-messages.json",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["cursor", "import", str(bundle_path)])

    assert result.exit_code != 0
    assert "contains no messages" in result.output
    assert not (primer_home / "cursor" / "sessions").exists()


def test_cursor_import_is_idempotent_for_same_session_id(tmp_path, monkeypatch):
    primer_home = _mock_primer_home(tmp_path, monkeypatch)
    bundle = {
        "session_id": "cursor-sess-2",
        "project_path": str(tmp_path / "demo"),
        "messages": [{"role": "human", "content_text": "Import me once"}],
    }
    bundle_path = _write_bundle(tmp_path, bundle, name="cursor-sess-2.json")

    runner = CliRunner()
    first = runner.invoke(cli, ["cursor", "import", str(bundle_path)])
    stored_path = primer_home / "cursor" / "sessions" / "cursor-sess-2.json"
    first_mtime_ns = stored_path.stat().st_mtime_ns if stored_path.exists() else None
    second = runner.invoke(cli, ["cursor", "import", str(bundle_path)])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert stored_path.exists()
    assert first_mtime_ns is not None
    assert stored_path.stat().st_mtime_ns == first_mtime_ns
    assert sorted(path.name for path in stored_path.parent.glob("*.json")) == ["cursor-sess-2.json"]


@pytest.mark.parametrize(
    ("session_id", "unexpected_path"),
    [
        (
            "nested/session",
            lambda primer_home, tmp_path: primer_home / "cursor" / "sessions" / "nested",
        ),
        ("../escape", lambda primer_home, tmp_path: primer_home / "cursor" / "escape.json"),
        (
            None,
            lambda primer_home, tmp_path: (tmp_path / "absolute-target").with_suffix(".json"),
        ),
    ],
)
def test_cursor_import_rejects_unsafe_session_ids(
    tmp_path, monkeypatch, session_id, unexpected_path
):
    primer_home = _mock_primer_home(tmp_path, monkeypatch)
    raw_session_id = session_id or str(tmp_path / "absolute-target")
    bundle_path = _write_bundle(
        tmp_path,
        {
            "session_id": raw_session_id,
            "project_path": str(tmp_path / "demo"),
            "messages": [{"role": "human", "content_text": "Do not trust this session id"}],
        },
        name="unsafe-session-id.json",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["cursor", "import", str(bundle_path)])

    assert result.exit_code != 0
    assert "unsafe session_id" in result.output
    assert not (primer_home / "cursor" / "sessions").exists()
    assert not unexpected_path(primer_home, tmp_path).exists()
