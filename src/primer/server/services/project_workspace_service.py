from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.common.models import (
    GitRepository,
    ModelUsage,
    SessionCommit,
    SessionFacets,
    SessionMessage,
    ToolUsage,
)
from primer.common.models import Session as SessionModel
from primer.common.schemas import (
    FrictionImpact,
    ProjectEnablementSummary,
    ProjectFrictionHotspot,
    ProjectRepositorySummary,
    ProjectScorecard,
    ProjectStats,
    ProjectWorkflowFingerprint,
    ProjectWorkflowSummary,
    ProjectWorkspaceResponse,
)
from primer.common.source_capabilities import CAPABILITIES
from primer.common.tool_classification import classify_tool
from primer.server.services.analytics_service import (
    _filter_sessions_by_capability,
    base_session_query,
    get_bottleneck_analytics,
    get_cost_analytics,
    get_overview,
    get_productivity_metrics,
)
from primer.server.services.effectiveness_service import (
    build_effectiveness_score,
    get_peer_cost_per_success_benchmark,
)
from primer.server.services.quality_service import get_quality_metrics


def get_project_workspace(
    db: Session,
    project_name: str,
    *,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> ProjectWorkspaceResponse | None:
    session_q = base_session_query(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
        project_name=project_name,
    )
    total_sessions = session_q.count()
    if total_sessions == 0:
        return None

    overview = get_overview(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
        project_name=project_name,
    )
    productivity = get_productivity_metrics(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
        project_name=project_name,
    )
    cost = get_cost_analytics(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
        project_name=project_name,
    )
    quality = get_quality_metrics(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
        project_name=project_name,
    )
    bottlenecks = get_bottleneck_analytics(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
        project_name=project_name,
    )

    enablement = _build_enablement_summary(db, session_q)
    repositories = _build_repository_summary(db, session_q)
    workflow_summary = _build_workflow_summary(
        db,
        session_q,
        bottlenecks.friction_impacts,
    )
    project = ProjectStats(
        project_name=project_name,
        total_sessions=overview.total_sessions,
        unique_engineers=overview.total_engineers,
        total_tokens=overview.total_input_tokens + overview.total_output_tokens,
        estimated_cost=cost.total_estimated_cost,
        outcome_distribution=overview.outcome_counts,
        top_tools=enablement.top_tools,
    )
    effectiveness_score = build_effectiveness_score(
        success_rate=overview.success_rate,
        cost_per_successful_outcome=productivity.cost_per_successful_outcome,
        benchmark_cost_per_successful_outcome=get_peer_cost_per_success_benchmark(
            db,
            group_by="project_name",
            target_value=project_name,
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        ),
        pr_merge_rate=quality.overview.pr_merge_rate,
        findings_fix_rate=(
            quality.findings_overview.fix_rate if quality.findings_overview else None
        ),
        total_sessions=overview.total_sessions,
        sessions_with_commits=quality.overview.sessions_with_commits,
    )
    scorecard = ProjectScorecard(
        adoption_rate=productivity.adoption_rate,
        effectiveness_rate=overview.success_rate,
        effectiveness_score=effectiveness_score,
        quality_rate=(
            quality.findings_overview.fix_rate
            if quality.findings_overview and quality.findings_overview.fix_rate is not None
            else quality.overview.pr_merge_rate
        ),
        avg_cost_per_session=productivity.avg_cost_per_session,
        cost_per_successful_outcome=productivity.cost_per_successful_outcome,
        measurement_confidence=_compute_measurement_confidence(db, session_q),
    )

    friction = next(
        (item for item in bottlenecks.project_friction if item.project_name == project_name),
        None,
    )

    return ProjectWorkspaceResponse(
        project=project,
        scorecard=scorecard,
        overview=overview,
        productivity=productivity,
        cost=cost,
        quality=quality,
        friction=friction,
        friction_impacts=bottlenecks.friction_impacts[:5],
        repositories=repositories,
        enablement=enablement,
        workflow_summary=workflow_summary,
    )


def _build_enablement_summary(db: Session, session_q) -> ProjectEnablementSummary:
    session_id_q = session_q.with_entities(SessionModel.id)

    agent_counts = Counter(
        agent_type
        for (agent_type,) in session_q.with_entities(SessionModel.agent_type).all()
        if agent_type
    )
    permission_counts = Counter(
        permission_mode
        for (permission_mode,) in session_q.with_entities(SessionModel.permission_mode)
        .filter(SessionModel.permission_mode.isnot(None))
        .all()
        if permission_mode
    )

    session_type_rows = (
        db.query(SessionFacets.session_type)
        .join(SessionModel, SessionFacets.session_id == SessionModel.id)
        .filter(
            SessionModel.id.in_(session_id_q),
            SessionFacets.session_type.isnot(None),
        )
        .all()
    )
    session_type_counts = Counter(
        session_type for (session_type,) in session_type_rows if session_type
    )

    tool_rows = (
        db.query(ToolUsage.tool_name, func.sum(ToolUsage.call_count).label("total_calls"))
        .join(SessionModel, ToolUsage.session_id == SessionModel.id)
        .filter(SessionModel.id.in_(session_id_q))
    )
    tool_rows = _filter_sessions_by_capability(tool_rows, "supports_tool_calls")
    top_tools = [
        tool_name
        for tool_name, _ in tool_rows.group_by(ToolUsage.tool_name)
        .order_by(func.sum(ToolUsage.call_count).desc())
        .limit(5)
        .all()
    ]

    model_rows = (
        db.query(
            ModelUsage.model_name,
            func.coalesce(func.sum(ModelUsage.input_tokens + ModelUsage.output_tokens), 0).label(
                "total_tokens"
            ),
        )
        .join(SessionModel, ModelUsage.session_id == SessionModel.id)
        .filter(SessionModel.id.in_(session_id_q))
    )
    model_rows = _filter_sessions_by_capability(model_rows, "supports_model_usage")
    top_models = [
        model_name
        for model_name, _ in model_rows.group_by(ModelUsage.model_name)
        .order_by(func.sum(ModelUsage.input_tokens + ModelUsage.output_tokens).desc())
        .limit(5)
        .all()
    ]

    linked_repository_count = (
        session_q.filter(SessionModel.repository_id.isnot(None))
        .with_entities(func.count(distinct(SessionModel.repository_id)))
        .scalar()
        or 0
    )

    return ProjectEnablementSummary(
        linked_repository_count=linked_repository_count,
        agent_type_counts=dict(agent_counts),
        session_type_counts=dict(session_type_counts),
        permission_mode_counts=dict(permission_counts),
        top_tools=top_tools,
        top_models=top_models,
    )


def _build_repository_summary(db: Session, session_q) -> list[ProjectRepositorySummary]:
    repo_rows = (
        session_q.filter(SessionModel.repository_id.isnot(None))
        .with_entities(
            SessionModel.repository_id,
            func.count(SessionModel.id).label("session_count"),
        )
        .group_by(SessionModel.repository_id)
        .all()
    )
    if not repo_rows:
        return []

    session_counts = {repo_id: session_count for repo_id, session_count in repo_rows if repo_id}
    repos = (
        db.query(GitRepository)
        .filter(GitRepository.id.in_(list(session_counts.keys())))
        .order_by(GitRepository.full_name.asc())
        .all()
    )

    return [
        ProjectRepositorySummary(
            repository=repo.full_name,
            session_count=session_counts.get(repo.id, 0),
            default_branch=repo.default_branch,
            readiness_checked=repo.ai_readiness_checked_at is not None,
            ai_readiness_score=repo.ai_readiness_score,
            has_claude_md=repo.has_claude_md,
            has_agents_md=repo.has_agents_md,
            has_claude_dir=repo.has_claude_dir,
        )
        for repo in repos
    ]


def _compute_measurement_confidence(db: Session, session_q) -> float | None:
    sessions = session_q.with_entities(SessionModel.id, SessionModel.agent_type).all()
    if not sessions:
        return None

    session_ids = [session_id for session_id, _ in sessions]
    message_session_ids = {
        session_id
        for (session_id,) in db.query(distinct(SessionMessage.session_id))
        .filter(SessionMessage.session_id.in_(session_ids))
        .all()
    }
    tool_session_ids = {
        session_id
        for (session_id,) in db.query(distinct(ToolUsage.session_id))
        .filter(ToolUsage.session_id.in_(session_ids))
        .all()
    }
    model_session_ids = {
        session_id
        for (session_id,) in db.query(distinct(ModelUsage.session_id))
        .filter(ModelUsage.session_id.in_(session_ids))
        .all()
    }
    facet_session_ids = {
        session_id
        for (session_id,) in db.query(distinct(SessionFacets.session_id))
        .filter(SessionFacets.session_id.in_(session_ids))
        .all()
    }

    expected = {"transcript": 0, "tool": 0, "model": 0, "facets": 0}
    actual = {"transcript": 0, "tool": 0, "model": 0, "facets": 0}

    for session_id, agent_type in sessions:
        capability = CAPABILITIES.get(agent_type)
        if capability is None:
            continue
        if capability.supports_transcript:
            expected["transcript"] += 1
            if session_id in message_session_ids:
                actual["transcript"] += 1
        if capability.supports_tool_calls:
            expected["tool"] += 1
            if session_id in tool_session_ids:
                actual["tool"] += 1
        if capability.supports_model_usage:
            expected["model"] += 1
            if session_id in model_session_ids:
                actual["model"] += 1
        if capability.supports_facets:
            expected["facets"] += 1
            if session_id in facet_session_ids:
                actual["facets"] += 1

    coverage_values = [actual[key] / expected[key] for key in expected if expected[key] > 0]
    if not coverage_values:
        return None
    return round(sum(coverage_values) / len(coverage_values), 3)


def _build_workflow_summary(
    db: Session,
    session_q,
    friction_impacts: list[FrictionImpact],
) -> ProjectWorkflowSummary:
    session_rows = session_q.with_entities(
        SessionModel.id,
        SessionModel.duration_seconds,
    ).all()
    total_sessions = len(session_rows)
    if total_sessions == 0:
        return ProjectWorkflowSummary(
            fingerprinted_sessions=0,
            total_sessions=0,
            coverage_pct=0.0,
        )

    session_ids = [session_id for session_id, _ in session_rows]
    duration_by_session = {session_id: duration for session_id, duration in session_rows}

    facet_rows = (
        db.query(
            SessionFacets.session_id,
            SessionFacets.session_type,
            SessionFacets.outcome,
            SessionFacets.friction_counts,
            SessionFacets.friction_detail,
        )
        .filter(SessionFacets.session_id.in_(session_ids))
        .all()
    )
    facets_by_session = {
        row.session_id: {
            "session_type": row.session_type,
            "outcome": row.outcome,
            "friction_counts": row.friction_counts or {},
            "friction_detail": row.friction_detail,
        }
        for row in facet_rows
    }

    tool_counts_by_session: dict[str, Counter[str]] = defaultdict(Counter)
    for session_id, tool_name, call_count in (
        db.query(ToolUsage.session_id, ToolUsage.tool_name, ToolUsage.call_count)
        .filter(ToolUsage.session_id.in_(session_ids))
        .all()
    ):
        tool_counts_by_session[session_id][tool_name] += call_count

    commit_session_ids = {
        session_id
        for (session_id,) in db.query(distinct(SessionCommit.session_id))
        .filter(SessionCommit.session_id.in_(session_ids))
        .all()
    }
    impact_by_type = {item.friction_type: item.impact_score for item in friction_impacts}

    fingerprinted_sessions = 0
    fingerprints: dict[str, dict] = {}
    hotspot_counts: dict[str, dict] = {}
    label_by_key: dict[str, str] = {}

    for session_id in session_ids:
        facets = facets_by_session.get(session_id, {})
        session_type = facets.get("session_type")
        tool_counts = tool_counts_by_session.get(session_id, Counter())
        steps = _infer_workflow_steps(tool_counts, session_id in commit_session_ids)
        if not session_type and not steps:
            continue

        fingerprinted_sessions += 1
        fingerprint_id = _fingerprint_id(session_type, steps)
        label = _fingerprint_label(session_type, steps)
        label_by_key[fingerprint_id] = label

        bucket = fingerprints.setdefault(
            fingerprint_id,
            {
                "label": label,
                "session_type": session_type,
                "steps": steps,
                "session_count": 0,
                "success_count": 0,
                "outcome_count": 0,
                "durations": [],
                "tool_counts": Counter(),
                "friction_counts": Counter(),
            },
        )
        bucket["session_count"] += 1
        if duration_by_session.get(session_id) is not None:
            bucket["durations"].append(duration_by_session[session_id])
        bucket["tool_counts"].update(tool_counts)

        if (outcome := canonical_outcome(facets.get("outcome"))) is not None:
            bucket["outcome_count"] += 1
            if is_success_outcome(outcome):
                bucket["success_count"] += 1

        friction_counts = facets.get("friction_counts") or {}
        if friction_counts:
            bucket["friction_counts"].update(friction_counts)
            for friction_type, count in friction_counts.items():
                if count <= 0:
                    continue
                hotspot = hotspot_counts.setdefault(
                    friction_type,
                    {
                        "session_ids": set(),
                        "occurrences": 0,
                        "fingerprint_counts": Counter(),
                        "sample_details": [],
                    },
                )
                hotspot["session_ids"].add(session_id)
                hotspot["occurrences"] += count
                hotspot["fingerprint_counts"][fingerprint_id] += 1
                detail = facets.get("friction_detail")
                if detail and detail not in hotspot["sample_details"]:
                    hotspot["sample_details"].append(detail)

    fingerprint_rows = [
        ProjectWorkflowFingerprint(
            fingerprint_id=fingerprint_id,
            label=bucket["label"],
            session_type=bucket["session_type"],
            steps=list(bucket["steps"]),
            session_count=bucket["session_count"],
            share_of_sessions=round(bucket["session_count"] / total_sessions, 3),
            success_rate=(
                round(bucket["success_count"] / bucket["outcome_count"], 3)
                if bucket["outcome_count"] > 0
                else None
            ),
            avg_duration_seconds=(
                round(sum(bucket["durations"]) / len(bucket["durations"]), 1)
                if bucket["durations"]
                else None
            ),
            top_tools=[tool_name for tool_name, _ in bucket["tool_counts"].most_common(3)],
            top_friction_types=[
                friction_type for friction_type, _ in bucket["friction_counts"].most_common(3)
            ],
        )
        for fingerprint_id, bucket in sorted(
            fingerprints.items(),
            key=lambda item: (
                item[1]["session_count"],
                item[1]["success_count"],
            ),
            reverse=True,
        )[:5]
    ]

    hotspot_rows = [
        ProjectFrictionHotspot(
            friction_type=friction_type,
            session_count=len(bucket["session_ids"]),
            share_of_sessions=round(len(bucket["session_ids"]) / total_sessions, 3),
            total_occurrences=bucket["occurrences"],
            impact_score=impact_by_type.get(friction_type),
            linked_fingerprints=[
                label_by_key[fingerprint_id]
                for fingerprint_id, _ in bucket["fingerprint_counts"].most_common(3)
                if fingerprint_id in label_by_key
            ],
            sample_details=bucket["sample_details"][:2],
        )
        for friction_type, bucket in sorted(
            hotspot_counts.items(),
            key=lambda item: (len(item[1]["session_ids"]), item[1]["occurrences"]),
            reverse=True,
        )[:5]
    ]

    return ProjectWorkflowSummary(
        fingerprinted_sessions=fingerprinted_sessions,
        total_sessions=total_sessions,
        coverage_pct=round(fingerprinted_sessions / total_sessions, 3),
        fingerprints=fingerprint_rows,
        friction_hotspots=hotspot_rows,
    )


def _infer_workflow_steps(tool_counts: Counter[str], has_commit: bool) -> list[str]:
    tool_names = set(tool_counts)
    steps: list[str] = []
    if any(classify_tool(name) == "search" for name in tool_names):
        steps.append("search")
    if tool_names.intersection({"Read", "WebFetch"}):
        steps.append("read")
    if tool_names.intersection({"Edit", "Write", "NotebookEdit"}):
        steps.append("edit")
    if "Bash" in tool_names:
        steps.append("execute")
    if any(classify_tool(name) in {"orchestration", "skill"} for name in tool_names):
        steps.append("delegate")
    if any(classify_tool(name) == "mcp" for name in tool_names):
        steps.append("integrate")
    if has_commit:
        steps.append("ship")
    return steps


def _fingerprint_id(session_type: str | None, steps: list[str]) -> str:
    normalized_type = session_type or "general"
    normalized_steps = "+".join(steps) if steps else "reasoning"
    return f"{normalized_type}::{normalized_steps}"


def _fingerprint_label(session_type: str | None, steps: list[str]) -> str:
    type_label = (session_type or "general").replace("_", " ")
    step_label = " -> ".join(steps) if steps else "reasoning"
    return f"{type_label}: {step_label}"
