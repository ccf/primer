"""Bottleneck, root-cause, and time-lost analytics."""

from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import date as date_type
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.common.models import (
    Engineer,
    SessionFacets,
    SessionMessage,
    SessionRecoveryPath,
    ToolUsage,
)
from primer.common.models import (
    Session as SessionModel,
)
from primer.common.schemas import (
    BottleneckAnalytics,
    EngineerFrictionTimeLost,
    FrictionImpact,
    FrictionTrend,
    ProjectFriction,
    RecoveryOverview,
    RecoveryPattern,
    RootCauseCluster,
)
from primer.common.source_capabilities import get_agent_types_with_capability
from primer.common.tool_classification import classify_tool
from primer.server.services.analytics_cache_service import get_cached_json, set_cached_json

_ROOT_CAUSE_FRICTION_MAP: dict[str, str] = {
    "permission_denied": "permission_boundary",
    "user_rejected_action": "permission_boundary",
    "tool_error": "tool_or_integration_failure",
    "tool_failed": "tool_or_integration_failure",
    "external_tool_issue": "tool_or_integration_failure",
    "timeout": "tool_or_integration_failure",
    "exec_error": "verification_failure",
    "compile_error": "verification_failure",
    "buggy_code": "verification_failure",
    "context_switching": "context_fragmentation",
    "context_limit": "context_fragmentation",
    "slow_or_verbose": "context_fragmentation",
    "edit_conflict": "repo_state_conflict",
    "wrong_file_or_location": "repo_state_conflict",
    "assistant_got_blocked": "environment_readiness",
    "wrong_approach": "task_misalignment",
    "misunderstood_request": "task_misalignment",
    "excessive_changes": "task_misalignment",
}

_ROOT_CAUSE_LABELS: dict[str, str] = {
    "permission_boundary": "Permission boundaries",
    "tool_or_integration_failure": "Tool and integration failures",
    "verification_failure": "Verification and command failures",
    "context_fragmentation": "Context fragmentation",
    "repo_state_conflict": "Repository state conflicts",
    "environment_readiness": "Environment and dependency gaps",
    "task_misalignment": "Task and scope misalignment",
    "unknown": "Repeated friction pattern",
}

_ROOT_CAUSE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "permission_boundary": (
        "permission",
        "access denied",
        "forbidden",
        "unauthorized",
        "sandbox",
        "approval",
        "read-only",
    ),
    "tool_or_integration_failure": (
        "mcp",
        "network",
        "connection",
        "timeout",
        "tool failed",
        "tooling failed",
        "service unavailable",
        "webhook",
        "api",
        "rate limit",
    ),
    "verification_failure": (
        "test failed",
        "failing test",
        "build failed",
        "compile",
        "lint",
        "typecheck",
        "assertion",
        "command failed",
    ),
    "context_fragmentation": (
        "context",
        "multiple files",
        "too many files",
        "lost track",
        "switch",
        "token limit",
        "verbose",
    ),
    "repo_state_conflict": (
        "merge conflict",
        "rebase",
        "branch",
        "worktree",
        "conflict",
        "dirty tree",
        "unstaged",
    ),
    "environment_readiness": (
        "module not found",
        "dependency",
        "import",
        "package",
        "missing file",
        "missing directory",
        "environment",
        "env var",
        "config",
        "path",
    ),
    "task_misalignment": (
        "wrong file",
        "wrong approach",
        "misunderstood",
        "rejected",
        "too much",
        "over-engineered",
    ),
}

