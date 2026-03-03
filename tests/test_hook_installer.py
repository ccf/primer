"""Tests for primer.hook.installer — install/uninstall/status for Claude and Gemini."""

import json

from primer.hook.installer import (
    HOOK_COMMAND,
    get_supported_agents,
    install,
    status,
    uninstall,
)

# ---------------------------------------------------------------------------
# get_supported_agents
# ---------------------------------------------------------------------------


def test_get_supported_agents():
    agents = get_supported_agents()
    assert "claude" in agents
    assert "gemini" in agents


# ---------------------------------------------------------------------------
# Claude Code tests (backward-compatible behavior)
# ---------------------------------------------------------------------------


def test_install_creates_hook(tmp_path):
    settings_path = tmp_path / "settings.json"
    ok, msg = install(path=settings_path)
    assert ok
    assert "installed" in msg.lower()

    data = json.loads(settings_path.read_text())
    hooks = data["hooks"]["SessionEnd"]
    assert len(hooks) == 1
    assert hooks[0]["command"] == HOOK_COMMAND


def test_install_idempotent(tmp_path):
    settings_path = tmp_path / "settings.json"
    install(path=settings_path)
    ok, msg = install(path=settings_path)
    assert ok
    assert "already" in msg.lower()

    data = json.loads(settings_path.read_text())
    assert len(data["hooks"]["SessionEnd"]) == 1


def test_install_preserves_existing_hooks(tmp_path):
    settings_path = tmp_path / "settings.json"
    existing = {
        "hooks": {"SessionEnd": [{"command": "other-hook", "timeout": 5000}]},
        "other_key": True,
    }
    settings_path.write_text(json.dumps(existing))

    install(path=settings_path)
    data = json.loads(settings_path.read_text())
    assert len(data["hooks"]["SessionEnd"]) == 2
    assert data["other_key"] is True


def test_uninstall_removes_hook(tmp_path):
    settings_path = tmp_path / "settings.json"
    install(path=settings_path)
    ok, msg = uninstall(path=settings_path)
    assert ok
    assert "removed" in msg.lower()

    data = json.loads(settings_path.read_text())
    assert len(data["hooks"]["SessionEnd"]) == 0


