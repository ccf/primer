from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from primer.common.schemas import LiveSessionSignal, LiveSessionSignalsResponse
from primer.hook.extractor_registry import get_extractor_for
from primer.mcp.reader import LocalSession, list_local_sessions
from primer.server.services.execution_evidence_service import (
    _EXECUTION_TOOL_NAMES,
    _classify_status,
    extract_execution_evidence,
)
from primer.server.services.recovery_path_service import extract_recovery_path
from primer.server.services.session_signal_parsing import message_payload, normalize_tool_name

if TYPE_CHECKING:
    from primer.hook.extractor import SessionMetadata

_NEGATIVE_SATISFACTION_PHRASES = (
    "still broken",
    "not working",
    "doesn't work",
    "does not work",
    "not right",
    "try again",
    "stuck",
    "blocked",
    "frustrated",
    "annoying",
    "i give up",
    "this is broken",
)
_POSITIVE_SATISFACTION_PHRASES = (
    "thanks",
    "thank you",
    "that fixed it",
    "works now",
    "looks good",
    "great",
    "nice",
    "perfect",
    "resolved",
)
_TOOL_ERROR_KEYWORDS = ("error", "failed", "failure", "traceback", "exception", "timeout")


def get_live_session_signals(
    *,
    session_id: str | None = None,
    transcript_path: str | None = None,
) -> LiveSessionSignalsResponse:
    session = _resolve_local_session(session_id=session_id, transcript_path=transcript_path)
    extractor = get_extractor_for(session.agent_type)
    if extractor is None:
        raise ValueError(f"No extractor available for agent type '{session.agent_type}'")

    metadata = extractor.extract(session.transcript_path)
    return _build_live_session_signal_summary(session, metadata)


def _resolve_local_session(
    *,
    session_id: str | None,
    transcript_path: str | None,
) -> LocalSession:
    sessions = list_local_sessions()
    if not sessions:
        raise ValueError("No local sessions found")

    if session_id:
        for session in sessions:
            if session.session_id == session_id:
                return session
        raise ValueError(f"No local session found for session_id '{session_id}'")

    if transcript_path:
        for session in sessions:
            if session.transcript_path == transcript_path:
                return session
        raise ValueError(f"No local session found for transcript_path '{transcript_path}'")

    return max(sessions, key=_session_sort_key)


def _session_sort_key(session: LocalSession) -> tuple[float, str]:
    return (_session_mtime(session), session.session_id)


def _session_mtime(session: LocalSession) -> float:
    path = _session_source_path(session.transcript_path)
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _session_source_path(transcript_path: str) -> Path:
    path = Path(transcript_path)
    if path.exists():
        return path
    if "::" in transcript_path:
        raw_path = transcript_path.rsplit("::", 1)[0]
        return Path(raw_path)
    return path