_FRICTION_TIME_LOST_MINUTES: dict[str, float] = {
    "permission_denied": 4.0,
    "user_rejected_action": 3.0,
    "timeout": 6.0,
    "tool_error": 5.0,
    "external_tool_issue": 6.0,
    "exec_error": 8.0,
    "compile_error": 8.0,
    "buggy_code": 8.0,
    "context_switching": 5.0,
    "context_limit": 7.0,
    "slow_or_verbose": 3.0,
    "edit_conflict": 6.0,
    "wrong_file_or_location": 5.0,
    "assistant_got_blocked": 4.0,
    "wrong_approach": 10.0,
    "misunderstood_request": 8.0,
    "excessive_changes": 9.0,
}
_DEFAULT_FRICTION_TIME_LOST_MINUTES = 5.0
_RECOVERY_STEP_TIME_LOST_MINUTES = 2.5
_ABANDONED_SESSION_TIME_LOST_FACTOR = 0.35
_ABANDONED_SESSION_TIME_LOST_CAP_MINUTES = 20.0
_ABANDONED_SESSION_TIME_LOST_FALLBACK_MINUTES = 12.0
_UNRESOLVED_SESSION_TIME_LOST_FACTOR = 0.2
_UNRESOLVED_SESSION_TIME_LOST_CAP_MINUTES = 10.0
_UNRESOLVED_SESSION_TIME_LOST_FALLBACK_MINUTES = 6.0

_STAGE_TOOL_WEIGHTS: dict[str, tuple[str, ...]] = {
    "search": ("Glob", "Grep", "WebSearch", "WebFetch"),
    "read": ("Read",),
    "edit": ("Edit", "Write", "NotebookEdit"),
    "execute": ("Bash",),
    "delegate": ("Task", "Agent", "EnterPlanMode", "ExitPlanMode", "AskUserQuestion"),
}

CacheGetter = Callable[[str, dict[str, object]], dict[str, Any] | None]
CacheSetter = Callable[[str, dict[str, object], dict[str, Any]], None]


def get_bottleneck_analytics(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    project_name: str | None = None,
    *,
    cache_getter: CacheGetter | None = None,
    cache_setter: CacheSetter | None = None,
) -> BottleneckAnalytics:
    """Analyse friction patterns across sessions for bottleneck detection."""
    cache_getter = cache_getter or get_cached_json
    cache_setter = cache_setter or set_cached_json
    cache_params = {
        "team_id": team_id,
        "engineer_id": engineer_id,
        "start_date": start_date,
        "end_date": end_date,
        "project_name": project_name,
    }
    cached = cache_getter("bottleneck_analytics", cache_params)
    if cached is not None:
        return BottleneckAnalytics.model_validate(cached)

    rows = _query_bottleneck_rows(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
        project_name=project_name,
    )

    total_sessions = len(rows)
    if total_sessions == 0:
        result = BottleneckAnalytics(
            friction_impacts=[],
            project_friction=[],
            friction_trends=[],
            root_cause_clusters=[],
            recovery_overview=RecoveryOverview(
                sessions_with_recovery_paths=0,
                recovered_sessions=0,
                abandoned_sessions=0,
                unresolved_sessions=0,
                recovery_rate=0.0,
                avg_recovery_steps=0.0,
            ),
            recovery_patterns=[],
            total_sessions_analyzed=0,
            sessions_with_any_friction=0,
            overall_friction_rate=0.0,
        )
        cache_setter("bottleneck_analytics", cache_params, result.model_dump(mode="json"))
        return result

    session_ids = [session.id for session, _ in rows]
    recovery_rows = (
        db.query(SessionRecoveryPath).filter(SessionRecoveryPath.session_id.in_(session_ids)).all()
    )
    recovery_by_session = {row.session_id: row for row in recovery_rows}
    engineer_names = _engineer_names_for_rows(db, rows)
    tool_counts_by_session = _tool_counts_by_session(db, session_ids)
    transcript_text_by_session = _transcript_text_by_session(db, session_ids)

    friction_state = _build_friction_state(rows, recovery_by_session)
    friction_impacts = _build_friction_impacts(friction_state)
    root_cause_clusters = _build_root_cause_clusters(
        rows=rows,
        tool_counts_by_session=tool_counts_by_session,
        transcript_text_by_session=transcript_text_by_session,
        friction_impacts=friction_impacts,
    )
    recovery_overview = _build_recovery_overview(recovery_rows)
    recovery_patterns = _build_recovery_patterns(recovery_rows)
    project_friction_list = _build_project_friction(friction_state)
    engineer_time_lost = _build_engineer_time_lost(friction_state, engineer_names)
    friction_trends = _build_friction_trends(friction_state)

    sessions_with_count = len(friction_state["sessions_with_friction"])
    result = BottleneckAnalytics(
        friction_impacts=friction_impacts,
        project_friction=project_friction_list,
        engineer_time_lost=engineer_time_lost,
        friction_trends=friction_trends,
        root_cause_clusters=root_cause_clusters,
        recovery_overview=recovery_overview,
        recovery_patterns=recovery_patterns,
        total_sessions_analyzed=total_sessions,
        sessions_with_any_friction=sessions_with_count,
        overall_friction_rate=round(sessions_with_count / total_sessions, 3)
        if total_sessions > 0
        else 0.0,
        total_estimated_minutes_lost=round(
            sum(friction_state["project_time_lost_minutes"].values()),
            1,
        ),
    )
    cache_setter("bottleneck_analytics", cache_params, result.model_dump(mode="json"))
    return result


