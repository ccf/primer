from __future__ import annotations

from primer.common.schemas import (
    CoachingBrief,
    InSessionNudge,
    InSessionNudgesResponse,
    LiveSessionSignal,
    LiveSessionSignalsResponse,
)


def build_in_session_nudges(
    live_signals: LiveSessionSignalsResponse,
    coaching_brief: CoachingBrief | None = None,
    *,
    limit: int = 3,
) -> InSessionNudgesResponse:
    section_items = _section_items_by_title(coaching_brief)
    nudges: list[InSessionNudge] = []

    for signal in live_signals.signals:
        nudge = _nudge_for_signal(signal, live_signals, section_items)
        if nudge is None:
            continue
        nudges.append(nudge)

    if not nudges and live_signals.risk_level == "low":
        nudges.append(
            InSessionNudge(
                nudge_type="stay_the_course",
                severity="info",
                title="Stay on the current path",
                message=(
                    "No strong intervention signal is standing out right now. Keep the current "
                    "workflow tight and only widen scope if the next verification step fails."
                ),
                rationale="Live signals look healthy and there is no urgent corrective action.",
                suggested_actions=section_items.get("How to start this session", [])[:1],
            )
        )

    nudges.sort(key=_nudge_sort_key)
    return InSessionNudgesResponse(
        session_id=live_signals.session_id,
        project_name=live_signals.project_name,
        risk_level=live_signals.risk_level,
        nudges=nudges[:limit],
    )


def _section_items_by_title(coaching_brief: CoachingBrief | None) -> dict[str, list[str]]:
    if coaching_brief is None:
        return {}
    return {section.title: list(section.items) for section in coaching_brief.sections}


def _nudge_for_signal(
    signal: LiveSessionSignal,
    live_signals: LiveSessionSignalsResponse,
    section_items: dict[str, list[str]],
) -> InSessionNudge | None:
    if signal.signal_type == "verification_failure":
        return InSessionNudge(
            nudge_type="tighten_verification_loop",
            severity=signal.severity,
            title="Tighten the verification loop",
            message=(
                "Recent verification steps are failing. Narrow the loop to the smallest proving "
                "command before making broader edits."
            ),
            rationale=signal.detail,
            suggested_actions=_merge_actions(
                section_items.get("How to start this session", []),
                section_items.get("What to reach for", []),
            )[:2],
        )

    if signal.signal_type == "tool_error_cluster":
        return InSessionNudge(
            nudge_type="fallback_from_tooling",
            severity=signal.severity,
            title="Switch away from the failing tool path",
            message=(
                "Multiple tool errors are stacking up. Move to the project fallback path or a "
                "simpler local inspection step instead of retrying the same integration."
            ),
            rationale=signal.detail,
            suggested_actions=_merge_actions(
                section_items.get("What to watch for", []),
                section_items.get("How to start this session", []),
            )[:2],
        )

    if signal.signal_type == "recovery_loop":
        return InSessionNudge(
            nudge_type="break_recovery_loop",
            severity=signal.severity,
            title="Break the recovery loop",
            message=(
                "The session looks stuck in repeated recovery attempts. Pause, return to the best "
                "known playbook, and pick a single next proving action."
            ),
            rationale=signal.detail,
            suggested_actions=_merge_actions(
                section_items.get("How to start this session", []),
                section_items.get("What to reach for", []),
            )[:3],
        )

    if signal.signal_type == "negative_sentiment":
        return InSessionNudge(
            nudge_type="reframe_task",
            severity=signal.severity,
            title="Reframe before the next step",
            message=(
                "Recent user messages look frustrated. Reset to the smallest next step that can "
                "confirm or disprove the current hypothesis."
            ),
            rationale=signal.detail,
            suggested_actions=_merge_actions(
                section_items.get("How to start this session", []),
                section_items.get("What to watch for", []),
            )[:2],
        )

    if signal.signal_type == "positive_momentum" and live_signals.risk_level == "low":
        return InSessionNudge(
            nudge_type="maintain_momentum",
            severity="info",
            title="Keep the loop tight",
            message=(
                "The session looks healthy. Stay with the current workflow and avoid adding extra "
                "scope until the next verification step."
            ),
            rationale=signal.detail,
            suggested_actions=section_items.get("How to start this session", [])[:1],
        )

    return None


def _merge_actions(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
    return merged


def _nudge_sort_key(nudge: InSessionNudge) -> tuple[int, int, str]:
    severity_score = {"critical": 2, "warning": 1, "info": 0}
    return (
        -severity_score.get(nudge.severity, 0),
        -len(nudge.suggested_actions),
        nudge.title,
    )
