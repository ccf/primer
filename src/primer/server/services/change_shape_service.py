from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass

_CREATE_TOOL_KEYWORDS = ("create", "new_file")
_DELETE_TOOL_KEYWORDS = ("delete", "remove", "unlink")
_RENAME_TOOL_KEYWORDS = ("rename", "move", "mv")
_EDIT_TOOL_KEYWORDS = ("edit", "patch", "replace", "insert", "write")
_WRITE_REWRITE_TOOL_KEYWORDS = ("write", "overwrite")
_PATH_FIELD_NAMES = {
    "path",
    "paths",
    "file",
    "files",
    "filepath",
    "file_path",
    "file_paths",
    "target",
    "targets",
    "target_file",
    "target_files",
    "destination",
    "destination_path",
    "destination_file",
    "source",
    "source_path",
    "source_file",
    "old_path",
    "new_path",
    "old_file_path",
    "new_file_path",
}
_REVERT_COMMAND_PATTERNS = (
    re.compile(r"\bgit\s+checkout\b"),
    re.compile(r"\bgit\s+restore\b"),
    re.compile(r"\bgit\s+revert\b"),
    re.compile(r"\bgit\s+reset\b"),
    re.compile(r"\brollback\b"),
    re.compile(r"\brevert\b"),
)


@dataclass
class ChangeShapeRecord:
    files_touched_count: int
    named_touched_files: list[str]
    commit_files_changed: int
    lines_added: int
    lines_deleted: int
    diff_size: int
    edit_operations: int
    create_operations: int
    delete_operations: int
    rename_operations: int
    churn_files_count: int
    rewrite_indicator: bool
    revert_indicator: bool


def extract_change_shape(
    messages: list[object],
    commits: list[object],
) -> ChangeShapeRecord | None:
    touched_files: Counter[str] = Counter()
    commit_files_changed = 0
    lines_added = 0
    lines_deleted = 0
    edit_operations = 0
    create_operations = 0
    delete_operations = 0
    rename_operations = 0
    rewrite_indicator = False
    revert_indicator = False

    for message in messages:
        payload = _message_payload(message)
        if payload is None:
            continue

        tool_calls = payload.get("tool_calls")
        if not isinstance(tool_calls, list):
            continue

        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue

            tool_name = _normalize_string(tool_call.get("name"))
            if not tool_name:
                continue

            input_preview = tool_call.get("input_preview")
            command = _extract_command(input_preview)
            if command and _is_revert_command(command):
                revert_indicator = True

            operation = _classify_operation(tool_name, command)
            if operation is None:
                continue

            if operation == "edit":
                edit_operations += 1
            elif operation == "create":
                create_operations += 1
            elif operation == "delete":
                delete_operations += 1
            elif operation == "rename":
                rename_operations += 1

            if operation == "edit" and any(
                keyword in tool_name for keyword in _WRITE_REWRITE_TOOL_KEYWORDS
            ):
                rewrite_indicator = True

            for path in _extract_paths(input_preview):
                touched_files[path] += 1

    for commit in commits:
        commit_files_changed += _safe_non_negative_int(_commit_value(commit, "files_changed"))
        lines_added += _safe_non_negative_int(_commit_value(commit, "lines_added"))
        lines_deleted += _safe_non_negative_int(_commit_value(commit, "lines_deleted"))

        commit_message = _normalize_string(
            _commit_value(commit, "commit_message") or _commit_value(commit, "message")
        )
        if commit_message and "revert" in commit_message:
            revert_indicator = True

    diff_size = lines_added + lines_deleted
    if diff_size >= 400 and lines_added > 0 and lines_deleted > 0:
        rewrite_indicator = True

    files_touched_count = len(touched_files)
    if commit_files_changed > files_touched_count:
        files_touched_count = commit_files_changed

    churn_files_count = sum(1 for count in touched_files.values() if count > 1)
    named_touched_files = [
        path for path, _count in sorted(touched_files.items(), key=lambda item: (-item[1], item[0]))
    ][:20]

    if (
        files_touched_count == 0
        and diff_size == 0
        and edit_operations == 0
        and create_operations == 0
        and delete_operations == 0
        and rename_operations == 0
        and not rewrite_indicator
        and not revert_indicator
    ):
        return None

    return ChangeShapeRecord(
        files_touched_count=files_touched_count,
        named_touched_files=named_touched_files,
        commit_files_changed=commit_files_changed,
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        diff_size=diff_size,
        edit_operations=edit_operations,
        create_operations=create_operations,
        delete_operations=delete_operations,
        rename_operations=rename_operations,
        churn_files_count=churn_files_count,
        rewrite_indicator=rewrite_indicator,
        revert_indicator=revert_indicator,
    )