def _query_bottleneck_rows(
    db: Session,
    *,
    team_id: str | None,
    engineer_id: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
    project_name: str | None,
):
    q = db.query(SessionModel, SessionFacets).join(
        SessionFacets, SessionFacets.session_id == SessionModel.id
    )
    q = _filter_sessions_by_capability(q, "supports_facets")
    if engineer_id:
        q = q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        q = q.join(Engineer, Engineer.id == SessionModel.engineer_id).filter(
            Engineer.team_id == team_id
        )
    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)
    if project_name:
        q = q.filter(SessionModel.project_name == project_name)
    return q.all()


def _filter_sessions_by_capability(query, capability_name: str):
    supported_agent_types = get_agent_types_with_capability(capability_name)
    if not supported_agent_types:
        return query.filter(SessionModel.id.is_(None))
    return query.filter(SessionModel.agent_type.in_(supported_agent_types))


def _engineer_names_for_rows(db: Session, rows) -> dict[str, str]:
    return {
        engineer_id: name
        for engineer_id, name in (
            db.query(Engineer.id, Engineer.name)
            .filter(Engineer.id.in_({session.engineer_id for session, _ in rows}))
            .all()
        )
    }


def _tool_counts_by_session(db: Session, session_ids: list[str]) -> dict[str, Counter[str]]:
    tool_counts_by_session: dict[str, Counter[str]] = defaultdict(Counter)
    for session_id, tool_name, call_count in (
        db.query(ToolUsage.session_id, ToolUsage.tool_name, ToolUsage.call_count)
        .filter(ToolUsage.session_id.in_(session_ids))
        .all()
    ):
        tool_counts_by_session[session_id][tool_name] += call_count
    return tool_counts_by_session


def _transcript_text_by_session(db: Session, session_ids: list[str]) -> dict[str, list[str]]:
    transcript_rows = (
        db.query(SessionMessage.session_id, SessionMessage.content_text)
        .filter(
            SessionMessage.session_id.in_(session_ids),
            SessionMessage.ordinal <= 4,
            SessionMessage.content_text.isnot(None),
        )
        .order_by(SessionMessage.session_id.asc(), SessionMessage.ordinal.asc())
        .all()
    )
    transcript_text_by_session: dict[str, list[str]] = defaultdict(list)
    for session_id, content_text in transcript_rows:
        if content_text and len(transcript_text_by_session[session_id]) < 4:
            transcript_text_by_session[session_id].append(content_text)
    return transcript_text_by_session


def _build_friction_state(rows, recovery_by_session: dict[str, SessionRecoveryPath]) -> dict:
    state = {
        "type_occurrences": Counter(),
        "type_sessions": {},
        "type_details": {},
        "type_outcomes_with": {},
        "sessions_with_friction": set(),
        "session_outcomes": {},
        "project_sessions": {},
        "project_friction_sessions": {},
        "project_friction_counts": {},
        "project_time_lost_minutes": defaultdict(float),
        "engineer_sessions": defaultdict(set),
        "engineer_friction_sessions": defaultdict(set),
        "engineer_friction_counts": defaultdict(Counter),
        "engineer_time_lost_minutes": defaultdict(float),
        "friction_time_lost_minutes": defaultdict(float),
        "daily_friction": {},
        "daily_friction_sessions": {},
        "daily_total_sessions": {},
    }

    for session, facets in rows:
        _add_session_to_friction_state(state, session, facets, recovery_by_session)
    return state


