from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


_CUSTOMIZATION_DIRS: dict[str, tuple[str, str]] = {
    "commands": ("command", "commands"),
    "agents": ("subagent", "agents"),
    "subagents": ("subagent", "subagents"),
    "skills": ("skill", "skills"),
    "templates": ("template", "templates"),
}


@dataclass(slots=True)
class CustomizationSnapshot:
    customization_type: str
    state: str
    identifier: str
    provenance: str
    display_name: str | None = None
    source_path: str | None = None
    invocation_count: int = 0
    details: dict[str, object] | None = None

    def key(self) -> tuple[str, str, str, str, str | None]:
        return (
            self.customization_type,
            self.state,
            self.identifier,
            self.provenance,
            self.source_path,
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "customization_type": self.customization_type,
            "state": self.state,
            "identifier": self.identifier,
            "provenance": self.provenance,
            "display_name": self.display_name,
            "source_path": self.source_path,
            "invocation_count": self.invocation_count,
            "details": self.details,
        }


def build_session_customizations(
    agent_type: str,
    project_path: str | None,
    tool_counts: Mapping[str, int],
) -> list[CustomizationSnapshot]:
    snapshots = []
    snapshots.extend(_derive_invoked_customizations(tool_counts))
    snapshots.extend(_collect_enabled_project_customizations(project_path))
    if agent_type == "claude_code":
        snapshots.extend(_collect_enabled_claude_user_customizations())
    return _dedupe_snapshots(snapshots)


def derive_invoked_customizations_from_tool_usages(
    tool_usages: list[object] | None,
) -> list[CustomizationSnapshot]:
    if not tool_usages:
        return []

    tool_counts: dict[str, int] = {}
    for usage in tool_usages:
        if isinstance(usage, dict):
            tool_name = usage.get("tool_name")
            call_count = usage.get("call_count", 0)
        else:
            tool_name = getattr(usage, "tool_name", None)
            call_count = getattr(usage, "call_count", 0)

        if not isinstance(tool_name, str) or not tool_name:
            continue

        try:
            normalized_count = max(int(call_count), 0)
        except (TypeError, ValueError):
            normalized_count = 0
        if normalized_count <= 0:
            continue
        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + normalized_count

    return _derive_invoked_customizations(tool_counts)


def _derive_invoked_customizations(
    tool_counts: Mapping[str, int],
) -> list[CustomizationSnapshot]:
    snapshots: list[CustomizationSnapshot] = []
    mcp_counts: dict[str, int] = {}

    for tool_name, raw_count in tool_counts.items():
        if not isinstance(tool_name, str) or not tool_name:
            continue
        call_count = max(int(raw_count), 0)
        if call_count <= 0:
            continue

        if tool_name.startswith("Skill:"):
            identifier = tool_name.split(":", 1)[1].strip() or tool_name
            snapshots.append(
                CustomizationSnapshot(
                    customization_type="skill",
                    state="invoked",
                    identifier=identifier,
                    display_name=identifier,
                    provenance="unknown",
                    invocation_count=call_count,
                    details={"raw_tool_name": tool_name},
                )
            )
            continue

        if tool_name.startswith("Task:"):
            identifier = tool_name.split(":", 1)[1].strip() or tool_name
            snapshots.append(
                CustomizationSnapshot(
                    customization_type="subagent",
                    state="invoked",
                    identifier=identifier,
                    display_name=identifier,
                    provenance="unknown",
                    invocation_count=call_count,
                    details={"raw_tool_name": tool_name},
                )
            )
            continue

        mcp_identifier = _mcp_identifier(tool_name)
        if mcp_identifier:
            mcp_counts[mcp_identifier] = mcp_counts.get(mcp_identifier, 0) + call_count

    for identifier, call_count in mcp_counts.items():
        snapshots.append(
            CustomizationSnapshot(
                customization_type="mcp",
                state="invoked",
                identifier=identifier,
                display_name=identifier,
                provenance="unknown",
                invocation_count=call_count,
            )
        )

    return _dedupe_snapshots(snapshots)


def _collect_enabled_project_customizations(
    project_path: str | None,
) -> list[CustomizationSnapshot]:
    if not project_path:
        return []

    snapshots: list[CustomizationSnapshot] = []
    for root in _candidate_project_roots(project_path):
        claude_dir = root / ".claude"
        if not claude_dir.exists():
            continue
        snapshots.extend(_scan_customization_dirs(claude_dir, provenance="repo_defined"))
        settings_path = claude_dir / "settings.json"
        snapshots.extend(
            _scan_mcp_settings(
                settings_path,
                provenance="repo_defined",
            )
        )
    return _dedupe_snapshots(snapshots)


