"""Tests for primer.hook.installer — install/uninstall/status."""

import json

from primer.hook.installer import HOOK_COMMAND, install, status, uninstall


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
