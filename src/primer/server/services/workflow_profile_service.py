from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from primer.common.models import Session as SessionModel
from primer.common.models import (
    SessionChangeShape,
    SessionCommit,
    SessionExecutionEvidence,
    SessionFacets,
    SessionRecoveryPath,
    SessionWorkflowProfile,
    ToolUsage,
)
from primer.server.services.workflow_patterns import (
    infer_workflow_steps,
    is_delegate_tool,
    workflow_fingerprint_id,
    workflow_fingerprint_label,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

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
_MIGRATION_TEXT_RE = re.compile(r"\b(?:migrat\w*|upgrade|moderniz\w*|deprecat\w*|port(?:ing|ed))\b")
_DEBUG_TEXT_RE = re.compile(
    r"\b(?:debug|failing|failure|regression|broken|traceback|incident|hotfix|repair)\b"
)


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


WorkflowProfileAction = Literal["created", "updated", "deleted", "unchanged", "skipped"]


def extract_session_workflow_profile(
    session: object,
    tool_usages: list[object],
    execution_evidence: list[object],
    *,
    change_shape: object | None = None,
    recovery_path: object | None = None,
    facets: object | None = None,
    source_metadata: object | None = None,
    agent_type: str | None = None,
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
    has_mutations = _has_mutations(change_shape, source_metadata=source_metadata)
    steps = infer_workflow_steps(
        tool_counts,
        has_commit,
        execution_types=execution_types,
        recovery_strategies=recovery_strategies,
        has_mutations=has_mutations,
    )
    steps = _augment_cursor_steps(
        steps,
        agent_type=agent_type,
        source_metadata=source_metadata,
    )

    archetype, archetype_source, archetype_reason = _infer_archetype(
        session,
        facets,
        change_shape,
        recovery_path,
        source_metadata=source_metadata,
        agent_type=agent_type,
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
        count for tool_name, count in tool_counts.items() if is_delegate_tool(tool_name)
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


def derive_session_workflow_profile(db: Session, session_id: str) -> WorkflowProfileRecord | None:
    db.flush()

    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session is None:
        return None

    tool_usages = db.query(ToolUsage).filter(ToolUsage.session_id == session_id).all()
    execution_evidence = (
        db.query(SessionExecutionEvidence)
        .filter(SessionExecutionEvidence.session_id == session_id)
        .order_by(SessionExecutionEvidence.ordinal)
        .all()
    )
    change_shape = (
        db.query(SessionChangeShape).filter(SessionChangeShape.session_id == session_id).first()
    )
    recovery_path = (
        db.query(SessionRecoveryPath).filter(SessionRecoveryPath.session_id == session_id).first()
    )
    facets = db.query(SessionFacets).filter(SessionFacets.session_id == session_id).first()
    has_commit = db.query(SessionCommit.id).filter(SessionCommit.session_id == session_id).first()
    return extract_session_workflow_profile(
        session,
        tool_usages,
        execution_evidence,
        change_shape=change_shape,
        recovery_path=recovery_path,
        facets=facets,
        source_metadata=session.source_metadata,
        agent_type=session.agent_type,
        has_commit=has_commit is not None,
    )


def upsert_session_workflow_profile(db: Session, session_id: str) -> WorkflowProfileAction:
    derived = derive_session_workflow_profile(db, session_id)
    existing = (
        db.query(SessionWorkflowProfile)
        .filter(SessionWorkflowProfile.session_id == session_id)
        .first()
    )
    action = _classify_workflow_profile_action(existing, derived)

    if action == "skipped" or action == "unchanged":
        return action

    if action == "deleted":
        db.delete(existing)
        db.flush()
        return action

    values = _workflow_profile_values(derived)
    record = existing or SessionWorkflowProfile(session_id=session_id)
    if existing is None:
        db.add(record)

    for field, value in values.items():
        setattr(record, field, value)
    db.flush()
    return action


def backfill_workflow_profiles(
    db: Session,
    *,
    limit: int = 500,
    recompute: bool = False,
    dry_run: bool = True,
) -> dict[str, int]:
    session_ids = _workflow_profile_candidate_session_ids(db, limit=limit, recompute=recompute)

    summary = {
        "sessions_scanned": len(session_ids),
        "profiles_created": 0,
        "profiles_updated": 0,
        "profiles_deleted": 0,
        "sessions_unchanged": 0,
        "sessions_skipped": 0,
    }

    for session_id in session_ids:
        if dry_run:
            derived = derive_session_workflow_profile(db, session_id)
            existing = (
                db.query(SessionWorkflowProfile)
                .filter(SessionWorkflowProfile.session_id == session_id)
                .first()
            )
            action = _classify_workflow_profile_action(existing, derived)
        else:
            action = upsert_session_workflow_profile(db, session_id)

        if action == "created":
            summary["profiles_created"] += 1
        elif action == "updated":
            summary["profiles_updated"] += 1
        elif action == "deleted":
            summary["profiles_deleted"] += 1
        elif action == "unchanged":
            summary["sessions_unchanged"] += 1
        else:
            summary["sessions_skipped"] += 1

    return summary


def _infer_archetype(
    session: object,
    facets: object | None,
    change_shape: object | None,
    recovery_path: object | None,
    *,
    source_metadata: object | None,
    agent_type: str | None,
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
    named_files = _named_files(change_shape) + _cursor_named_files(source_metadata)
    if _looks_like_docs(text, named_files):
        return "docs", "heuristic", "Documentation-heavy prompt or changed files suggest docs work."

    if _looks_like_migration(text, change_shape):
        return (
            "migration",
            "heuristic",
            "Prompt hints and broad file changes suggest a migration or upgrade effort.",
        )

    if _looks_like_debugging(text, execution_types, recovery_path, steps):
        return (
            "debugging",
            "heuristic",
            _debugging_reason(
                text,
                execution_types,
                recovery_path,
                steps,
                agent_type=agent_type,
                source_metadata=source_metadata,
            ),
        )

    if _looks_like_refactor(text, change_shape):
        return (
            "refactor",
            "heuristic",
            "Rewrite or rename signals point to a refactor-oriented session.",
        )

    if _looks_like_feature_delivery(change_shape, source_metadata, has_commit, steps):
        return (
            "feature_delivery",
            "heuristic",
            _cursor_feature_delivery_reason(agent_type, source_metadata),
        )

    if _looks_like_investigation(change_shape, source_metadata, has_commit, steps):
        return (
            "investigation",
            "heuristic",
            _cursor_investigation_reason(agent_type, source_metadata),
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


def _workflow_profile_candidate_session_ids(
    db: Session, *, limit: int, recompute: bool
) -> list[str]:
    query = db.query(SessionModel.id).order_by(SessionModel.created_at.asc(), SessionModel.id.asc())
    if not recompute:
        query = query.outerjoin(
            SessionWorkflowProfile, SessionWorkflowProfile.session_id == SessionModel.id
        ).filter(SessionWorkflowProfile.id.is_(None))
    return [row.id for row in query.limit(limit).all()]


def _workflow_profile_values(record: WorkflowProfileRecord) -> dict[str, object]:
    return {
        "fingerprint_id": record.fingerprint_id,
        "label": record.label,
        "steps": record.steps,
        "archetype": record.archetype,
        "archetype_source": record.archetype_source,
        "archetype_reason": record.archetype_reason,
        "top_tools": record.top_tools,
        "delegation_count": record.delegation_count,
        "verification_run_count": record.verification_run_count,
    }


def _classify_workflow_profile_action(
    existing: SessionWorkflowProfile | None, derived: WorkflowProfileRecord | None
) -> WorkflowProfileAction:
    if derived is None:
        return "deleted" if existing is not None else "skipped"
    if existing is None:
        return "created"

    values = _workflow_profile_values(derived)
    if any(getattr(existing, field) != value for field, value in values.items()):
        return "updated"
    return "unchanged"


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


def _has_mutations(change_shape: object | None, *, source_metadata: object | None = None) -> bool:
    if any(
        _int_attr(change_shape, field) > 0
        for field in (
            "files_touched_count",
            "diff_size",
            "edit_operations",
            "create_operations",
            "delete_operations",
            "rename_operations",
        )
    ):
        return True
    return bool(_cursor_change_metadata(source_metadata))


def _cursor_native_telemetry(source_metadata: object | None) -> dict | None:
    if not isinstance(source_metadata, dict):
        return None
    native = source_metadata.get("native_telemetry")
    return native if isinstance(native, dict) else None


def _cursor_change_metadata(source_metadata: object | None) -> dict | None:
    native = _cursor_native_telemetry(source_metadata)
    if native is None:
        return None
    change_signals = native.get("change_signals")
    return change_signals if isinstance(change_signals, dict) else None


def _cursor_context_metadata(source_metadata: object | None) -> dict | None:
    native = _cursor_native_telemetry(source_metadata)
    if native is None:
        return None
    context_usage = native.get("context_usage")
    return context_usage if isinstance(context_usage, dict) else None


def _cursor_named_files(source_metadata: object | None) -> list[str]:
    change_signals = _cursor_change_metadata(source_metadata)
    if change_signals is None:
        return []
    target_files = change_signals.get("target_files")
    if not isinstance(target_files, list):
        return []
    return [value for value in target_files if isinstance(value, str) and value]


def _augment_cursor_steps(
    steps: list[str],
    *,
    agent_type: str | None,
    source_metadata: object | None,
) -> list[str]:
    if agent_type != "cursor":
        return steps

    ordered_steps = list(steps)
    if _cursor_context_metadata(source_metadata) and "read" not in ordered_steps:
        insert_at = ordered_steps.index("search") + 1 if "search" in ordered_steps else 0
        ordered_steps.insert(insert_at, "read")

    return ordered_steps


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
    text: str,
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
    if _DEBUG_TEXT_RE.search(text) and ("edit" in steps or "execute" in steps):
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
    source_metadata: object | None,
    has_commit: bool,
    steps: list[str],
) -> bool:
    if has_commit or "ship" in steps:
        return True
    return _has_mutations(change_shape, source_metadata=source_metadata)


def _looks_like_investigation(
    change_shape: object | None,
    source_metadata: object | None,
    has_commit: bool,
    steps: list[str],
) -> bool:
    if has_commit or _has_mutations(change_shape, source_metadata=source_metadata):
        return False
    return bool(steps) and set(steps).issubset(
        {"search", "read", "execute", "delegate", "integrate"}
    )


def _bool_attr(value: object | None, field: str) -> bool:
    if value is None:
        return False
    candidate = value.get(field) if isinstance(value, dict) else getattr(value, field, None)
    return bool(candidate)


def _debugging_reason(
    text: str,
    execution_types: set[str],
    recovery_path: object | None,
    steps: list[str],
    *,
    agent_type: str | None,
    source_metadata: object | None,
) -> str:
    if _int_attr(recovery_path, "recovery_step_count") > 0 or _string_attr(
        recovery_path, "recovery_result"
    ) in {"recovered", "unresolved"}:
        return "Recovery behavior suggests a debugging loop."
    if "fix" in steps or ("test" in execution_types and "edit" in steps):
        return "Verification evidence suggests a debugging loop."
    if agent_type == "cursor" and _cursor_change_metadata(source_metadata):
        return (
            "Cursor-native change signals plus debugging-style prompt cues suggest a "
            "debugging loop."
        )
    if _DEBUG_TEXT_RE.search(text) and ("edit" in steps or "execute" in steps):
        return "Debugging-style prompt cues suggest a debugging loop."
    return "Heuristic debugging signals suggest a debugging loop."


def _cursor_feature_delivery_reason(agent_type: str | None, source_metadata: object | None) -> str:
    if agent_type == "cursor" and _cursor_change_metadata(source_metadata):
        return (
            "Cursor-native change signals indicate durable edits, which suggests feature delivery "
            "work."
        )
    return "Mutating changes and shipping signals suggest feature delivery work."


def _cursor_investigation_reason(agent_type: str | None, source_metadata: object | None) -> str:
    if agent_type == "cursor" and _cursor_context_metadata(source_metadata):
        return (
            "Cursor-native context selection without durable changes suggests an investigation "
            "workflow."
        )
    return "Read-heavy activity without durable changes suggests investigation work."
