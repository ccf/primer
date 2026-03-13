from __future__ import annotations

import json


def message_payload(message: object) -> dict | None:
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


def normalize_tool_name(tool_name: str | None) -> str:
    return tool_name.strip().lower() if isinstance(tool_name, str) else ""


def extract_command(input_preview: object) -> str | None:
    if not isinstance(input_preview, str):
        return None

    text = input_preview.strip()
    if not text:
        return None

    parsed = load_json_object(text)
    if parsed is not None:
        command = _find_command(parsed)
        return command[:1000] if command else None

    return text[:1000]


def load_json_object(text: str) -> object | None:
    if not text or text[0] not in "{[":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _find_command(value: object) -> str | None:
    if isinstance(value, dict):
        for key in (
            "command",
            "cmd",
            "script",
            "commandString",
            "raw_command",
            "rawCommand",
        ):
            child = value.get(key)
            command = _command_from_child(child)
            if command:
                return command
        for key in ("argv", "args"):
            child = value.get(key)
            command = _command_from_child(child)
            if command:
                return command
        for child in value.values():
            command = _find_command(child)
            if command:
                return command
    elif isinstance(value, list):
        command = _command_from_child(value)
        if command:
            return command
        for child in value:
            command = _find_command(child)
            if command:
                return command
    return None


def _command_from_child(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list):
        parts = [str(part).strip() for part in value if str(part).strip()]
        if parts:
            return " ".join(parts)
    return None
