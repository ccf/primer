"""Hook installation management for AI coding agents.

Supports Claude Code (~/.claude/settings.json) and Gemini CLI (~/.gemini/settings.json)
with their respective hook JSON structures.
"""

import json
from dataclasses import dataclass
from pathlib import Path

HOOK_NAME = "primer-hook"


@dataclass
class AgentHookConfig:
    """Configuration for an agent's hook system."""

    agent_name: str
    settings_path: Path
    hook_command: str
    hook_format: str  # "claude" or "gemini"


AGENT_CONFIGS: dict[str, AgentHookConfig] = {
    "claude": AgentHookConfig(
        agent_name="Claude Code",
        settings_path=Path.home() / ".claude" / "settings.json",
        hook_command="python -m primer.hook.session_end",
        hook_format="claude",
    ),
    "gemini": AgentHookConfig(
        agent_name="Gemini CLI",
        settings_path=Path.home() / ".gemini" / "settings.json",
        hook_command="python -m primer.hook.session_end --agent gemini",
        hook_format="gemini",
    ),
}

# Backward-compatible aliases
SETTINGS_PATH = AGENT_CONFIGS["claude"].settings_path
HOOK_COMMAND = AGENT_CONFIGS["claude"].hook_command


def get_supported_agents() -> list[str]:
    """Return list of agent names that support hook installation."""
    return list(AGENT_CONFIGS.keys())


def _get_config(agent: str) -> AgentHookConfig:
    """Look up agent config, raising ValueError for unknown agents."""
    if agent not in AGENT_CONFIGS:
        raise ValueError(f"Unknown agent '{agent}'. Supported: {', '.join(AGENT_CONFIGS)}")
    return AGENT_CONFIGS[agent]


def _resolve_settings_path(path: Path | None, config: AgentHookConfig, agent: str) -> Path:
    """Honor explicit path overrides and backward-compatible Claude aliases."""
    if path is not None:
        return path
    if agent == "claude":
        return SETTINGS_PATH
    return config.settings_path


def _resolve_hook_command(config: AgentHookConfig, agent: str) -> str:
    """Honor backward-compatible Claude command overrides used by tests/tools."""
    if agent == "claude":
        return HOOK_COMMAND
    return config.hook_command


def _with_resolved_compat_overrides(config: AgentHookConfig, agent: str) -> AgentHookConfig:
    """Return a config with any backward-compatible overrides applied."""
    return AgentHookConfig(
        agent_name=config.agent_name,
        settings_path=config.settings_path,
        hook_command=_resolve_hook_command(config, agent),
        hook_format=config.hook_format,
    )


def _load_settings(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _save_settings(settings: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(settings, f, indent=2)


# ---------------------------------------------------------------------------
# Claude Code format helpers
#
# Claude Code uses a matcher-wrapped hook structure:
#   {
#     "EVENT_NAME": [
#       {
#         "matcher": "",
#         "hooks": [
#           {"type": "command", "command": "...", "timeout": 30}
#         ]
#       }
#     ]
#   }
#
# Timeouts are specified in SECONDS (not milliseconds).
#
# Detection also handles a legacy flat format that earlier versions of this
# installer wrote (`{"command": ..., "timeout": ...}` directly at the event
# level) so reinstall / uninstall can migrate existing users.
# ---------------------------------------------------------------------------

_CLAUDE_HOOK_TIMEOUT_SECONDS = 30


def _find_hook_claude(event_hooks: list, command: str) -> bool:
    """Check if the Primer hook is present in a Claude event hook list.

    Detects both the current matcher-wrapped format and the legacy flat format
    written by earlier versions of this installer.
    """
    for entry in event_hooks:
        # Legacy flat format: {"command": cmd, ...}
        if isinstance(entry, dict) and entry.get("command") == command:
            return True
        if isinstance(entry, str) and entry == command:
            return True
        # Current matcher-wrapped format: {"matcher": ..., "hooks": [{"command": cmd}]}
        if isinstance(entry, dict):
            inner_hooks = entry.get("hooks", [])
            if isinstance(inner_hooks, list):
                for inner in inner_hooks:
                    if isinstance(inner, dict) and inner.get("command") == command:
                        return True
    return False


def _new_claude_hook_entry(command: str) -> dict:
    """Build a matcher-wrapped hook entry in Claude Code's expected schema."""
    return {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": _CLAUDE_HOOK_TIMEOUT_SECONDS,
            }
        ],
    }


