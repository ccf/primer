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
    SessionWorkflowProfile,
    ToolUsage,
)
from primer.common.models import Session as SessionModel
from primer.common.pricing import estimate_cost
from primer.common.schemas import (
    CrossProjectComparisonEntry,
    CrossProjectComparisonResponse,
    FrictionImpact,
    LanguageShare,
    ProjectAgentMixEntry,
    ProjectAgentMixSummary,
    ProjectEnablementSummary,
    ProjectFrictionHotspot,
    ProjectRepositoryContextSummary,
    ProjectRepositorySummary,
    ProjectScorecard,
    ProjectStats,
    ProjectWorkflowFingerprint,
    ProjectWorkflowSummary,
    ProjectWorkspaceResponse,
    Recommendation,
)
from primer.common.source_capabilities import CAPABILITIES
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
from primer.server.services.workflow_patterns import (
    infer_workflow_steps,
    workflow_fingerprint_id,
    workflow_fingerprint_label,
)

_PROJECT_CONTEXT_FRICTION = {"context_switching", "edit_conflict"}
_PROJECT_TOOLING_FRICTION = {"tool_error", "timeout", "exec_error"}


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
    agent_mix = _build_project_agent_mix(db, session_q)
    repositories = _build_repository_summary(db, session_q)
    repository_context = _build_repository_context_summary(repositories)
    workflow_summary = _build_workflow_summary(
        db,
        session_q,
        bottlenecks.friction_impacts,
    )
    friction = next(
        (item for item in bottlenecks.project_friction if item.project_name == project_name),
        None,
    )
    enablement = enablement.model_copy(
        update={
            "recommendations": _build_project_enablement_recommendations(
                enablement,
                repositories,
                workflow_summary,
                friction,
            )
        }
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
        agent_mix=agent_mix,
        repository_context=repository_context,
        workflow_summary=workflow_summary,
    )


