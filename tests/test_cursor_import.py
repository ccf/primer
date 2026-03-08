import json
from pathlib import Path

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
