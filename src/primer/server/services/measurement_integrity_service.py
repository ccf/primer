from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from primer.common.facet_taxonomy import canonical_outcome, normalize_goal_categories
from primer.common.models import (
    Engineer,
    GitRepository,
    ModelUsage,
    SessionCommit,
    SessionFacets,
    SessionMessage,
    SessionWorkflowProfile,
    ToolUsage,
)
from primer.common.models import (
    Session as SessionModel,
)
from primer.common.source_capabilities import TelemetryField, get_capability_for

LOW_CONFIDENCE_THRESHOLD = 0.7
LEGACY_OUTCOMES = {
    outcome
    for outcome in (
        "success",
        "partial",
        "failure",
        "fully_achieved",
        "mostly_achieved",
        "partially_achieved",
        "not_achieved",
    )
    if canonical_outcome(outcome) != outcome
}


def _has_legacy_goal_categories(value: object) -> bool:
    return isinstance(value, dict)


def _legacy_goal_categories_predicate(db: Session):
    engine = db.get_bind()
    dialect_name = engine.dialect.name if engine is not None else ""
    if dialect_name == "sqlite":
        return func.json_type(SessionFacets.goal_categories) == "object"
    if dialect_name == "postgresql":
        return func.json_typeof(SessionFacets.goal_categories) == "object"
    return SessionFacets.id.is_(None)


def _legacy_rows_predicate(db: Session):
    return or_(
        SessionFacets.outcome.in_(sorted(LEGACY_OUTCOMES)),
        _legacy_goal_categories_predicate(db),
    )


def _legacy_candidate_query(db: Session, query=None):
    base_query = query if query is not None else db.query(SessionFacets)
    return base_query.filter(_legacy_rows_predicate(db))


def _count_legacy_goal_category_rows(db: Session, query=None) -> int:
    base_query = query if query is not None else db.query(SessionFacets)
    return base_query.filter(_legacy_goal_categories_predicate(db)).count()


def _count_legacy_rows(db: Session, query=None) -> int:
    return _legacy_candidate_query(db, query=query).count()