def _add_session_to_friction_state(
    state: dict,
    session: SessionModel,
    facets: SessionFacets,
    recovery_by_session: dict[str, SessionRecoveryPath],
) -> None:
    sid = session.id
    outcome = canonical_outcome(facets.outcome) if facets else None
    date_key = session.started_at.strftime("%Y-%m-%d") if session.started_at else None
    project = session.project_name or "unknown"

    state["project_sessions"][project] = state["project_sessions"].get(project, 0) + 1
    state["engineer_sessions"][session.engineer_id].add(sid)
    if date_key:
        state["daily_total_sessions"].setdefault(date_key, set()).add(sid)

    friction_counts = facets.friction_counts if facets else None
    if friction_counts:
        _add_friction_counts_to_state(
            state=state,
            session=session,
            facets=facets,
            friction_counts=friction_counts,
            outcome=outcome,
            date_key=date_key,
            project=project,
            recovery_path=recovery_by_session.get(sid),
        )
    if outcome:
        state["session_outcomes"][sid] = outcome


def _add_friction_counts_to_state(
    *,
    state: dict,
    session: SessionModel,
    facets: SessionFacets,
    friction_counts: dict[str, int],
    outcome: str | None,
    date_key: str | None,
    project: str,
    recovery_path: SessionRecoveryPath | None,
) -> None:
    has_friction = False
    detail_assigned = False
    distributed_minutes_by_type, total_minutes_lost = _estimate_session_time_lost_minutes(
        session,
        friction_counts,
        outcome=outcome,
        recovery_path=recovery_path,
    )

    for friction_type, count in friction_counts.items():
        if count <= 0:
            continue
        has_friction = True
        state["type_occurrences"][friction_type] += count
        state["type_sessions"].setdefault(friction_type, set()).add(session.id)

        if outcome:
            state["type_outcomes_with"].setdefault(friction_type, []).append(outcome)

        if facets.friction_detail and not detail_assigned:
            state["type_details"].setdefault(friction_type, [])
            if len(state["type_details"][friction_type]) < 10:
                state["type_details"][friction_type].append(facets.friction_detail)
                detail_assigned = True

        state["project_friction_counts"].setdefault(project, Counter())[friction_type] += count
        if date_key:
            state["daily_friction"][date_key] = state["daily_friction"].get(date_key, 0) + count

        state["friction_time_lost_minutes"][friction_type] += distributed_minutes_by_type.get(
            friction_type,
            0.0,
        )

    if not has_friction:
        return

    state["sessions_with_friction"].add(session.id)
    state["project_friction_sessions"].setdefault(project, set()).add(session.id)
    state["project_time_lost_minutes"][project] += total_minutes_lost
    state["engineer_friction_sessions"][session.engineer_id].add(session.id)
    state["engineer_time_lost_minutes"][session.engineer_id] += total_minutes_lost
    state["engineer_friction_counts"][session.engineer_id].update(
        {
            friction_type: count
            for friction_type, count in friction_counts.items()
            if count and count > 0
        }
    )
    if date_key:
        state["daily_friction_sessions"].setdefault(date_key, set()).add(session.id)