def _collect_enabled_claude_user_customizations() -> list[CustomizationSnapshot]:
    claude_home = Path.home() / ".claude"
    if not claude_home.exists():
        return []

    snapshots = _scan_customization_dirs(claude_home, provenance="user_local")
    snapshots.extend(
        _scan_mcp_settings(
            claude_home / "settings.json",
            provenance="user_local",
        )
    )
    return _dedupe_snapshots(snapshots)


def _scan_customization_dirs(
    root: Path,
    *,
    provenance: str,
) -> list[CustomizationSnapshot]:
    snapshots: list[CustomizationSnapshot] = []
    for dirname, (customization_type, folder_label) in _CUSTOMIZATION_DIRS.items():
        base_dir = root / dirname
        if not base_dir.exists():
            continue
        for path in sorted(base_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(base_dir)
            identifier = str(relative.with_suffix("")).replace("\\", "/")
            snapshots.append(
                CustomizationSnapshot(
                    customization_type=customization_type,
                    state="enabled",
                    identifier=identifier,
                    display_name=path.stem,
                    provenance=provenance,
                    source_path=str(path),
                    details={"folder": folder_label},
                )
            )
    return snapshots


_MCP_SENSITIVE_KEYS = frozenset({"env", "headers"})


def _redact_mcp_config(config: dict[str, object]) -> dict[str, object]:
    """Return a copy of an MCP server config with sensitive keys removed."""
    return {k: v for k, v in config.items() if k not in _MCP_SENSITIVE_KEYS}


def _scan_mcp_settings(
    settings_path: Path,
    *,
    provenance: str,
) -> list[CustomizationSnapshot]:
    if not settings_path.exists():
        return []

    try:
        with open(settings_path) as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []

    servers = payload.get("mcpServers", {})
    if not isinstance(servers, dict):
        return []

    snapshots: list[CustomizationSnapshot] = []
    for identifier, config in servers.items():
        if not isinstance(identifier, str) or not identifier:
            continue
        details = _redact_mcp_config(config) if isinstance(config, dict) else {}
        snapshots.append(
            CustomizationSnapshot(
                customization_type="mcp",
                state="enabled",
                identifier=identifier,
                display_name=identifier,
                provenance=provenance,
                source_path=str(settings_path),
                details=details,
            )
        )
    return snapshots


def _candidate_project_roots(project_path: str) -> list[Path]:
    path = Path(project_path).expanduser()
    if not path.exists():
        return []
    if path.is_file():
        path = path.parent

    results: list[Path] = []
    home = Path.home().resolve()
    for candidate in [path.resolve(), *path.resolve().parents]:
        if candidate == home or candidate in home.parents:
            break
        if (candidate / ".claude").exists() or (candidate / ".git").exists():
            results.append(candidate)
    if not results:
        results.append(path.resolve())
    return results[:3]


def _mcp_identifier(tool_name: str) -> str | None:
    if not tool_name.startswith("mcp__"):
        return None

    parts = tool_name.split("__")
    if len(parts) < 3 or not parts[1]:
        return None
    return parts[1]


def _dedupe_snapshots(
    snapshots: list[CustomizationSnapshot],
) -> list[CustomizationSnapshot]:
    merged: dict[tuple[str, str, str, str, str | None], CustomizationSnapshot] = {}
    for snapshot in snapshots:
        key = snapshot.key()
        existing = merged.get(key)
        if existing is None:
            merged[key] = snapshot
            continue

        merged[key] = CustomizationSnapshot(
            customization_type=snapshot.customization_type,
            state=snapshot.state,
            identifier=snapshot.identifier,
            provenance=snapshot.provenance,
            display_name=snapshot.display_name or existing.display_name,
            source_path=snapshot.source_path or existing.source_path,
            invocation_count=existing.invocation_count + snapshot.invocation_count,
            details=snapshot.details or existing.details,
        )

    return sorted(
        merged.values(),
        key=lambda item: (
            item.customization_type,
            item.state,
            item.identifier,
            item.provenance,
            item.source_path or "",
        ),
    )
