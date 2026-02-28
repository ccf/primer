"""Hook installation management for Claude Code settings.

Provides install/uninstall/status functions for the Primer SessionEnd hook.
"""

import json
from pathlib import Path

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
HOOK_COMMAND = "python -m primer.hook.session_end"


def _load_settings(path: Path | None = None) -> dict:
    path = path or SETTINGS_PATH
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _save_settings(settings: dict, path: Path | None = None) -> None:
    path = path or SETTINGS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(settings, f, indent=2)


def _find_hook(session_end_hooks: list) -> bool:
    """Check if the Primer hook is already in the list."""
    for hook in session_end_hooks:
        if isinstance(hook, dict) and hook.get("command") == HOOK_COMMAND:
            return True
        if isinstance(hook, str) and hook == HOOK_COMMAND:
            return True
    return False


def install(path: Path | None = None) -> tuple[bool, str]:
    """Install the Primer SessionEnd hook.

    Returns (success, message).
    """
    settings = _load_settings(path)
    hooks = settings.setdefault("hooks", {})
    session_end_hooks = hooks.setdefault("SessionEnd", [])

    if _find_hook(session_end_hooks):
        return True, "Primer hook already installed."

    session_end_hooks.append({"command": HOOK_COMMAND, "timeout": 10000})
    _save_settings(settings, path)
    return True, f"Primer SessionEnd hook installed in {path or SETTINGS_PATH}"


def uninstall(path: Path | None = None) -> tuple[bool, str]:
    """Remove the Primer SessionEnd hook.

    Returns (success, message).
    """
    settings = _load_settings(path)
    hooks = settings.get("hooks", {})
    session_end_hooks = hooks.get("SessionEnd", [])

    if not _find_hook(session_end_hooks):
        return True, "Primer hook not found (nothing to remove)."

    hooks["SessionEnd"] = [
        h
        for h in session_end_hooks
        if not (
            (isinstance(h, dict) and h.get("command") == HOOK_COMMAND)
            or (isinstance(h, str) and h == HOOK_COMMAND)
        )
    ]
    _save_settings(settings, path)
    return True, "Primer SessionEnd hook removed."


def status(path: Path | None = None) -> tuple[bool, str]:
    """Check whether the Primer hook is installed.

    Returns (installed, message).
    """
    settings = _load_settings(path)
    hooks = settings.get("hooks", {})
    session_end_hooks = hooks.get("SessionEnd", [])

    if _find_hook(session_end_hooks):
        return True, "Primer SessionEnd hook is installed."
    return False, "Primer SessionEnd hook is not installed."