def _message_payload(message: object) -> dict | None:
    if isinstance(message, dict):
        return message
    model_dump = getattr(message, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        return dumped if isinstance(dumped, dict) else None
    payload: dict[str, object] = {}
    for field in ("ordinal", "role", "content_text", "tool_calls", "tool_results"):
        value = getattr(message, field, None)
        if value is not None:
            payload[field] = value
    return payload or None


def _commit_value(commit: object, field: str) -> object:
    if isinstance(commit, dict):
        return commit.get(field)
    return getattr(commit, field, None)


def _normalize_string(value: object) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def _safe_non_negative_int(value: object) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(number, 0)


def _extract_command(input_preview: object) -> str | None:
    if not isinstance(input_preview, str):
        return None

    text = input_preview.strip()
    if not text:
        return None

    parsed = _load_json_object(text)
    if parsed is not None:
        command = _find_command(parsed)
        return command[:1000] if command else None

    return text[:1000]


def _load_json_object(text: str) -> dict | list | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict | list) else None


def _find_command(value: object) -> str | None:
    if isinstance(value, dict):
        for key in ("command", "cmd"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for nested in value.values():
            command = _find_command(nested)
            if command:
                return command
    elif isinstance(value, list):
        for item in value:
            command = _find_command(item)
            if command:
                return command
    return None


def _classify_operation(tool_name: str, command: str | None) -> str | None:
    if any(keyword in tool_name for keyword in _DELETE_TOOL_KEYWORDS):
        return "delete"
    if any(keyword in tool_name for keyword in _RENAME_TOOL_KEYWORDS):
        return "rename"
    if any(keyword in tool_name for keyword in _CREATE_TOOL_KEYWORDS):
        return "create"
    if any(keyword in tool_name for keyword in _EDIT_TOOL_KEYWORDS):
        return "edit"

    if not command:
        return None

    normalized_command = command.lower()
    if "git checkout" in normalized_command or "git restore" in normalized_command:
        return "edit"
    if re.search(r"(^|\s)(rm|git rm)\s", normalized_command):
        return "delete"
    if re.search(r"(^|\s)mv\s", normalized_command):
        return "rename"
    return None


def _is_revert_command(command: str) -> bool:
    normalized_command = command.lower()
    return any(pattern.search(normalized_command) for pattern in _REVERT_COMMAND_PATTERNS)


def _extract_paths(input_preview: object) -> set[str]:
    if not isinstance(input_preview, str):
        return set()

    parsed = _load_json_object(input_preview.strip())
    if parsed is None:
        return set()

    paths: set[str] = set()
    _collect_paths(parsed, paths)
    return paths


def _collect_paths(value: object, paths: set[str], field_name: str | None = None) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            _collect_paths(nested, paths, key.lower())
        return

    if isinstance(value, list):
        for item in value:
            _collect_paths(item, paths, field_name)
        return

    if not isinstance(value, str) or field_name not in _PATH_FIELD_NAMES:
        return

    normalized = value.strip()
    if normalized:
        paths.add(normalized)