def test_uninstall_noop_when_not_installed(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{}")
    ok, msg = uninstall(path=settings_path)
    assert ok
    assert "not found" in msg.lower()


def test_status_installed(tmp_path):
    settings_path = tmp_path / "settings.json"
    install(path=settings_path)
    installed, msg = status(path=settings_path)
    assert installed
    assert "installed" in msg.lower()


def test_status_not_installed(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{}")
    installed, msg = status(path=settings_path)
    assert not installed
    assert "not installed" in msg.lower()


def test_status_missing_file(tmp_path):
    settings_path = tmp_path / "nonexistent.json"
    installed, _msg = status(path=settings_path)
    assert not installed


# ---------------------------------------------------------------------------
# Gemini CLI tests
# ---------------------------------------------------------------------------


def test_gemini_install_creates_hook(tmp_path):
    settings_path = tmp_path / "settings.json"
    ok, msg = install(path=settings_path, agent="gemini")
    assert ok
    assert "installed" in msg.lower()
    assert "Gemini CLI" in msg

    data = json.loads(settings_path.read_text())
    hooks_list = data["hooks"]
    assert isinstance(hooks_list, list)
    assert len(hooks_list) == 1

    exit_entry = hooks_list[0]
    assert exit_entry["matcher"] == "exit"
    inner = exit_entry["hooks"]
    assert len(inner) == 1
    assert inner[0]["name"] == "primer-hook"
    assert inner[0]["type"] == "command"
    assert "--agent gemini" in inner[0]["command"]


def test_gemini_install_idempotent(tmp_path):
    settings_path = tmp_path / "settings.json"
    install(path=settings_path, agent="gemini")
    ok, msg = install(path=settings_path, agent="gemini")
    assert ok
    assert "already" in msg.lower()

    data = json.loads(settings_path.read_text())
    exit_entry = data["hooks"][0]
    assert len(exit_entry["hooks"]) == 1


def test_gemini_install_preserves_existing_hooks(tmp_path):
    settings_path = tmp_path / "settings.json"
    existing = {
        "hooks": [
            {
                "matcher": "exit",
                "hooks": [{"name": "other-hook", "type": "command", "command": "echo bye"}],
            }
        ],
        "other_key": True,
    }
    settings_path.write_text(json.dumps(existing))

    install(path=settings_path, agent="gemini")
    data = json.loads(settings_path.read_text())
    assert data["other_key"] is True

    exit_entry = data["hooks"][0]
    assert len(exit_entry["hooks"]) == 2
    commands = [h["command"] for h in exit_entry["hooks"]]
    assert "echo bye" in commands


def test_gemini_install_creates_exit_matcher(tmp_path):
    """If hooks list exists but no 'exit' matcher, a new one is created."""
    settings_path = tmp_path / "settings.json"
    existing = {
        "hooks": [
            {
                "matcher": "start",
                "hooks": [{"name": "startup", "type": "command", "command": "echo hi"}],
            }
        ]
    }
    settings_path.write_text(json.dumps(existing))

    install(path=settings_path, agent="gemini")
    data = json.loads(settings_path.read_text())
    assert len(data["hooks"]) == 2
    matchers = [e["matcher"] for e in data["hooks"]]
    assert "exit" in matchers
    assert "start" in matchers


def test_gemini_uninstall_removes_hook(tmp_path):
    settings_path = tmp_path / "settings.json"
    install(path=settings_path, agent="gemini")
    ok, msg = uninstall(path=settings_path, agent="gemini")
    assert ok
    assert "removed" in msg.lower()

    data = json.loads(settings_path.read_text())
    exit_entry = data["hooks"][0]
    assert len(exit_entry["hooks"]) == 0


def test_gemini_uninstall_preserves_other_hooks(tmp_path):
    settings_path = tmp_path / "settings.json"
    existing = {
        "hooks": [
            {
                "matcher": "exit",
                "hooks": [
                    {"name": "other-hook", "type": "command", "command": "echo bye"},
                    {
                        "name": "primer-hook",
                        "type": "command",
                        "command": "python -m primer.hook.session_end --agent gemini",
                    },
                ],
            }
        ]
    }
    settings_path.write_text(json.dumps(existing))

    uninstall(path=settings_path, agent="gemini")
    data = json.loads(settings_path.read_text())
    inner = data["hooks"][0]["hooks"]
    assert len(inner) == 1
    assert inner[0]["command"] == "echo bye"


def test_gemini_uninstall_noop_when_not_installed(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{}")
    ok, msg = uninstall(path=settings_path, agent="gemini")
    assert ok
    assert "not found" in msg.lower()


def test_gemini_status_installed(tmp_path):
    settings_path = tmp_path / "settings.json"
    install(path=settings_path, agent="gemini")
    installed, msg = status(path=settings_path, agent="gemini")
    assert installed
    assert "installed" in msg.lower()
    assert "Gemini CLI" in msg


def test_gemini_status_not_installed(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{}")
    installed, msg = status(path=settings_path, agent="gemini")
    assert not installed
    assert "not installed" in msg.lower()


def test_gemini_status_missing_file(tmp_path):
    settings_path = tmp_path / "nonexistent.json"
    installed, _msg = status(path=settings_path, agent="gemini")
    assert not installed


# ---------------------------------------------------------------------------
# Cross-agent tests
# ---------------------------------------------------------------------------


def test_claude_and_gemini_independent(tmp_path):
    """Installing one agent doesn't affect the other (different files)."""
    claude_path = tmp_path / "claude_settings.json"
    gemini_path = tmp_path / "gemini_settings.json"

    install(path=claude_path, agent="claude")
    install(path=gemini_path, agent="gemini")

    claude_installed, _ = status(path=claude_path, agent="claude")
    gemini_installed, _ = status(path=gemini_path, agent="gemini")
    assert claude_installed
    assert gemini_installed

    # Uninstall claude doesn't affect gemini
    uninstall(path=claude_path, agent="claude")
    claude_installed, _ = status(path=claude_path, agent="claude")
    gemini_installed, _ = status(path=gemini_path, agent="gemini")
    assert not claude_installed
    assert gemini_installed
