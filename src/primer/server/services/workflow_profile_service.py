from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from primer.server.services.workflow_patterns import (
    _is_delegate_tool,
    infer_workflow_steps,
    workflow_fingerprint_id,
    workflow_fingerprint_label,
)

_SESSION_TYPE_ARCHETYPES = {
    "bug_fix": "debugging",
    "code_modification": "feature_delivery",
    "debugging": "debugging",
    "docs": "docs",
    "documentation": "docs",
    "exploration": "investigation",
    "feature": "feature_delivery",
    "feature_delivery": "feature_delivery",
    "implementation": "feature_delivery",
    "investigation": "investigation",
    "migration": "migration",
    "refactor": "refactor",
    "refactoring": "refactor",
    "research": "investigation",
}
_DOC_TEXT_RE = re.compile(r"\b(?:docs?|documentation|readme|changelog|guide)\b")
_MIGRATION_TEXT_RE = re.compile(r"\b(?:migrat\w*|upgrade|moderniz\w*|deprecat\w*|port(?:ed|ing))\b")


@dataclass
class WorkflowProfileRecord:
    fingerprint_id: str | None
    label: str | None
    steps: list[str]
    archetype: str | None
    archetype_source: str | None
    archetype_reason: str | None
    top_tools: list[str]
    delegation_count: int
    verification_run_count: int


def extract_session_workflow_profile(
    session: object,
    tool_usages: list[object],
    execution_evidence: list[object],
    *,
    change_shape: object | None = None,
    recovery_path: object | None = None,
    facets: object | None = None,
    has_commit: bool = False,
) -> WorkflowProfileRecord | None:
    tool_counts = _tool_counts(tool_usages)
    execution_types = {
        evidence_type
        for evidence in execution_evidence
        if (evidence_type := _string_attr(evidence, "evidence_type"))
    }
    recovery_strategies = {
        strategy
        for strategy in (_list_attr(recovery_path, "recovery_strategies") or [])
        if isinstance(strategy, str) and strategy
    }
    session_type = _string_attr(facets, "session_type")
    has_mutations = _has_mutations(change_shape)
    steps = infer_workflow_steps(
        tool_counts,
        has_commit,
        execution_types=execution_types,
        recovery_strategies=recovery_strategies,
        has_mutations=has_mutations,
    )

    archetype, archetype_source, archetype_reason = _infer_archetype(
        session,
        facets,
        change_shape,
        recovery_path,
        session_type=session_type,
        steps=steps,
        execution_types=execution_types,
        has_commit=has_commit,
    )
    fingerprint_type = session_type or archetype
    fingerprint_id = (
        workflow_fingerprint_id(fingerprint_type, steps) if fingerprint_type or steps else None
    )
    label = workflow_fingerprint_label(fingerprint_type, steps) if fingerprint_id else None
    top_tools = [tool_name for tool_name, _count in tool_counts.most_common(4)]
    delegation_count = sum(
        count for tool_name, count in tool_counts.items() if _is_delegate_tool(tool_name)
    )
    verification_run_count = sum(
        1
        for evidence in execution_evidence
        if _string_attr(evidence, "evidence_type") in {"test", "lint", "build", "verification"}
    )

    if not (
        fingerprint_id
        or archetype
        or top_tools
        or delegation_count > 0
        or verification_run_count > 0
    ):
        return None

    return WorkflowProfileRecord(
        fingerprint_id=fingerprint_id,
        label=label,
        steps=steps,
        archetype=archetype,
        archetype_source=archetype_source,
        archetype_reason=archetype_reason,
        top_tools=top_tools,
        delegation_count=delegation_count,
        verification_run_count=verification_run_count,
    )


def _infer_archetype(
    session: object,
    facets: object | None,
    change_shape: object | None,
    recovery_path: object | None,
    *,
    session_type: str | None,
    steps: list[str],
    execution_types: set[str],
    has_commit: bool,
) -> tuple[str | None, str | None, str | None]:
    normalized_type = session_type.lower() if session_type else None
    mapped = _SESSION_TYPE_ARCHETYPES.get(normalized_type or "")
    if mapped:
        return (
            mapped,
            "session_type",
            f"Mapped from the extracted session type '{normalized_type}'.",
        )

    text = _hint_text(session, facets)
    named_files = _named_files(change_shape)
    if _looks_like_docs(text, named_files):
        return "docs", "heuristic", "Documentation-heavy prompt or changed files suggest docs work."

    if _looks_like_migration(text, change_shape):
        return (
            "migration",
            "heuristic",
            "Prompt hints and broad file changes suggest a migration or upgrade effort.",
        )

    if _looks_like_debugging(execution_types, recovery_path, steps):
        return (
            "debugging",
            "heuristic",
            "Failed verification or recovery behavior suggests a debugging loop.",
        )

    if _looks_like_refactor(text, change_shape):
        return (
            "refactor",
            "heuristic",
            "Rewrite or rename signals point to a refactor-oriented session.",
        )

    if _looks_like_feature_delivery(change_shape, has_commit, steps):
        return (
            "feature_delivery",
            "heuristic",
            "Mutating changes and shipping signals suggest feature delivery work.",
        )

    if _looks_like_investigation(change_shape, has_commit, steps):
        return (
            "investigation",
            "heuristic",
            "Read-heavy activity without durable changes suggests investigation work.",
        )

    return None, None, None


