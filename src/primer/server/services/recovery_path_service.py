from __future__ import annotations

import re
from dataclasses import dataclass

from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.server.services.session_signal_parsing import (
    extract_command,
    message_payload,
    normalize_tool_name,
)

_REVERT_COMMAND_PATTERNS = (
    re.compile(r"\bgit\s+checkout\b"),
    re.compile(r"\bgit\s+restore\b"),
    re.compile(r"\bgit\s+revert\b"),
    re.compile(r"\bgit\s+reset\b"),
    re.compile(r"\brollback\b"),
    re.compile(r"\brevert\b"),
)
_INSPECT_TOOL_KEYWORDS = ("read", "grep", "glob", "search", "fetch", "open")
_EDIT_TOOL_KEYWORDS = (
    "edit",
    "write",
    "patch",
    "replace",
    "insert",
    "create",
    "new_file",
    "delete",
    "remove",
    "unlink",
    "rename",
    "move",
    "mv",
)
_DELEGATE_TOOL_KEYWORDS = ("task", "agent", "delegate", "team", "sendmessage", "send_message")
_INSPECT_COMMAND_PATTERNS = (
    re.compile(r"(^|\s)(rg|grep|find|fd)\s"),
    re.compile(r"(^|\s)(cat|less|head|tail|sed)\s"),
    re.compile(r"\bgit\s+(status|diff|log|show)\b"),
    re.compile(r"(^|\s)ls\s"),
)

_STRATEGY_ORDER = (
    "inspect_context",
    "edit_fix",
    "revert_or_reset",
    "rerun_verification",
    "delegate_or_parallelize",
)


@dataclass
class RecoveryPathRecord:
    friction_detected: bool
    first_friction_ordinal: int | None
    recovery_step_count: int
    recovery_strategies: list[str]
    recovery_result: str
    final_outcome: str | None
    last_verification_status: str | None
    sample_recovery_commands: list[str]


def extract_recovery_path(
    messages: list[object],
    execution_evidence: list[object],
    facets: object | None = None,
) -> RecoveryPathRecord | None:
    friction_counts = _facet_value(facets, "friction_counts")
    final_outcome = canonical_outcome(_facet_value(facets, "outcome"))
    has_friction_counts = _has_positive_friction_counts(friction_counts)
    failed_ordinals = [
        _evidence_int(evidence, "ordinal")
        for evidence in execution_evidence
        if _evidence_value(evidence, "status") == "failed"
    ]
    friction_detected = has_friction_counts or bool(failed_ordinals)
    if not friction_detected:
        return None

    first_friction_ordinal = min(failed_ordinals) if failed_ordinals else 0
    recovery_step_ordinals: set[int] = set()
    strategies_used: set[str] = set()
    sample_commands: list[str] = []
    last_verification_status: str | None = None
    post_friction_pass = False

    for evidence in execution_evidence:
        ordinal = _evidence_int(evidence, "ordinal")
        if ordinal <= first_friction_ordinal:
            continue

        recovery_step_ordinals.add(ordinal)
        strategies_used.add("rerun_verification")
        last_verification_status = _string_value(_evidence_value(evidence, "status"))
        if last_verification_status == "passed":
            post_friction_pass = True

        command = _string_value(_evidence_value(evidence, "command"))
        if command:
            _append_sample_command(sample_commands, command)

    for message in messages:
        payload = message_payload(message)
        if payload is None:
            continue

        ordinal = int(payload.get("ordinal", 0) or 0)
        if ordinal <= first_friction_ordinal:
            continue

        tool_calls = payload.get("tool_calls")
        if not isinstance(tool_calls, list):
            continue

        message_had_recovery_signal = False
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue

            tool_name = normalize_tool_name(tool_call.get("name"))
            if not tool_name:
                continue

            command = extract_command(tool_call.get("input_preview"))
            strategies = _classify_recovery_strategies(tool_name, command)
            if not strategies:
                continue

            message_had_recovery_signal = True
            strategies_used.update(strategies)
            if command:
                _append_sample_command(sample_commands, command)

        if message_had_recovery_signal:
            recovery_step_ordinals.add(ordinal)

    recovered = post_friction_pass or (is_success_outcome(final_outcome) and friction_detected)
    if recovered:
        recovery_result = "recovered"
    elif final_outcome == "abandoned":
        recovery_result = "abandoned"
    else:
        recovery_result = "unresolved"

    return RecoveryPathRecord(
        friction_detected=True,
        first_friction_ordinal=first_friction_ordinal,
        recovery_step_count=len(recovery_step_ordinals),
        recovery_strategies=[
            strategy for strategy in _STRATEGY_ORDER if strategy in strategies_used
        ],
        recovery_result=recovery_result,
        final_outcome=final_outcome,
        last_verification_status=last_verification_status,
        sample_recovery_commands=sample_commands,
    )


def _facet_value(facets: object | None, field: str) -> object:
    if facets is None:
        return None
    if isinstance(facets, dict):
        return facets.get(field)
    return getattr(facets, field, None)


def _evidence_value(evidence: object, field: str) -> object:
    if isinstance(evidence, dict):
        return evidence.get(field)
    return getattr(evidence, field, None)


def _evidence_int(evidence: object, field: str) -> int:
    try:
        return int(_evidence_value(evidence, field) or 0)
    except (TypeError, ValueError):
        return 0


def _string_value(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _has_positive_friction_counts(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    for count in value.values():
        try:
            if int(count) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _classify_recovery_strategies(tool_name: str, command: str | None) -> set[str]:
    strategies: set[str] = set()
    if any(keyword in tool_name for keyword in _INSPECT_TOOL_KEYWORDS):
        strategies.add("inspect_context")
    if any(keyword in tool_name for keyword in _EDIT_TOOL_KEYWORDS):
        strategies.add("edit_fix")
    if any(keyword in tool_name for keyword in _DELEGATE_TOOL_KEYWORDS):
        strategies.add("delegate_or_parallelize")

    if not command:
        return strategies

    normalized_command = command.lower()
    if any(pattern.search(normalized_command) for pattern in _INSPECT_COMMAND_PATTERNS):
        strategies.add("inspect_context")
    if any(pattern.search(normalized_command) for pattern in _REVERT_COMMAND_PATTERNS):
        strategies.add("revert_or_reset")
    if _looks_like_edit_command(normalized_command):
        strategies.add("edit_fix")
    if _looks_like_verification_command(normalized_command):
        strategies.add("rerun_verification")
    return strategies


def _looks_like_edit_command(command: str) -> bool:
    return bool(
        re.search(r"(^|\s)(sed|perl|python|node)\s", command)
        or re.search(r"\bgit\s+(apply|cherry-pick)\b", command)
        or re.search(r"(^|\s)(mv|cp|rm|touch)\s", command)
    )


def _looks_like_verification_command(command: str) -> bool:
    return any(
        keyword in command
        for keyword in (
            "pytest",
            "vitest",
            "jest",
            "npm test",
            "pnpm test",
            "yarn test",
            "cargo test",
            "go test",
            "ruff",
            "eslint",
            "mypy",
            "pyright",
            "typecheck",
            "npm run build",
            "pnpm build",
            "yarn build",
            "vite build",
            "cargo build",
            "verify",
        )
    )


def _append_sample_command(commands: list[str], command: str) -> None:
    cleaned = command.strip()
    if not cleaned or cleaned in commands:
        return
    if len(commands) < 5:
        commands.append(cleaned[:200])