def _build_friction_impacts(state: dict) -> list[FrictionImpact]:
    def _success_rate(outcomes: list[str]) -> float | None:
        if not outcomes:
            return None
        return sum(1 for outcome in outcomes if is_success_outcome(outcome)) / len(outcomes)

    all_session_ids = set(state["session_outcomes"].keys())
    friction_impacts: list[FrictionImpact] = []
    for friction_type, occurrence_count in state["type_occurrences"].most_common():
        sr_with = _success_rate(state["type_outcomes_with"].get(friction_type, []))
        sessions_without_friction_type = all_session_ids - state["type_sessions"].get(
            friction_type,
            set(),
        )
        outcomes_without_friction_type = [
            state["session_outcomes"][session_id] for session_id in sessions_without_friction_type
        ]
        sr_without = _success_rate(outcomes_without_friction_type)
        impact = None
        if sr_with is not None and sr_without is not None:
            impact = round(sr_without - sr_with, 3)

        affected_sessions = len(state["type_sessions"].get(friction_type, set()))
        estimated_minutes_lost = state["friction_time_lost_minutes"].get(friction_type, 0.0)
        friction_impacts.append(
            FrictionImpact(
                friction_type=friction_type,
                occurrence_count=occurrence_count,
                sessions_affected=affected_sessions,
                success_rate_with=round(sr_with, 3) if sr_with is not None else None,
                success_rate_without=round(sr_without, 3) if sr_without is not None else None,
                impact_score=impact,
                estimated_minutes_lost=round(estimated_minutes_lost, 1),
                avg_minutes_lost_per_affected_session=(
                    round(estimated_minutes_lost / affected_sessions, 1)
                    if affected_sessions
                    else None
                ),
                avg_minutes_lost_per_occurrence=(
                    round(estimated_minutes_lost / occurrence_count, 1)
                    if occurrence_count > 0
                    else None
                ),
                sample_details=state["type_details"].get(friction_type, []),
            )
        )
    return friction_impacts


def _build_root_cause_clusters(
    *,
    rows,
    tool_counts_by_session: dict[str, Counter[str]],
    transcript_text_by_session: dict[str, list[str]],
    friction_impacts: list[FrictionImpact],
) -> list[RootCauseCluster]:
    impact_by_type = {
        item.friction_type: item.impact_score
        for item in friction_impacts
        if item.impact_score is not None
    }
    cluster_buckets: dict[str, dict] = {}
    for session, facets in rows:
        friction_counts = facets.friction_counts if facets else None
        if not friction_counts:
            continue

        positive_counts = {
            friction_type: count
            for friction_type, count in friction_counts.items()
            if count and count > 0
        }
        if not positive_counts:
            continue

        tool_counts = tool_counts_by_session.get(session.id, Counter())
        workflow_stage = _infer_workflow_stage(tool_counts)
        combined_text = " ".join(
            part
            for part in [
                facets.friction_detail or "",
                *transcript_text_by_session.get(session.id, []),
            ]
            if part
        )
        cause_category = _derive_root_cause_category(positive_counts, combined_text)
        cluster_id = f"{cause_category}::{workflow_stage}"
        bucket = cluster_buckets.setdefault(
            cluster_id,
            {
                "cause_category": cause_category,
                "workflow_stage": workflow_stage,
                "session_ids": set(),
                "occurrence_count": 0,
                "success_count": 0,
                "outcome_count": 0,
                "friction_type_counts": Counter(),
                "tool_counts": Counter(),
                "cue_counts": Counter(),
                "sample_details": [],
            },
        )

        if session.id not in bucket["session_ids"]:
            bucket["session_ids"].add(session.id)
            if (outcome := canonical_outcome(facets.outcome)) is not None:
                bucket["outcome_count"] += 1
                if is_success_outcome(outcome):
                    bucket["success_count"] += 1

        bucket["occurrence_count"] += sum(positive_counts.values())
        bucket["friction_type_counts"].update(positive_counts)
        bucket["tool_counts"].update(tool_counts)
        bucket["cue_counts"].update(_extract_transcript_cues(combined_text))
        if facets.friction_detail and facets.friction_detail not in bucket["sample_details"]:
            bucket["sample_details"].append(facets.friction_detail)

    return [
        RootCauseCluster(
            cluster_id=cluster_id,
            title=_root_cause_title(bucket["cause_category"], bucket["workflow_stage"]),
            cause_category=bucket["cause_category"],
            workflow_stage=bucket["workflow_stage"],
            session_count=len(bucket["session_ids"]),
            occurrence_count=bucket["occurrence_count"],
            success_rate=(
                round(bucket["success_count"] / bucket["outcome_count"], 3)
                if bucket["outcome_count"] > 0
                else None
            ),
            avg_impact_score=(
                round(
                    sum(
                        (impact_by_type.get(friction_type) or 0.0) * count
                        for friction_type, count in bucket["friction_type_counts"].items()
                    )
                    / sum(bucket["friction_type_counts"].values()),
                    3,
                )
                if bucket["friction_type_counts"]
                else None
            ),
            top_friction_types=[
                friction_type for friction_type, _ in bucket["friction_type_counts"].most_common(3)
            ],
            common_tools=[tool_name for tool_name, _ in bucket["tool_counts"].most_common(3)],
            transcript_cues=[cue for cue, _ in bucket["cue_counts"].most_common(3)],
            sample_details=bucket["sample_details"][:3],
        )
        for cluster_id, bucket in sorted(
            cluster_buckets.items(),
            key=lambda item: (
                len(item[1]["session_ids"]),
                item[1]["occurrence_count"],
            ),
            reverse=True,
        )[:8]
    ]