def get_cross_project_comparison(
    db: Session,
    *,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 3,
    max_projects: int = 20,
) -> CrossProjectComparisonResponse:
    project_rows = (
        base_session_query(
            db,
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        )
        .filter(SessionModel.project_name.isnot(None))
        .with_entities(
            SessionModel.project_name,
            func.count(SessionModel.id).label("session_count"),
        )
        .group_by(SessionModel.project_name)
        .order_by(func.count(SessionModel.id).desc())
        .limit(max_projects)
        .all()
    )

    entries: list[CrossProjectComparisonEntry] = []
    for project_name, _session_count in project_rows:
        if not project_name:
            continue
        workspace = get_project_workspace(
            db,
            project_name,
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        )
        if workspace is None:
            continue
        entries.append(_build_cross_project_comparison_entry(workspace))

    eligible_entries = [entry for entry in entries if entry.effectiveness_score is not None]
    easiest_projects = sorted(
        eligible_entries,
        key=_easiest_project_sort_key,
        reverse=True,
    )[:limit]
    hardest_projects = sorted(eligible_entries, key=_hardest_project_sort_key)[:limit]

    return CrossProjectComparisonResponse(
        compared_projects=len(eligible_entries),
        easiest_projects=easiest_projects,
        hardest_projects=hardest_projects,
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


def _build_cross_project_comparison_entry(
    workspace: ProjectWorkspaceResponse,
) -> CrossProjectComparisonEntry:
    readiness_scores = [
        repo.ai_readiness_score
        for repo in workspace.repositories
        if repo.ai_readiness_score is not None
    ]
    avg_readiness_score = (
        round(sum(readiness_scores) / len(readiness_scores), 1) if readiness_scores else None
    )
    top_recommendation_title = (
        workspace.enablement.recommendations[0].title
        if workspace.enablement.recommendations
        else None
    )

    return CrossProjectComparisonEntry(
        project_name=workspace.project.project_name,
        total_sessions=workspace.project.total_sessions,
        unique_engineers=workspace.project.unique_engineers,
        effectiveness_score=workspace.scorecard.effectiveness_score.score
        if workspace.scorecard.effectiveness_score
        else None,
        effectiveness_rate=workspace.scorecard.effectiveness_rate,
        quality_rate=workspace.scorecard.quality_rate,
        friction_rate=workspace.friction.friction_rate if workspace.friction else None,
        avg_cost_per_session=workspace.scorecard.avg_cost_per_session,
        measurement_confidence=workspace.scorecard.measurement_confidence,
        ai_readiness_score=avg_readiness_score,
        dominant_agent_type=workspace.agent_mix.dominant_agent_type,
        top_recommendation_title=top_recommendation_title,
    )


def _easiest_project_sort_key(entry: CrossProjectComparisonEntry) -> tuple[float, ...]:
    return (
        entry.effectiveness_score if entry.effectiveness_score is not None else -1.0,
        entry.quality_rate if entry.quality_rate is not None else -1.0,
        -(entry.friction_rate if entry.friction_rate is not None else 1.0),
        entry.measurement_confidence if entry.measurement_confidence is not None else -1.0,
        entry.ai_readiness_score if entry.ai_readiness_score is not None else -1.0,
        float(entry.total_sessions),
    )


def _hardest_project_sort_key(entry: CrossProjectComparisonEntry) -> tuple[float, ...]:
    return (
        entry.effectiveness_score if entry.effectiveness_score is not None else 101.0,
        -(entry.friction_rate or 0.0),
        entry.quality_rate if entry.quality_rate is not None else 1.0,
        entry.ai_readiness_score if entry.ai_readiness_score is not None else 101.0,
        -(entry.measurement_confidence or 0.0),
        -float(entry.total_sessions),
    )


def _build_project_agent_mix(db: Session, session_q) -> ProjectAgentMixSummary:
    from primer.server.services.session_insights_service import compute_session_health_score

    session_rows = session_q.with_entities(
        SessionModel.id,
        SessionModel.agent_type,
        SessionModel.engineer_id,
    ).all()
    if not session_rows:
        return ProjectAgentMixSummary(total_sessions=0, compared_agents=0)

    session_ids = [session_id for session_id, _, _ in session_rows]
    session_counts: Counter[str] = Counter()
    engineer_ids_by_agent: defaultdict[str, set[str]] = defaultdict(set)
    for _session_id, agent_type, engineer_id in session_rows:
        if not agent_type:
            continue
        session_counts[agent_type] += 1
        engineer_ids_by_agent[agent_type].add(engineer_id)

    health_inputs_by_agent: defaultdict[str, list[tuple]] = defaultdict(list)
    facet_rows = (
        db.query(
            SessionModel.agent_type,
            SessionFacets.outcome,
            SessionFacets.friction_counts,
            SessionFacets.user_satisfaction_counts,
            SessionFacets.primary_success,
            SessionModel.duration_seconds,
        )
        .join(SessionFacets, SessionFacets.session_id == SessionModel.id)
        .filter(
            SessionModel.id.in_(session_ids),
            SessionModel.agent_type.isnot(None),
        )
    )
    facet_rows = _filter_sessions_by_capability(facet_rows, "supports_facets")
    for (
        agent_type,
        outcome,
        friction_counts,
        satisfaction_counts,
        primary_success,
        duration,
    ) in facet_rows.all():
        if not agent_type:
            continue
        health_inputs_by_agent[agent_type].append(
            (
                outcome,
                friction_counts,
                satisfaction_counts,
                primary_success,
                duration,
            )
        )

    tool_counts_by_agent: defaultdict[str, Counter[str]] = defaultdict(Counter)
    tool_rows = (
        db.query(
            SessionModel.agent_type,
            ToolUsage.tool_name,
            func.sum(ToolUsage.call_count).label("total_calls"),
        )
        .join(SessionModel, ToolUsage.session_id == SessionModel.id)
        .filter(
            SessionModel.id.in_(session_ids),
            SessionModel.agent_type.isnot(None),
        )
        .group_by(SessionModel.agent_type, ToolUsage.tool_name)
        .all()
    )
    for agent_type, tool_name, total_calls in tool_rows:
        if agent_type and tool_name and total_calls:
            tool_counts_by_agent[agent_type][tool_name] = int(total_calls)

    model_tokens_by_agent: defaultdict[str, Counter[str]] = defaultdict(Counter)
    session_costs_by_agent: defaultdict[str, dict[str, float]] = defaultdict(dict)
    model_rows = (
        db.query(
            SessionModel.agent_type,
            ModelUsage.session_id,
            ModelUsage.model_name,
            func.coalesce(func.sum(ModelUsage.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ModelUsage.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(ModelUsage.cache_read_tokens), 0).label("cache_read_tokens"),
            func.coalesce(
                func.sum(ModelUsage.cache_creation_tokens),
                0,
            ).label("cache_creation_tokens"),
        )
        .join(SessionModel, ModelUsage.session_id == SessionModel.id)
        .filter(
            SessionModel.id.in_(session_ids),
            SessionModel.agent_type.isnot(None),
        )
        .group_by(SessionModel.agent_type, ModelUsage.session_id, ModelUsage.model_name)
        .all()
    )
    for (
        agent_type,
        session_id,
        model_name,
        input_tokens,
        output_tokens,
        cache_read_tokens,
        cache_creation_tokens,
    ) in model_rows:
        if not agent_type or not model_name:
            continue
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
        model_tokens_by_agent[agent_type][model_name] += total_tokens
        session_costs_by_agent[agent_type][session_id] = session_costs_by_agent[agent_type].get(
            session_id, 0.0
        ) + estimate_cost(
            model_name,
            input_tokens or 0,
            output_tokens or 0,
            cache_read_tokens or 0,
            cache_creation_tokens or 0,
        )

    entries: list[ProjectAgentMixEntry] = []
    total_sessions = len(session_rows)
    for agent_type, session_count in sorted(
        session_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        health_inputs = health_inputs_by_agent.get(agent_type, [])
        outcomes = [
            canonical_outcome(outcome)
            for outcome, *_rest in health_inputs
            if isinstance(outcome, str) and outcome
        ]
        success_rate = None
        if outcomes:
            success_rate = round(
                sum(1 for outcome in outcomes if is_success_outcome(outcome)) / len(outcomes),
                3,
            )

        friction_rate = None
        avg_health_score = None
        if health_inputs:
            sessions_with_friction = sum(
                1
                for _, friction_counts, *_rest in health_inputs
                if isinstance(friction_counts, dict) and sum(friction_counts.values()) > 0
            )
            friction_rate = round(sessions_with_friction / len(health_inputs), 3)

            durations = [duration for *_, duration in health_inputs if duration is not None]
            median_duration = None
            if durations:
                sorted_durations = sorted(durations)
                midpoint = len(sorted_durations) // 2
                median_duration = (
                    sorted_durations[midpoint]
                    if len(sorted_durations) % 2 == 1
                    else (sorted_durations[midpoint - 1] + sorted_durations[midpoint]) / 2
                )

            health_scores = [
                compute_session_health_score(
                    outcome=outcome,
                    friction_counts=friction_counts,
                    duration_seconds=duration,
                    median_duration=median_duration,
                    satisfaction_counts=satisfaction_counts,
                    primary_success=primary_success,
                )
                for outcome, friction_counts, satisfaction_counts, primary_success, duration in (
                    health_inputs
                )
            ]
            avg_health_score = round(sum(health_scores) / len(health_scores), 1)

        agent_costs = session_costs_by_agent.get(agent_type, {})
        avg_cost_per_session = None
        if agent_costs:
            avg_cost_per_session = round(
                sum(agent_costs.values()) / len(agent_costs),
                4,
            )

        entries.append(
            ProjectAgentMixEntry(
                agent_type=agent_type,
                session_count=session_count,
                share_of_sessions=round(session_count / total_sessions, 3),
                unique_engineers=len(engineer_ids_by_agent.get(agent_type, set())),
                success_rate=success_rate,
                friction_rate=friction_rate,
                avg_health_score=avg_health_score,
                avg_cost_per_session=avg_cost_per_session,
                top_tools=[
                    tool_name
                    for tool_name, _count in tool_counts_by_agent.get(
                        agent_type,
                        Counter(),
                    ).most_common(3)
                ],
                top_models=[
                    model_name
                    for model_name, _tokens in model_tokens_by_agent.get(
                        agent_type,
                        Counter(),
                    ).most_common(3)
                ],
            )
        )

    dominant_agent_type = entries[0].agent_type if entries else None
    return ProjectAgentMixSummary(
        total_sessions=total_sessions,
        compared_agents=len(entries),
        dominant_agent_type=dominant_agent_type,
        entries=entries,
    )


def _build_project_enablement_recommendations(
    enablement: ProjectEnablementSummary,
    repositories: list[ProjectRepositorySummary],
    workflow_summary: ProjectWorkflowSummary,
    friction,
) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    hotspots = {item.friction_type: item for item in workflow_summary.friction_hotspots}

    context_hotspot = _select_hotspot(hotspots, _PROJECT_CONTEXT_FRICTION)
    tooling_hotspot = _select_hotspot(hotspots, _PROJECT_TOOLING_FRICTION)
    permission_hotspot = hotspots.get("permission_denied")

    repos_missing_guidance = [
        repo.repository
        for repo in repositories
        if repo.readiness_checked and not (repo.has_claude_md or repo.has_agents_md)
    ]

    if context_hotspot and repos_missing_guidance:
        recommendations.append(
            Recommendation(
                category="project_context",
                title="Codify project context for agents",
                description=(
                    f"{context_hotspot.friction_type.replace('_', ' ')} is showing up in "
                    f"{context_hotspot.session_count} "
                    f"{_pluralize('session', context_hotspot.session_count)}, "
                    f"and {len(repos_missing_guidance)} linked "
                    f"{_pluralize('repository', len(repos_missing_guidance))} still lack "
                    "CLAUDE.md or AGENTS.md. Capture the preferred commands, file boundaries, "
                    "and handoff conventions so agents stop rediscovering project context."
                ),
                severity="warning",
                evidence={
                    "friction_type": context_hotspot.friction_type,
                    "session_count": context_hotspot.session_count,
                    "repositories_missing_guidance": repos_missing_guidance,
                },
            )
        )

    if tooling_hotspot and tooling_hotspot.total_occurrences >= 2:
        recommendations.append(
            Recommendation(
                category="tooling",
                title="Stabilize recurring tooling failures",
                description=(
                    f"{tooling_hotspot.friction_type.replace('_', ' ')} is recurring across "
                    f"{tooling_hotspot.session_count} "
                    f"{_pluralize('session', tooling_hotspot.session_count)}. "
                    "Audit the commands, MCP servers, or build/test steps used in these workflows, "
                    "then document the happy path and recovery path in the project workspace."
                ),
                severity="warning",
                evidence={
                    "friction_type": tooling_hotspot.friction_type,
                    "session_count": tooling_hotspot.session_count,
                    "total_occurrences": tooling_hotspot.total_occurrences,
                    "linked_fingerprints": tooling_hotspot.linked_fingerprints,
                    "sample_details": tooling_hotspot.sample_details,
                },
            )
        )

    dominant_permission_mode = None
    if enablement.permission_mode_counts:
        dominant_permission_mode = max(
            enablement.permission_mode_counts.items(),
            key=lambda item: item[1],
        )[0]
    if permission_hotspot and permission_hotspot.total_occurrences >= 2:
        recommendations.append(
            Recommendation(
                category="permissions",
                title="Reduce permission friction in common workflows",
                description=(
                    f"Permission-denied friction affected {permission_hotspot.session_count} "
                    f"{_pluralize('session', permission_hotspot.session_count)}"
                    + (
                        f" while `{dominant_permission_mode}` is the dominant permission mode."
                        if dominant_permission_mode
                        else "."
                    )
                    + " Pre-approve safe commands, or document approval boundaries for the "
                    "project's most common workflows."
                ),
                severity="info",
                evidence={
                    "friction_type": "permission_denied",
                    "session_count": permission_hotspot.session_count,
                    "total_occurrences": permission_hotspot.total_occurrences,
                    "dominant_permission_mode": dominant_permission_mode,
                },
            )
        )

    best_fingerprint = _select_best_fingerprint(workflow_summary.fingerprints)
    if (
        best_fingerprint
        and best_fingerprint.session_count >= 2
        and best_fingerprint.success_rate is not None
        and best_fingerprint.success_rate >= 0.75
        and workflow_summary.friction_hotspots
    ):
        recommendations.append(
            Recommendation(
                category="workflow",
                title="Turn the best workflow into a project playbook",
                description=(
                    f"The strongest observed pattern, '{best_fingerprint.label}', succeeds "
                    f"{best_fingerprint.success_rate:.0%} of the time across "
                    f"{best_fingerprint.session_count} sessions. Capture it in repo guidance or "
                    "a project playbook so more work follows the same path."
                ),
                severity="info",
                evidence={
                    "fingerprint_id": best_fingerprint.fingerprint_id,
                    "label": best_fingerprint.label,
                    "session_count": best_fingerprint.session_count,
                    "success_rate": best_fingerprint.success_rate,
                },
            )
        )

    if not recommendations and friction and friction.total_friction_count > 0:
        recommendations.append(
            Recommendation(
                category="workflow",
                title="Review the highest-friction project workflows",
                description=(
                    "This project is showing repeated friction, but the patterns do not yet map "
                    "to a specific enablement recommendation. Review the workflow fingerprints "
                    "and recent sessions, then convert the best recovery path into guidance."
                ),
                severity="info",
                evidence={
                    "friction_rate": friction.friction_rate,
                    "total_friction_count": friction.total_friction_count,
                },
            )
        )

    return recommendations[:3]


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
            primary_language=repo.primary_language,
            language_mix=_language_mix_from_breakdown(
                repo.language_breakdown, repo.primary_language
            ),
            repo_size_kb=repo.repo_size_kb,
            repo_size_bucket=_repo_size_bucket(repo.repo_size_kb),
            has_test_harness=repo.has_test_harness,
            has_ci_pipeline=repo.has_ci_pipeline,
            test_maturity_score=repo.test_maturity_score,
        )
        for repo in repos
    ]


def _build_repository_context_summary(
    repositories: list[ProjectRepositorySummary],
) -> ProjectRepositoryContextSummary:
    context_repositories = [
        repo
        for repo in repositories
        if repo.language_mix
        or repo.repo_size_kb is not None
        or repo.test_maturity_score is not None
        or repo.has_test_harness is not None
        or repo.has_ci_pipeline is not None
    ]
    if not context_repositories:
        return ProjectRepositoryContextSummary()

    language_totals: Counter[str] = Counter()
    size_distribution: Counter[str] = Counter()
    repo_sizes = [
        repo.repo_size_kb for repo in context_repositories if repo.repo_size_kb is not None
    ]
    test_scores = [
        repo.test_maturity_score
        for repo in context_repositories
        if repo.test_maturity_score is not None
    ]

    repos_with_languages = 0
    for repo in context_repositories:
        if repo.language_mix:
            repos_with_languages += 1
        for item in repo.language_mix:
            language_totals[item.language] += item.share_pct
        if repo.repo_size_bucket:
            size_distribution[repo.repo_size_bucket] += 1

    repo_count = len(context_repositories)
    language_mix = (
        [
            LanguageShare(
                language=language,
                share_pct=round(total / repos_with_languages, 3),
            )
            for language, total in language_totals.most_common(5)
        ]
        if repos_with_languages
        else []
    )

    return ProjectRepositoryContextSummary(
        repositories_with_context=repo_count,
        avg_repo_size_kb=round(sum(repo_sizes) / len(repo_sizes), 1) if repo_sizes else None,
        avg_test_maturity_score=(
            round(sum(test_scores) / len(test_scores), 3) if test_scores else None
        ),
        repositories_with_test_harness=sum(
            1 for repo in context_repositories if repo.has_test_harness is True
        ),
        repositories_with_ci_pipeline=sum(
            1 for repo in context_repositories if repo.has_ci_pipeline is True
        ),
        language_mix=language_mix,
        size_distribution=dict(size_distribution),
    )


def _language_mix_from_breakdown(
    breakdown: dict[str, int] | None,
    primary_language: str | None,
) -> list[LanguageShare]:
    if breakdown:
        top_languages = [
            (language, bytes_of_code)
            for language, bytes_of_code in sorted(
                breakdown.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:3]
            if bytes_of_code > 0
        ]
        top_total = sum(bytes_of_code for _, bytes_of_code in top_languages)
        if top_total > 0:
            return [
                LanguageShare(language=language, share_pct=round(bytes_of_code / top_total, 3))
                for language, bytes_of_code in top_languages
            ]
    if primary_language:
        return [LanguageShare(language=primary_language, share_pct=1.0)]
    return []


def _repo_size_bucket(repo_size_kb: int | None) -> str | None:
    if repo_size_kb is None:
        return None
    if repo_size_kb < 5_000:
        return "small"
    if repo_size_kb < 50_000:
        return "medium"
    return "large"


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


def _select_hotspot(
    hotspots: dict[str, ProjectFrictionHotspot],
    allowed_types: set[str],
) -> ProjectFrictionHotspot | None:
    candidates = [
        hotspots[friction_type] for friction_type in allowed_types if friction_type in hotspots
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item.session_count, item.total_occurrences))