def _install_claude(settings: dict, config: AgentHookConfig) -> bool:
    """Add the Primer hook to Claude Code settings. Returns True if already present.

    Registers the hook under both SessionEnd and PreCompact so that long-running
    sessions are captured incrementally (on each compaction) rather than only at
    exit.  The server's upsert logic handles repeated ingestion of the same
    session_id gracefully.
    """
    hooks = settings.setdefault("hooks", {})
    already_end = False
    already_compact = False

    session_end_hooks = hooks.setdefault("SessionEnd", [])
    if _find_hook_claude(session_end_hooks, config.hook_command):
        already_end = True
    else:
        session_end_hooks.append(_new_claude_hook_entry(config.hook_command))

    pre_compact_hooks = hooks.setdefault("PreCompact", [])
    if _find_hook_claude(pre_compact_hooks, config.hook_command):
        already_compact = True
    else:
        pre_compact_hooks.append(_new_claude_hook_entry(config.hook_command))

    return already_end and already_compact


def _uninstall_claude(settings: dict, config: AgentHookConfig) -> bool:
    """Remove the Primer hook from Claude Code settings. Returns True if found.

    Handles both the current matcher-wrapped format and the legacy flat format.
    Third-party entries are left untouched — including matcher entries whose
    `hooks` array is already empty, which would otherwise be collapsed to None.
    """
    hooks = settings.get("hooks", {})
    command = config.hook_command
    found = False

    for event in ("SessionEnd", "PreCompact"):
        event_hooks = hooks.get(event, [])
        if not _find_hook_claude(event_hooks, command):
            continue
        found = True
        new_list: list = []
        for entry in event_hooks:
            # Legacy flat: drop entirely if it matches
            if isinstance(entry, str) and entry == command:
                continue
            if isinstance(entry, dict) and entry.get("command") == command:
                continue
            # Matcher-wrapped: strip our command only if this entry contains
            # it. Third-party entries pass through unchanged — including ones
            # that happen to have an empty `hooks` array already.
            if isinstance(entry, dict) and isinstance(entry.get("hooks"), list):
                inner = entry["hooks"]
                if any(isinstance(h, dict) and h.get("command") == command for h in inner):
                    remaining = [
                        h
                        for h in inner
                        if not (isinstance(h, dict) and h.get("command") == command)
                    ]
                    if remaining:
                        cleaned = dict(entry)
                        cleaned["hooks"] = remaining
                        new_list.append(cleaned)
                    # else: entry held only our command → drop it
                    continue
            new_list.append(entry)
        hooks[event] = new_list

    return found


def _status_claude(settings: dict, config: AgentHookConfig) -> bool:
    """Check if Primer hook is installed in Claude Code settings."""
    hooks = settings.get("hooks", {})
    # Consider installed if at least SessionEnd is registered
    session_end_hooks = hooks.get("SessionEnd", [])
    return _find_hook_claude(session_end_hooks, config.hook_command)


# ---------------------------------------------------------------------------
# Gemini CLI format helpers
#
# Gemini uses a matcher-wrapped structure:
# {"hooks": [{"matcher": "exit", "hooks": [{"name": "...", "type": "command", "command": "..."}]}]}
# ---------------------------------------------------------------------------