def _build_live_session_signal_summary(
    session: LocalSession,
    metadata: SessionMetadata,
) -> LiveSessionSignalsResponse:
    messages = metadata.messages or []
    execution_evidence = extract_execution_evidence(messages)
    recovery_path = extract_recovery_path(messages, execution_evidence)

    failed_execution = [record for record in execution_evidence if record.status == "failed"]
    failed_verifications = [
        record
        for record in failed_execution
        if record.evidence_type in {"test", "lint", "build", "verification"}
    ]
    tool_error_count = _count_tool_errors(messages)
    satisfaction_signal = _infer_satisfaction_signal(messages)
    recovery_loop = bool(
        recovery_path
        and recovery_path.recovery_result != "recovered"
        and recovery_path.recovery_step_count >= 3
    )

    signals: list[LiveSessionSignal] = []

    if failed_verifications:
        severity = "critical" if len(failed_verifications) >= 2 else "warning"
        signals.append(
            LiveSessionSignal(
                signal_type="verification_failure",
                severity=severity,
                title="Verification is failing",
                detail=(
                    f"Recent test/build/lint commands have failed {len(failed_verifications)} "
                    f"time{'s' if len(failed_verifications) != 1 else ''}."
                ),
                evidence={
                    "failure_count": len(failed_verifications),
                    "last_failure_type": failed_verifications[-1].evidence_type,
                },
            )
        )

    if tool_error_count >= 2:
        signals.append(
            LiveSessionSignal(
                signal_type="tool_error_cluster",
                severity="warning",
                title="Tool errors are stacking up",
                detail=(
                    f"{tool_error_count} recent tool results look error-like. "
                    "This session may be fighting the toolchain, not the task."
                ),
                evidence={"tool_error_count": tool_error_count},
            )
        )

    if recovery_loop:
        assert recovery_path is not None
        signals.append(
            LiveSessionSignal(
                signal_type="recovery_loop",
                severity="critical",
                title="Recovery loop detected",
                detail=(
                    f"The session has {recovery_path.recovery_step_count} recovery steps "
                    "without a clear resolution yet."
                ),
                evidence={
                    "recovery_step_count": recovery_path.recovery_step_count,
                    "recovery_result": recovery_path.recovery_result,
                },
            )
        )

    if satisfaction_signal == "negative":
        signals.append(
            LiveSessionSignal(
                signal_type="negative_sentiment",
                severity="warning",
                title="User sentiment looks frustrated",
                detail=("Recent user messages suggest the current approach still is not landing."),
                evidence={"satisfaction_signal": satisfaction_signal},
            )
        )
    elif satisfaction_signal == "positive" and not signals:
        signals.append(
            LiveSessionSignal(
                signal_type="positive_momentum",
                severity="info",
                title="Session looks healthy",
                detail="Recent interaction signals look positive and unblocked.",
                evidence={"satisfaction_signal": satisfaction_signal},
            )
        )

    if not signals:
        signals.append(
            LiveSessionSignal(
                signal_type="steady_state",
                severity="info",
                title="No acute live risks detected",
                detail="No strong friction or abandonment signals are standing out right now.",
                evidence={},
            )
        )

    risk_score = 0
    if len(failed_verifications) >= 2:
        risk_score += 2
    elif failed_verifications:
        risk_score += 1
    if tool_error_count >= 2:
        risk_score += 1
    if recovery_loop:
        risk_score += 1
    if satisfaction_signal == "negative":
        risk_score += 1
    elif satisfaction_signal == "positive":
        risk_score -= 1

    if risk_score >= 3:
        risk_level = "high"
    elif risk_score >= 1:
        risk_level = "medium"
    else:
        risk_level = "low"

    return LiveSessionSignalsResponse(
        session_id=metadata.session_id or session.session_id,
        agent_type=metadata.agent_type or session.agent_type,
        project_name=metadata.project_name or session.project_path,
        started_at=metadata.started_at,
        total_messages=len(messages),
        risk_level=risk_level,
        satisfaction_signal=satisfaction_signal,
        signals=signals,
    )


def _count_tool_errors(messages: list[object]) -> int:
    count = 0
    for message in messages:
        payload = message_payload(message)
        if payload is None:
            continue
        tool_results = payload.get("tool_results")
        if not isinstance(tool_results, list):
            continue
        for tool_result in tool_results:
            if not isinstance(tool_result, dict):
                continue
            tool_name = normalize_tool_name(tool_result.get("name"))
            if tool_name in _EXECUTION_TOOL_NAMES:
                continue
            output_preview = tool_result.get("output_preview")
            if not isinstance(output_preview, str):
                continue
            status = _classify_status(output_preview)
            if status == "passed":
                continue
            if status == "failed":
                count += 1
                continue
            normalized = output_preview.lower()
            if any(keyword in normalized for keyword in _TOOL_ERROR_KEYWORDS):
                count += 1
                continue
            if tool_name and "error" in tool_name:
                count += 1
    return count


def _infer_satisfaction_signal(messages: list[object]) -> str:
    negative = 0
    positive = 0

    recent_user_text = list(_recent_user_messages(messages, limit=6))
    for text in recent_user_text:
        normalized = text.lower()
        if any(phrase in normalized for phrase in _NEGATIVE_SATISFACTION_PHRASES):
            negative += 1
        if any(phrase in normalized for phrase in _POSITIVE_SATISFACTION_PHRASES):
            positive += 1

    if negative > positive and negative > 0:
        return "negative"
    if positive > negative and positive > 0:
        return "positive"
    if positive or negative:
        return "neutral"
    return "unknown"


def _recent_user_messages(messages: list[object], *, limit: int) -> list[str]:
    user_text: list[str] = []
    for message in reversed(messages):
        payload = message_payload(message)
        if payload is None:
            continue
        role = payload.get("role")
        if role not in {"human", "user"}:
            continue
        content = payload.get("content_text")
        if isinstance(content, str) and content.strip():
            user_text.append(content.strip())
        if len(user_text) >= limit:
            break
    user_text.reverse()
    return user_text