def _select_best_fingerprint(
    fingerprints: list[ProjectWorkflowFingerprint],
) -> ProjectWorkflowFingerprint | None:
    candidates = [item for item in fingerprints if item.success_rate is not None]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item.success_rate,
            item.session_count,
            item.share_of_sessions,
        ),
    )


def _pluralize(noun: str, count: int) -> str:
    if count == 1:
        return noun
    if noun.endswith("y") and noun[-2:] not in ("ay", "ey", "oy", "uy"):
        return f"{noun[:-1]}ies"
    return f"{noun}s"


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
    profiles_by_session = {
        row.session_id: row
        for row in (
            db.query(
                SessionWorkflowProfile.session_id,
                SessionWorkflowProfile.fingerprint_id,
                SessionWorkflowProfile.label,
                SessionWorkflowProfile.steps,
            )
            .filter(SessionWorkflowProfile.session_id.in_(session_ids))
            .all()
        )
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
        profile = profiles_by_session.get(session_id)
        steps = list(profile.steps or []) if profile is not None else []
        if not steps:
            steps = infer_workflow_steps(tool_counts, session_id in commit_session_ids)
        if not session_type and not steps:
            continue

        fingerprinted_sessions += 1
        fingerprint_id = profile.fingerprint_id if profile is not None else None
        if not fingerprint_id:
            fingerprint_id = workflow_fingerprint_id(session_type, steps)
        label = profile.label if profile is not None else None
        if not label:
            label = workflow_fingerprint_label(session_type, steps)
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
