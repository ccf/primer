from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass

_EXECUTION_TOOL_NAMES = {
    "bash",
    "exec_command",
    "run_terminal_command",
    "run_terminal_command_v2",
    "shell",
    "terminal",
}

_TEST_KEYWORDS = (
    "pytest",
    "vitest",
    "jest",
    "go test",
    "cargo test",
    "npm test",
    "pnpm test",
    "yarn test",
    "bun test",
    "rspec",
    "phpunit",
    "mvn test",
    "gradle test",
    "ctest",
)

_LINT_KEYWORDS = (
    "ruff",
    "eslint",
    "flake8",
    "pylint",
    "shellcheck",
    "rubocop",
    "stylelint",
    "prettier",
    "biome",
)

_BUILD_KEYWORDS = (
    "npm run build",
    "pnpm build",
    "yarn build",
    "bun run build",
    "vite build",
    "cargo build",
    "go build",
    "make build",
    "bazel build",
    "gradle build",
    "mvn package",
    "mvn compile",
    "webpack",
    "tsc -b",
)

_VERIFICATION_KEYWORDS = (
    "check",
    "typecheck",
    "verify",
    "validate",
    "validation",
    "smoke",
    "e2e",
    "integration",
    "cargo check",
    "mypy",
    "pyright",
    "tsc --noemit",
)

_FAILURE_KEYWORDS = (
    "failed",
    "failure",
    "error",
    "errors",
    "traceback",
    "exception",
    "fatal",
    "command failed",
    "exit code",
    '"success": false',
    '"ok": false',
)

_SUCCESS_KEYWORDS = (
    "all checks passed",
    "no issues found",
    "build succeeded",
    "build completed successfully",
    "compiled successfully",
    "test result: ok",
    "0 failed",
    '"success": true',
    '"ok": true',
)


@dataclass
class ExecutionEvidenceRecord:
    ordinal: int
    evidence_type: str
    status: str = "unknown"
    tool_name: str | None = None
    command: str | None = None
    output_preview: str | None = None


def extract_execution_evidence(messages: list[object]) -> list[ExecutionEvidenceRecord]:
    records: list[ExecutionEvidenceRecord] = []
    pending_by_tool: dict[str, deque[ExecutionEvidenceRecord]] = defaultdict(deque)

    for message in messages:
        payload = _message_payload(message)
        if payload is None:
            continue

        ordinal = int(payload.get("ordinal", 0) or 0)

        tool_calls = payload.get("tool_calls")
        if isinstance(tool_calls, list):
            for tool_call in tool_calls:
                record = _record_from_tool_call(ordinal, tool_call)
                if record is None:
                    continue
                records.append(record)
                pending_by_tool[_normalize_tool_name(record.tool_name)].append(record)

        tool_results = payload.get("tool_results")
        if isinstance(tool_results, list):
            for tool_result in tool_results:
                _apply_tool_result(ordinal, tool_result, pending_by_tool, records)

    return records


def _message_payload(message: object) -> dict | None:
    if isinstance(message, dict):
        return message
    model_dump = getattr(message, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        return dumped if isinstance(dumped, dict) else None
    return None


def _record_from_tool_call(ordinal: int, tool_call: object) -> ExecutionEvidenceRecord | None:
    if not isinstance(tool_call, dict):
        return None

    tool_name = tool_call.get("name")
    if not isinstance(tool_name, str) or not tool_name:
        return None

    input_preview = tool_call.get("input_preview")
    command = _extract_command(input_preview)
    if not _is_execution_tool(tool_name) and not command:
        return None

    evidence_type = _classify_evidence_type(command)
    if evidence_type is None:
        return None

    return ExecutionEvidenceRecord(
        ordinal=ordinal,
        evidence_type=evidence_type,
        tool_name=tool_name,
        command=command,
    )


def _apply_tool_result(
    ordinal: int,
    tool_result: object,
    pending_by_tool: dict[str, deque[ExecutionEvidenceRecord]],
    records: list[ExecutionEvidenceRecord],
) -> None:
    if not isinstance(tool_result, dict):
        return

    tool_name = tool_result.get("name")
    output_preview = tool_result.get("output_preview")
    if not isinstance(tool_name, str) or not tool_name:
        return
    if not isinstance(output_preview, str) or not output_preview:
        return

    normalized_tool_name = _normalize_tool_name(tool_name)
    status = _classify_status(output_preview)
    output_preview = output_preview[:1000]

    if pending_by_tool[normalized_tool_name]:
        record = pending_by_tool[normalized_tool_name].popleft()
        record.ordinal = max(record.ordinal, ordinal)
        record.output_preview = output_preview
        record.status = status
        return

    evidence_type = _classify_evidence_type(output_preview)
    if evidence_type is None:
        return

    records.append(
        ExecutionEvidenceRecord(
            ordinal=ordinal,
            evidence_type=evidence_type,
            status=status,
            tool_name=tool_name,
            output_preview=output_preview,
        )
    )


def _is_execution_tool(tool_name: str) -> bool:
    return _normalize_tool_name(tool_name) in _EXECUTION_TOOL_NAMES


def _normalize_tool_name(tool_name: str | None) -> str:
    return tool_name.strip().lower() if isinstance(tool_name, str) else ""


def _extract_command(input_preview: object) -> str | None:
    if not isinstance(input_preview, str):
        return None

    text = input_preview.strip()
    if not text:
        return None

    parsed = _load_json_object(text)
    if parsed is not None:
        command = _find_command(parsed)
        if command:
            return command[:1000]

    return text[:1000]


def _load_json_object(text: str) -> object | None:
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


def _classify_evidence_type(text: str | None) -> str | None:
    if not text:
        return None

    normalized = text.lower()

    if any(keyword in normalized for keyword in _TEST_KEYWORDS):
        return "test"
    if any(keyword in normalized for keyword in _LINT_KEYWORDS):
        return "lint"
    if any(keyword in normalized for keyword in _BUILD_KEYWORDS):
        return "build"
    if any(keyword in normalized for keyword in _VERIFICATION_KEYWORDS):
        return "verification"
    return None


def _classify_status(output_preview: str) -> str:
    normalized = output_preview.lower()
    if any(keyword in normalized for keyword in _FAILURE_KEYWORDS):
        return "failed"
    if any(keyword in normalized for keyword in _SUCCESS_KEYWORDS):
        return "passed"
    if "passed" in normalized and "failed" not in normalized:
        return "passed"
    return "unknown"