def _build_recovery_overview(recovery_rows: list[SessionRecoveryPath]) -> RecoveryOverview:
    recovered_sessions = sum(1 for row in recovery_rows if row.recovery_result == "recovered")
    abandoned_sessions = sum(1 for row in recovery_rows if row.recovery_result == "abandoned")
    unresolved_sessions = max(len(recovery_rows) - recovered_sessions - abandoned_sessions, 0)
    avg_recovery_steps = (
        round(
            sum(row.recovery_step_count for row in recovery_rows) / len(recovery_rows),
            1,
        )
        if recovery_rows
        else 0.0
    )
    return RecoveryOverview(
        sessions_with_recovery_paths=len(recovery_rows),
        recovered_sessions=recovered_sessions,
        abandoned_sessions=abandoned_sessions,
        unresolved_sessions=unresolved_sessions,
        recovery_rate=round(recovered_sessions / len(recovery_rows), 3) if recovery_rows else 0.0,
        avg_recovery_steps=avg_recovery_steps,
    )


def _build_recovery_patterns(recovery_rows: list[SessionRecoveryPath]) -> list[RecoveryPattern]:
    recovery_buckets: dict[str, dict] = {}
    for row in recovery_rows:
        for strategy in row.recovery_strategies or []:
            bucket = recovery_buckets.setdefault(
                strategy,
                {
                    "session_count": 0,
                    "recovered_sessions": 0,
                    "abandoned_sessions": 0,
                    "unresolved_sessions": 0,
                    "step_total": 0,
                    "command_counts": Counter(),
                },
            )
            bucket["session_count"] += 1
            bucket["step_total"] += row.recovery_step_count
            if row.recovery_result == "recovered":
                bucket["recovered_sessions"] += 1
            elif row.recovery_result == "abandoned":
                bucket["abandoned_sessions"] += 1
            else:
                bucket["unresolved_sessions"] += 1
            bucket["command_counts"].update(row.sample_recovery_commands or [])

    return [
        RecoveryPattern(
            strategy=strategy,
            session_count=bucket["session_count"],
            recovered_sessions=bucket["recovered_sessions"],
            abandoned_sessions=bucket["abandoned_sessions"],
            unresolved_sessions=bucket["unresolved_sessions"],
            recovery_rate=(
                round(bucket["recovered_sessions"] / bucket["session_count"], 3)
                if bucket["session_count"] > 0
                else 0.0
            ),
            avg_recovery_steps=(
                round(bucket["step_total"] / bucket["session_count"], 1)
                if bucket["session_count"] > 0
                else 0.0
            ),
            sample_commands=[command for command, _ in bucket["command_counts"].most_common(3)],
        )
        for strategy, bucket in sorted(
            recovery_buckets.items(),
            key=lambda item: (
                item[1]["recovered_sessions"],
                item[1]["session_count"],
            ),
            reverse=True,
        )[:5]
    ]