def _find_hook_gemini(settings: dict, config: AgentHookConfig) -> bool:
    """Check if the Primer hook exists in Gemini-format settings."""
    hooks_list = settings.get("hooks", [])
    if not isinstance(hooks_list, list):
        return False

    for matcher_entry in hooks_list:
        if not isinstance(matcher_entry, dict):
            continue
        if matcher_entry.get("matcher") != "exit":
            continue
        inner_hooks = matcher_entry.get("hooks", [])
        for hook in inner_hooks:
            if isinstance(hook, dict) and hook.get("command") == config.hook_command:
                return True
    return False


def _install_gemini(settings: dict, config: AgentHookConfig) -> bool:
    """Add the Primer hook to Gemini CLI settings. Returns True if already present."""
    if _find_hook_gemini(settings, config):
        return True

    hooks_list = settings.setdefault("hooks", [])
    if not isinstance(hooks_list, list):
        settings["hooks"] = []
        hooks_list = settings["hooks"]

    # Find existing "exit" matcher entry or create one
    exit_entry = None
    for entry in hooks_list:
        if isinstance(entry, dict) and entry.get("matcher") == "exit":
            exit_entry = entry
            break

    if exit_entry is None:
        exit_entry = {"matcher": "exit", "hooks": []}
        hooks_list.append(exit_entry)

    inner_hooks = exit_entry.setdefault("hooks", [])
    inner_hooks.append(
        {
            "name": HOOK_NAME,
            "type": "command",
            "command": config.hook_command,
        }
    )
    return False


def _uninstall_gemini(settings: dict, config: AgentHookConfig) -> bool:
    """Remove the Primer hook from Gemini CLI settings. Returns True if found."""
    if not _find_hook_gemini(settings, config):
        return False

    hooks_list = settings.get("hooks", [])
    for matcher_entry in hooks_list:
        if not isinstance(matcher_entry, dict):
            continue
        if matcher_entry.get("matcher") != "exit":
            continue
        inner_hooks = matcher_entry.get("hooks", [])
        matcher_entry["hooks"] = [
            h
            for h in inner_hooks
            if not (isinstance(h, dict) and h.get("command") == config.hook_command)
        ]
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def install(path: Path | None = None, agent: str = "claude") -> tuple[bool, str]:
    """Install the Primer SessionEnd hook for the given agent.

    Returns (success, message).
    """
    config = _with_resolved_compat_overrides(_get_config(agent), agent)
    settings_path = _resolve_settings_path(path, config, agent)
    settings = _load_settings(settings_path)

    if config.hook_format == "gemini":
        already = _install_gemini(settings, config)
    else:
        already = _install_claude(settings, config)

    if already:
        return True, f"Primer hook already installed for {config.agent_name}."

    _save_settings(settings, settings_path)
    return True, f"Primer hook installed for {config.agent_name} in {settings_path}"


def uninstall(path: Path | None = None, agent: str = "claude") -> tuple[bool, str]:
    """Remove the Primer SessionEnd hook for the given agent.

    Returns (success, message).
    """
    config = _with_resolved_compat_overrides(_get_config(agent), agent)
    settings_path = _resolve_settings_path(path, config, agent)
    settings = _load_settings(settings_path)

    if config.hook_format == "gemini":
        found = _uninstall_gemini(settings, config)
    else:
        found = _uninstall_claude(settings, config)

    if not found:
        return True, f"Primer hook not found for {config.agent_name} (nothing to remove)."

    _save_settings(settings, settings_path)
    return True, f"Primer hook removed for {config.agent_name}."


def status(path: Path | None = None, agent: str = "claude") -> tuple[bool, str]:
    """Check whether the Primer hook is installed for the given agent.

    Returns (installed, message).
    """
    config = _with_resolved_compat_overrides(_get_config(agent), agent)
    settings_path = _resolve_settings_path(path, config, agent)
    settings = _load_settings(settings_path)

    if config.hook_format == "gemini":
        installed = _find_hook_gemini(settings, config)
    else:
        installed = _status_claude(settings, config)

    if installed:
        return True, f"Primer hook is installed for {config.agent_name}."
    return False, f"Primer hook is not installed for {config.agent_name}."