def _apply_session_scope(
    query,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    if engineer_id:
        query = query.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        query = query.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        query = query.filter(SessionModel.started_at >= start_date)
    if end_date:
        query = query.filter(SessionModel.started_at <= end_date)
    return query


def _scoped_session_ids_subquery(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    return _apply_session_scope(
        db.query(SessionModel.id),
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    ).subquery()


def _scoped_facets_query(db: Session, scoped_session_ids):
    return db.query(SessionFacets).join(
        scoped_session_ids, SessionFacets.session_id == scoped_session_ids.c.id
    )


def _grouped_session_counts(
    db: Session,
    *,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, int]:
    rows = (
        _apply_session_scope(
            db.query(
                SessionModel.agent_type,
                func.count(SessionModel.id),
            ),
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        )
        .group_by(SessionModel.agent_type)
        .all()
    )
    return {agent_type: count for agent_type, count in rows if agent_type}


def _grouped_related_counts(
    db: Session,
    related_model,
    session_key,
    *,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, int]:
    rows = (
        _apply_session_scope(
            db.query(
                SessionModel.agent_type,
                func.count(func.distinct(session_key)),
            ).join(related_model, session_key == SessionModel.id),
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        )
        .group_by(SessionModel.agent_type)
        .all()
    )
    return {agent_type: count for agent_type, count in rows if agent_type}


def _normalized_row_updates(row: SessionFacets) -> dict[str, object]:
    updates: dict[str, object] = {}

    if row.outcome in LEGACY_OUTCOMES:
        updates["outcome"] = canonical_outcome(row.outcome)

    if _has_legacy_goal_categories(row.goal_categories):
        updates["goal_categories"] = normalize_goal_categories(row.goal_categories)

    return updates


def _required_session_count_for_field(
    sessions_by_agent: dict[str, int], field_name: TelemetryField
) -> int:
    return sum(
        session_count
        for agent_type, session_count in sessions_by_agent.items()
        if (capability := get_capability_for(agent_type)) and capability.is_required(field_name)
    )


def _covered_session_count_for_field(
    sessions_by_agent: dict[str, int],
    covered_sessions_by_agent: dict[str, int],
    field_name: TelemetryField,
) -> int:
    return sum(
        covered_sessions_by_agent.get(agent_type, 0)
        for agent_type in sessions_by_agent
        if (capability := get_capability_for(agent_type)) and capability.is_required(field_name)
    )


def _coverage_pct(covered_count: int, total_count: int) -> float:
    return round((covered_count / total_count) * 100, 1) if total_count else 0.0


def _optional_coverage_pct(covered_count: int, total_count: int) -> float | None:
    return round((covered_count / total_count) * 100, 1) if total_count else None


def get_measurement_integrity_stats(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, object]:
    scoped_session_ids = _scoped_session_ids_subquery(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )
    total_sessions = db.query(func.count()).select_from(scoped_session_ids).scalar() or 0
    sessions_with_messages = (
        db.query(func.count(func.distinct(SessionMessage.session_id)))
        .join(scoped_session_ids, SessionMessage.session_id == scoped_session_ids.c.id)
        .scalar()
        or 0
    )
    sessions_with_facets = _scoped_facets_query(db, scoped_session_ids).count()
    sessions_with_workflow_profiles = (
        db.query(func.count(func.distinct(SessionWorkflowProfile.session_id)))
        .join(scoped_session_ids, SessionWorkflowProfile.session_id == scoped_session_ids.c.id)
        .scalar()
        or 0
    )
    low_confidence_sessions = (
        _scoped_facets_query(db, scoped_session_ids)
        .filter(
            SessionFacets.confidence_score.isnot(None),
            SessionFacets.confidence_score < LOW_CONFIDENCE_THRESHOLD,
        )
        .count()
    )
    missing_confidence_sessions = (
        _scoped_facets_query(db, scoped_session_ids)
        .filter(SessionFacets.confidence_score.is_(None))
        .count()
    )
    legacy_outcome_sessions = (
        _scoped_facets_query(db, scoped_session_ids)
        .filter(SessionFacets.outcome.in_(sorted(LEGACY_OUTCOMES)))
        .count()
    )
    legacy_goal_category_sessions = _count_legacy_goal_category_rows(
        db, query=_scoped_facets_query(db, scoped_session_ids)
    )
    remaining_legacy_rows = _count_legacy_rows(
        db, query=_scoped_facets_query(db, scoped_session_ids)
    )
    sessions_by_agent = _grouped_session_counts(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )
    transcript_sessions_by_agent = _grouped_related_counts(
        db,
        SessionMessage,
        SessionMessage.session_id,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )
    tool_sessions_by_agent = _grouped_related_counts(
        db,
        ToolUsage,
        ToolUsage.session_id,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )
    model_sessions_by_agent = _grouped_related_counts(
        db,
        ModelUsage,
        ModelUsage.session_id,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )
    facet_sessions_by_agent = _grouped_related_counts(
        db,
        SessionFacets,
        SessionFacets.session_id,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )
    workflow_profile_sessions_by_agent = _grouped_related_counts(
        db,
        SessionWorkflowProfile,
        SessionWorkflowProfile.session_id,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )
    required_transcript_session_count = _required_session_count_for_field(
        sessions_by_agent, "transcript"
    )
    required_transcript_sessions_with_messages = _covered_session_count_for_field(
        sessions_by_agent,
        transcript_sessions_by_agent,
        "transcript",
    )
    required_tool_session_count = _required_session_count_for_field(sessions_by_agent, "tool_calls")
    required_tool_sessions_with_telemetry = _covered_session_count_for_field(
        sessions_by_agent,
        tool_sessions_by_agent,
        "tool_calls",
    )
    required_model_session_count = _required_session_count_for_field(
        sessions_by_agent, "model_usage"
    )
    required_model_sessions_with_telemetry = _covered_session_count_for_field(
        sessions_by_agent,
        model_sessions_by_agent,
        "model_usage",
    )
    required_facet_session_count = _required_session_count_for_field(sessions_by_agent, "facets")
    required_facet_sessions_with_facets = _covered_session_count_for_field(
        sessions_by_agent,
        facet_sessions_by_agent,
        "facets",
    )
    sessions_with_commit_sync_target = (
        _apply_session_scope(
            db.query(func.count(func.distinct(SessionCommit.session_id)))
            .join(SessionModel, SessionCommit.session_id == SessionModel.id)
            .filter(SessionModel.repository_id.isnot(None)),
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        ).scalar()
        or 0
    )
    sessions_with_linked_pull_requests = (
        _apply_session_scope(
            db.query(func.count(func.distinct(SessionCommit.session_id)))
            .join(SessionModel, SessionCommit.session_id == SessionModel.id)
            .filter(
                SessionModel.repository_id.isnot(None),
                SessionCommit.pull_request_id.isnot(None),
            ),
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        ).scalar()
        or 0
    )
    repository_rows = (
        _apply_session_scope(
            db.query(
                SessionModel.repository_id.label("repository_id"),
                GitRepository.full_name.label("repository_full_name"),
                GitRepository.github_id.label("github_id"),
                GitRepository.default_branch.label("default_branch"),
                GitRepository.ai_readiness_checked_at.label("ai_readiness_checked_at"),
                func.count(SessionModel.id).label("session_count"),
            )
            .join(GitRepository, SessionModel.repository_id == GitRepository.id)
            .filter(SessionModel.repository_id.isnot(None)),
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        )
        .group_by(
            SessionModel.repository_id,
            GitRepository.full_name,
            GitRepository.github_id,
            GitRepository.default_branch,
            GitRepository.ai_readiness_checked_at,
        )
        .order_by(func.count(SessionModel.id).desc(), GitRepository.full_name.asc())
        .all()
    )
    repository_commit_rows = (
        _apply_session_scope(
            db.query(
                SessionModel.repository_id.label("repository_id"),
                func.count(func.distinct(SessionCommit.session_id)).label("sessions_with_commits"),
            )
            .join(SessionCommit, SessionCommit.session_id == SessionModel.id)
            .filter(SessionModel.repository_id.isnot(None)),
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        )
        .group_by(SessionModel.repository_id)
        .all()
    )
    repository_linked_pr_rows = (
        _apply_session_scope(
            db.query(
                SessionModel.repository_id.label("repository_id"),
                func.count(func.distinct(SessionCommit.session_id)).label(
                    "sessions_with_linked_pull_requests"
                ),
            )
            .join(SessionCommit, SessionCommit.session_id == SessionModel.id)
            .filter(
                SessionModel.repository_id.isnot(None),
                SessionCommit.pull_request_id.isnot(None),
            ),
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        )
        .group_by(SessionModel.repository_id)
        .all()
    )

    facet_coverage_pct = _coverage_pct(
        required_facet_sessions_with_facets, required_facet_session_count
    )
    transcript_coverage_pct = _coverage_pct(
        required_transcript_sessions_with_messages, required_transcript_session_count
    )
    workflow_profile_coverage_pct = _coverage_pct(
        sessions_with_workflow_profiles,
        total_sessions,
    )
    github_sync_coverage_pct = _coverage_pct(
        sessions_with_linked_pull_requests, sessions_with_commit_sync_target
    )
    sessions_missing_transcript_telemetry = max(
        required_transcript_session_count - required_transcript_sessions_with_messages,
        0,
    )
    sessions_missing_tool_telemetry = max(
        required_tool_session_count - required_tool_sessions_with_telemetry,
        0,
    )
    sessions_missing_model_telemetry = max(
        required_model_session_count - required_model_sessions_with_telemetry,
        0,
    )
    source_quality: list[dict[str, str | int | float]] = []
    repository_commit_counts = {
        row.repository_id: row.sessions_with_commits for row in repository_commit_rows
    }
    repository_linked_pr_counts = {
        row.repository_id: row.sessions_with_linked_pull_requests
        for row in repository_linked_pr_rows
    }
    repository_quality: list[dict[str, str | int | float | bool | None]] = []
    workflow_profile_quality: list[dict[str, str | int | float]] = []
    for row in repository_rows:
        has_github_id = row.github_id is not None
        has_default_branch = row.default_branch is not None
        readiness_checked = row.ai_readiness_checked_at is not None
        sessions_with_commits = repository_commit_counts.get(row.repository_id, 0)
        repo_sessions_with_linked_pull_requests = repository_linked_pr_counts.get(
            row.repository_id, 0
        )
        metadata_coverage_pct = _coverage_pct(
            int(has_github_id) + int(has_default_branch),
            2,
        )
        repository_quality.append(
            {
                "repository_full_name": row.repository_full_name,
                "session_count": row.session_count,
                "sessions_with_commits": sessions_with_commits,
                "sessions_with_linked_pull_requests": repo_sessions_with_linked_pull_requests,
                "github_sync_coverage_pct": _optional_coverage_pct(
                    repo_sessions_with_linked_pull_requests,
                    sessions_with_commits,
                ),
                "has_github_id": has_github_id,
                "has_default_branch": has_default_branch,
                "metadata_coverage_pct": metadata_coverage_pct,
                "readiness_checked": readiness_checked,
            }
        )

    repositories_in_scope = len(repository_quality)
    repositories_with_complete_metadata = sum(
        1
        for row in repository_quality
        if bool(row["has_github_id"]) and bool(row["has_default_branch"])
    )
    repositories_with_readiness_check = sum(
        1 for row in repository_quality if bool(row["readiness_checked"])
    )
    repository_metadata_coverage_pct = _coverage_pct(
        repositories_with_complete_metadata,
        repositories_in_scope,
    )

    for agent_type in sorted(sessions_by_agent):
        session_count = sessions_by_agent[agent_type]
        capability = get_capability_for(agent_type)
        transcript_count = transcript_sessions_by_agent.get(agent_type, 0)
        tool_count = tool_sessions_by_agent.get(agent_type, 0)
        model_count = model_sessions_by_agent.get(agent_type, 0)
        facet_count = facet_sessions_by_agent.get(agent_type, 0)
        transcript_parity = capability.parity_for("transcript") if capability else "unavailable"
        tool_call_parity = capability.parity_for("tool_calls") if capability else "unavailable"
        model_usage_parity = capability.parity_for("model_usage") if capability else "unavailable"
        facet_parity = capability.parity_for("facets") if capability else "unavailable"
        native_discovery_parity = (
            capability.parity_for("native_discovery") if capability else "unavailable"
        )

        source_quality.append(
            {
                "agent_type": agent_type,
                "session_count": session_count,
                "transcript_parity": transcript_parity,
                "transcript_coverage_pct": round((transcript_count / session_count) * 100, 1)
                if session_count
                else 0.0,
                "tool_call_parity": tool_call_parity,
                "tool_call_coverage_pct": round((tool_count / session_count) * 100, 1)
                if session_count
                else 0.0,
                "model_usage_parity": model_usage_parity,
                "model_usage_coverage_pct": round((model_count / session_count) * 100, 1)
                if session_count
                else 0.0,
                "facet_parity": facet_parity,
                "facet_coverage_pct": round((facet_count / session_count) * 100, 1)
                if capability and capability.supports_facets and session_count
                else 0.0,
                "native_discovery_parity": native_discovery_parity,
            }
        )

        workflow_profile_quality.append(
            {
                "agent_type": agent_type,
                "session_count": session_count,
                "sessions_with_workflow_profiles": workflow_profile_sessions_by_agent.get(
                    agent_type, 0
                ),
                "workflow_profile_coverage_pct": _coverage_pct(
                    workflow_profile_sessions_by_agent.get(agent_type, 0),
                    session_count,
                ),
            }
        )

    return {
        "total_sessions": total_sessions,
        "sessions_with_messages": sessions_with_messages,
        "sessions_with_facets": sessions_with_facets,
        "sessions_with_workflow_profiles": sessions_with_workflow_profiles,
        "facet_coverage_pct": facet_coverage_pct,
        "transcript_coverage_pct": transcript_coverage_pct,
        "workflow_profile_coverage_pct": workflow_profile_coverage_pct,
        "sessions_with_commit_sync_target": sessions_with_commit_sync_target,
        "sessions_with_linked_pull_requests": sessions_with_linked_pull_requests,
        "github_sync_coverage_pct": github_sync_coverage_pct,
        "repositories_in_scope": repositories_in_scope,
        "repositories_with_complete_metadata": repositories_with_complete_metadata,
        "repositories_with_readiness_check": repositories_with_readiness_check,
        "repository_metadata_coverage_pct": repository_metadata_coverage_pct,
        "low_confidence_sessions": low_confidence_sessions,
        "missing_confidence_sessions": missing_confidence_sessions,
        "legacy_outcome_sessions": legacy_outcome_sessions,
        "legacy_goal_category_sessions": legacy_goal_category_sessions,
        "remaining_legacy_rows": remaining_legacy_rows,
        "sessions_missing_transcript_telemetry": sessions_missing_transcript_telemetry,
        "sessions_missing_tool_telemetry": sessions_missing_tool_telemetry,
        "sessions_missing_model_telemetry": sessions_missing_model_telemetry,
        "source_quality": source_quality,
        "repository_quality": repository_quality,
        "workflow_profile_quality": workflow_profile_quality,
    }


def normalize_existing_facets(
    db: Session, limit: int | None = None, dry_run: bool = False
) -> dict[str, int]:
    candidate_query = _legacy_candidate_query(db).order_by(SessionFacets.id)
    if limit is not None:
        candidate_query = candidate_query.limit(limit)

    candidate_rows = candidate_query.all()
    pending_updates = [(row, _normalized_row_updates(row)) for row in candidate_rows]

    if not dry_run:
        for row, updates in pending_updates:
            for field_name, value in updates.items():
                setattr(row, field_name, value)
        db.flush()

    return {
        "rows_scanned": len(candidate_rows),
        "rows_updated": 0 if dry_run else sum(1 for _, updates in pending_updates if updates),
        "remaining_legacy_rows": _count_legacy_rows(db),
    }