def _build_project_friction(state: dict) -> list[ProjectFriction]:
    project_friction_list: list[ProjectFriction] = []
    for project_name, total in state["project_sessions"].items():
        friction_sids = state["project_friction_sessions"].get(project_name, set())
        friction_count = len(friction_sids)
        project_counter = state["project_friction_counts"].get(project_name, Counter())
        total_friction_count = sum(project_counter.values())

        project_friction_list.append(
            ProjectFriction(
                project_name=project_name,
                total_sessions=total,
                sessions_with_friction=friction_count,
                friction_rate=round(friction_count / total, 3) if total > 0 else 0.0,
                top_friction_types=[
                    friction_type for friction_type, _ in project_counter.most_common(3)
                ],
                total_friction_count=total_friction_count,
                estimated_minutes_lost=round(
                    state["project_time_lost_minutes"].get(project_name, 0.0),
                    1,
                ),
                avg_minutes_lost_per_friction_session=(
                    round(
                        state["project_time_lost_minutes"].get(project_name, 0.0) / friction_count,
                        1,
                    )
                    if friction_count > 0
                    else None
                ),
            )
        )
    project_friction_list.sort(key=lambda project: project.total_friction_count, reverse=True)
    return project_friction_list


def _build_engineer_time_lost(
    state: dict,
    engineer_names: dict[str, str],
) -> list[EngineerFrictionTimeLost]:
    return [
        EngineerFrictionTimeLost(
            engineer_id=engineer_id,
            engineer_name=engineer_names.get(engineer_id, "Unknown"),
            total_sessions=len(state["engineer_sessions"].get(engineer_id, set())),
            sessions_with_friction=len(state["engineer_friction_sessions"].get(engineer_id, set())),
            total_friction_count=sum(
                state["engineer_friction_counts"].get(engineer_id, Counter()).values()
            ),
            estimated_minutes_lost=round(
                state["engineer_time_lost_minutes"].get(engineer_id, 0.0),
                1,
            ),
            avg_minutes_lost_per_friction_session=(
                round(
                    state["engineer_time_lost_minutes"].get(engineer_id, 0.0)
                    / len(state["engineer_friction_sessions"].get(engineer_id, set())),
                    1,
                )
                if state["engineer_friction_sessions"].get(engineer_id)
                else None
            ),
            top_friction_types=[
                friction_type
                for friction_type, _count in state["engineer_friction_counts"]
                .get(engineer_id, Counter())
                .most_common(3)
            ],
        )
        for engineer_id in sorted(
            state["engineer_friction_sessions"],
            key=lambda value: (
                state["engineer_time_lost_minutes"].get(value, 0.0),
                len(state["engineer_friction_sessions"].get(value, set())),
            ),
            reverse=True,
        )
    ]


def _build_friction_trends(state: dict) -> list[FrictionTrend]:
    friction_trends: list[FrictionTrend] = []
    for day in sorted(set(state["daily_total_sessions"].keys())):
        parts = day.split("-")
        friction_trends.append(
            FrictionTrend(
                date=date_type(int(parts[0]), int(parts[1]), int(parts[2])),
                total_friction_count=state["daily_friction"].get(day, 0),
                sessions_with_friction=len(state["daily_friction_sessions"].get(day, set())),
                total_sessions=len(state["daily_total_sessions"].get(day, set())),
            )
        )
    return friction_trends


def _infer_workflow_stage(tool_counts: Counter[str]) -> str:
    if not tool_counts:
        return "general"

    stage_counts: Counter[str] = Counter()
    for tool_name, count in tool_counts.items():
        matched_stage = None
        for stage, tool_names in _STAGE_TOOL_WEIGHTS.items():
            if tool_name in tool_names or any(
                tool_name.startswith(f"{prefix}:") for prefix in tool_names if prefix in {"Task"}
            ):
                matched_stage = stage
                break
        if matched_stage is None:
            category = classify_tool(tool_name)
            if category == "search":
                matched_stage = "search"
            elif category == "orchestration" or category == "skill":
                matched_stage = "delegate"
            elif category == "mcp":
                matched_stage = "integrate"
            else:
                matched_stage = "general"
        stage_counts[matched_stage] += count

    primary_stage, _ = stage_counts.most_common(1)[0]
    return primary_stage