def _tool_counts(tool_usages: list[object]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for usage in tool_usages:
        tool_name = _string_attr(usage, "tool_name")
        if not tool_name:
            continue
        call_count = _int_attr(usage, "call_count")
        counts[tool_name] += max(call_count, 0)
    return counts


def _string_attr(value: object | None, field: str) -> str | None:
    if value is None:
        return None
    candidate = value.get(field) if isinstance(value, dict) else getattr(value, field, None)
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return None


def _int_attr(value: object | None, field: str) -> int:
    if value is None:
        return 0
    candidate = value.get(field) if isinstance(value, dict) else getattr(value, field, None)
    try:
        return int(candidate or 0)
    except (TypeError, ValueError):
        return 0


def _list_attr(value: object | None, field: str) -> list[object] | None:
    if value is None:
        return None
    candidate = value.get(field) if isinstance(value, dict) else getattr(value, field, None)
    return candidate if isinstance(candidate, list) else None


def _hint_text(session: object, facets: object | None) -> str:
    parts = [
        _string_attr(session, "first_prompt"),
        _string_attr(session, "summary"),
        _string_attr(facets, "underlying_goal"),
        _string_attr(facets, "brief_summary"),
    ]
    return " ".join(part.lower() for part in parts if part)


def _named_files(change_shape: object | None) -> list[str]:
    values = _list_attr(change_shape, "named_touched_files") or []
    return [value for value in values if isinstance(value, str) and value]


def _has_mutations(change_shape: object | None) -> bool:
    return any(
        _int_attr(change_shape, field) > 0
        for field in (
            "files_touched_count",
            "diff_size",
            "edit_operations",
            "create_operations",
            "delete_operations",
            "rename_operations",
        )
    )


def _looks_like_docs(text: str, named_files: list[str]) -> bool:
    text_match = bool(_DOC_TEXT_RE.search(text))
    if not named_files:
        return False
    doc_files = 0
    for path in named_files:
        normalized = path.lower()
        if normalized.endswith((".md", ".mdx", ".rst", ".txt")) or "/docs/" in normalized:
            doc_files += 1
    if text_match and doc_files > 0:
        return True
    return doc_files > 0 and doc_files >= max(1, len(named_files) // 2)


def _looks_like_migration(text: str, change_shape: object | None) -> bool:
    if not _MIGRATION_TEXT_RE.search(text):
        return False
    return (
        _int_attr(change_shape, "files_touched_count") >= 2
        or _int_attr(change_shape, "rename_operations") > 0
    )


def _looks_like_debugging(
    execution_types: set[str],
    recovery_path: object | None,
    steps: list[str],
) -> bool:
    if _int_attr(recovery_path, "recovery_step_count") > 0:
        return True
    if _string_attr(recovery_path, "recovery_result") in {"recovered", "unresolved"}:
        return True
    if "fix" in steps:
        return True
    return "test" in execution_types and "edit" in steps


def _looks_like_refactor(text: str, change_shape: object | None) -> bool:
    if "refactor" in text or "cleanup" in text or "restructure" in text:
        return True
    return bool(
        _int_attr(change_shape, "rename_operations") > 0
        or _int_attr(change_shape, "churn_files_count") > 1
        or _bool_attr(change_shape, "rewrite_indicator")
    )


def _looks_like_feature_delivery(
    change_shape: object | None,
    has_commit: bool,
    steps: list[str],
) -> bool:
    if has_commit or "ship" in steps:
        return True
    return bool(
        _int_attr(change_shape, "create_operations") > 0
        or _int_attr(change_shape, "diff_size") > 0
        or _int_attr(change_shape, "files_touched_count") > 0
    )


def _looks_like_investigation(
    change_shape: object | None,
    has_commit: bool,
    steps: list[str],
) -> bool:
    if has_commit or _has_mutations(change_shape):
        return False
    return bool(steps) and set(steps).issubset(
        {"search", "read", "execute", "delegate", "integrate"}
    )


def _bool_attr(value: object | None, field: str) -> bool:
    if value is None:
        return False
    candidate = value.get(field) if isinstance(value, dict) else getattr(value, field, None)
    return bool(candidate)