def _derive_root_cause_category(
    friction_counts: dict[str, int] | None,
    combined_text: str,
) -> str:
    category_scores: Counter[str] = Counter()
    for friction_type, count in (friction_counts or {}).items():
        category = _ROOT_CAUSE_FRICTION_MAP.get(friction_type)
        if category:
            category_scores[category] += max(count, 1)

    normalized_text = combined_text.lower()
    for category, keywords in _ROOT_CAUSE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized_text:
                category_scores[category] += 1

    if category_scores:
        return category_scores.most_common(1)[0][0]
    return "unknown"


def _extract_transcript_cues(combined_text: str) -> list[str]:
    normalized_text = combined_text.lower()
    cues: list[str] = []
    for keywords in _ROOT_CAUSE_KEYWORDS.values():
        for keyword in keywords:
            if keyword in normalized_text and keyword not in cues:
                cues.append(keyword)
    return cues[:5]


def _root_cause_title(category: str, workflow_stage: str) -> str:
    base = _ROOT_CAUSE_LABELS.get(category, _ROOT_CAUSE_LABELS["unknown"])
    if workflow_stage == "general":
        return base
    return f"{base} during {workflow_stage} work"


def _friction_time_lost_weight(friction_type: str) -> float:
    return _FRICTION_TIME_LOST_MINUTES.get(friction_type, _DEFAULT_FRICTION_TIME_LOST_MINUTES)


def _estimate_session_time_lost_minutes(
    session: SessionModel,
    friction_counts: dict[str, int],
    *,
    outcome: str | None,
    recovery_path: SessionRecoveryPath | None,
) -> tuple[dict[str, float], float]:
    positive_counts = {
        friction_type: count
        for friction_type, count in friction_counts.items()
        if count and count > 0
    }
    if not positive_counts:
        return {}, 0.0

    weighted_minutes = {
        friction_type: _friction_time_lost_weight(friction_type) * count
        for friction_type, count in positive_counts.items()
    }
    base_minutes = sum(weighted_minutes.values())

    extra_minutes = 0.0
    recovery_steps = recovery_path.recovery_step_count if recovery_path is not None else 0
    if recovery_steps > 0:
        extra_minutes += recovery_steps * _RECOVERY_STEP_TIME_LOST_MINUTES

    duration_minutes = max((session.duration_seconds or 0.0) / 60.0, 0.0)
    recovery_result = recovery_path.recovery_result if recovery_path is not None else None
    if outcome == "abandoned" or recovery_result == "abandoned":
        extra_minutes += (
            min(
                duration_minutes * _ABANDONED_SESSION_TIME_LOST_FACTOR,
                _ABANDONED_SESSION_TIME_LOST_CAP_MINUTES,
            )
            if duration_minutes > 0
            else _ABANDONED_SESSION_TIME_LOST_FALLBACK_MINUTES
        )
    elif recovery_result == "unresolved":
        extra_minutes += (
            min(
                duration_minutes * _UNRESOLVED_SESSION_TIME_LOST_FACTOR,
                _UNRESOLVED_SESSION_TIME_LOST_CAP_MINUTES,
            )
            if duration_minutes > 0
            else _UNRESOLVED_SESSION_TIME_LOST_FALLBACK_MINUTES
        )

    total_minutes = base_minutes + extra_minutes
    if duration_minutes > 0:
        total_minutes = min(total_minutes, duration_minutes)
    if total_minutes <= 0:
        return {}, 0.0

    weighted_total = sum(weighted_minutes.values())
    if weighted_total <= 0:
        share = total_minutes / len(positive_counts)
        return ({friction_type: share for friction_type in positive_counts}, total_minutes)

    distributed_minutes = {
        friction_type: total_minutes * (weight / weighted_total)
        for friction_type, weight in weighted_minutes.items()
    }
    return distributed_minutes, total_minutes
