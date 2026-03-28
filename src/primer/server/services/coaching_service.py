"""Coaching brief service — synthesizes multiple analytics into actionable guidance."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy.orm import Session

from primer.common.schemas import CoachingBrief, CoachingSection
from primer.server.services.analytics_service import get_friction_report, get_overview
from primer.server.services.insights_service import (
    get_config_optimization,
    get_personalized_tips,
)
from primer.server.services.maturity_service import get_maturity_analytics


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.0f}%"


def _build_status(overview, profile) -> str:
    parts = [f"{overview.total_sessions} sessions"]
    if overview.success_rate is not None:
        parts.append(f"{_fmt_pct(overview.success_rate)} success rate")
    if profile is not None:
        parts.append(f"Leverage: {profile.leverage_score:.1f}")
    if profile is not None and profile.effectiveness_score is not None:
        parts.append(f"Effectiveness: {profile.effectiveness_score:.1f}")
    return " · ".join(parts)


_FRICTION_FIXES: dict[str, str] = {
    "permission_denied": ("Update your tool's allowed directories or permission settings."),
    "context_limit": (
        "Break tasks into smaller, focused sessions. "
        "Add a CLAUDE.md with project context to reduce prompt size."
    ),
    "timeout": (
        "Investigate slow commands (test suites, builds). "
        "Consider running long tasks in background."
    ),
    "edit_conflict": (
        "Improve your CLAUDE.md with code style conventions so edits match project patterns."
    ),
    "tool_error": ("Check MCP server availability and tool configuration with `primer doctor`."),
    "exec_error": "Review command permissions and environment setup.",
}


def _build_friction_section(friction_data) -> CoachingSection:
    items = []
    # Sort by count descending, take top 3
    sorted_friction = sorted(friction_data, key=lambda f: f.count, reverse=True)[:3]
    for f in sorted_friction:
        fix = _FRICTION_FIXES.get(f.friction_type, "Review session logs for details.")
        items.append(f"**{f.friction_type}** ({f.count} occurrences) — {fix}")
    if not items:
        items.append("No significant friction detected. Keep it up!")
    return CoachingSection(title="What's slowing you down", items=items)


def _build_skills_section(profile, tips) -> CoachingSection:
    items = []
    if profile:
        if profile.model_count == 1:
            items.append(
                "You use a single model. "
                "Try cheaper models for simple tasks — "
                "Haiku is 3-5x cheaper for lookups and quick edits."
            )
        if not profile.uses_agent_teams and profile.orchestration_calls == 0:
            items.append(
                "You haven't used orchestration tools (Task, Agent). "
                "Engineers who delegate to subagents have higher success rates on complex tasks."
            )
        if profile.leverage_breakdown:
            bd = profile.leverage_breakdown
            if bd.cache_efficiency < 0.3:
                items.append(
                    "Your cache hit rate is low. "
                    "Add project-scoped context files (CLAUDE.md) to improve prompt caching."
                )

    # Add tool gap tips
    for tip in tips.tips:
        if tip.category == "tool_gap" and len(items) < 4:
            items.append(tip.description)

    if not items:
        if profile is not None:
            items.append(
                "Your tool usage is well-diversified. "
                "Look at the Growth page for shared patterns from top performers."
            )
        else:
            items.append("Not enough session data yet to assess skill opportunities.")
    return CoachingSection(title="Where you could level up", items=items)


def _build_recommendations(tips, config) -> CoachingSection:
    items = []

    # Prioritize: config suggestions first (actionable), then tips
    for s in config.suggestions[:2]:
        items.append(f"**{s.title}** — {s.description}")

    for tip in tips.tips:
        if tip.category != "tool_gap" and len(items) < 4:
            items.append(f"**{tip.title}** — {tip.description}")

    if not items:
        items.append("No urgent recommendations. You're on track!")
    return CoachingSection(title="Top recommendations", items=items[:4])


def get_coaching_brief(
    db: Session,
    engineer_id: str,
    team_id: str | None = None,
    days: int = 30,
) -> CoachingBrief:
    """Generate a coaching brief for an engineer.

    Synthesizes overview stats, maturity scores, friction data,
    personalized tips, and config optimization into a single
    prioritized coaching response.
    """
    now = datetime.now(tz=UTC)
    start_date = now - timedelta(days=days)

    overview = get_overview(db, team_id, engineer_id, start_date)
    maturity = get_maturity_analytics(db, team_id, engineer_id, start_date)
    friction = get_friction_report(db, team_id, engineer_id, start_date)
    tips = get_personalized_tips(db, team_id, engineer_id, start_date)
    config = get_config_optimization(db, team_id, engineer_id, start_date)

    # Find this engineer's profile in maturity data
    profile = next(
        (p for p in maturity.engineer_profiles if p.engineer_id == engineer_id),
        None,
    )

    return CoachingBrief(
        status_summary=_build_status(overview, profile),
        sections=[
            _build_friction_section(friction),
            _build_skills_section(profile, tips),
            _build_recommendations(tips, config),
        ],
        sessions_analyzed=overview.total_sessions,
        generated_at=now.isoformat(),
    )


def _normalize_hint(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized or None


def _matches_workflow_hint(playbook_like, workflow_hint: str | None) -> bool:
    if not workflow_hint:
        return True
    title = _normalize_hint(getattr(playbook_like, "title", "")) or ""
    session_type = _normalize_hint(getattr(playbook_like, "session_type", None))
    return workflow_hint in title or workflow_hint == session_type


def _context_summary(
    *,
    project_name: str | None,
    workflow_hint: str | None,
    task_hint: str | None,
) -> str | None:
    parts: list[str] = []
    if project_name:
        parts.append(f"Project: {project_name}")
    if workflow_hint:
        parts.append(f"Workflow: {workflow_hint.replace('_', ' ')}")
    if task_hint:
        parts.append(f"Task: {task_hint}")
    if not parts:
        return None
    return " · ".join(parts)


def _append_reason(base: str, reason: str | None) -> str:
    if not reason:
        return base
    return f"{base} Why this helps: {reason}"


def _playbook_reason(playbook) -> str | None:
    parts: list[str] = []
    if getattr(playbook, "success_rate", None) is not None:
        parts.append(f"{playbook.success_rate:.0%} success rate")
    if getattr(playbook, "supporting_session_count", 0):
        parts.append(f"{playbook.supporting_session_count} supporting sessions")
    if getattr(playbook, "supporting_peer_count", 0):
        parts.append(f"{playbook.supporting_peer_count} peers")
    if not parts:
        return None
    return "Backed by " + ", ".join(parts) + "."


def _model_reason(recommendation) -> str | None:
    current_success = getattr(recommendation, "current_success_rate", None)
    recommended_success = getattr(recommendation, "recommended_success_rate", None)
    current_cost = getattr(recommendation, "current_avg_cost", None)
    recommended_cost = getattr(recommendation, "recommended_avg_cost", None)
    supporting_sessions = getattr(recommendation, "supporting_session_count", 0)

    details: list[str] = []
    if current_cost is not None and recommended_cost is not None:
        details.append(f"avg cost shifts from ${current_cost:.2f} to ${recommended_cost:.2f}")
    if current_success is not None and recommended_success is not None:
        details.append(
            f"peer success stays around {recommended_success:.0%}"
            if recommendation.recommendation_type == "downshift"
            else f"peer success rises toward {recommended_success:.0%}"
        )
    if supporting_sessions:
        details.append(f"{supporting_sessions} supporting sessions")
    if not details:
        return None
    return ", ".join(details).capitalize() + "."


def _tool_reason(recommendation) -> str | None:
    details: list[str] = []
    exemplar_count = getattr(recommendation, "supporting_exemplar_count", 0)
    project_matches = getattr(recommendation, "project_context_match_count", 0)
    if exemplar_count:
        details.append(f"{exemplar_count} exemplar session{'s' if exemplar_count != 1 else ''}")
    if project_matches:
        details.append(
            f"{project_matches} matching project context{'s' if project_matches != 1 else ''}"
        )
    if not details:
        return None
    return "Seen in " + " and ".join(details) + "."


def _learning_reason(recommendation) -> str | None:
    exemplars = list(getattr(recommendation, "exemplars", []) or [])
    if not exemplars:
        return None
    return (
        f"Grounded in {len(exemplars)} exemplar session"
        f"{'s' if len(exemplars) != 1 else ''} from similar work."
    )


def _build_starting_pattern_section(
    profile,
    project_workspace,
    workflow_hint: str | None,
    project_name: str | None,
) -> CoachingSection:
    items: list[str] = []

    playbooks = list(getattr(profile, "workflow_playbooks", []) or [])
    matching_playbooks = [
        playbook
        for playbook in playbooks
        if _matches_workflow_hint(playbook, workflow_hint)
        and (
            not project_name
            or not playbook.example_projects
            or project_name in playbook.example_projects
        )
    ]
    fallback_playbooks = [
        playbook for playbook in playbooks if _matches_workflow_hint(playbook, workflow_hint)
    ]
    selected_playbook = (matching_playbooks or fallback_playbooks or playbooks[:1])[:1]
    if selected_playbook:
        playbook = selected_playbook[0]
        tools = ", ".join(playbook.recommended_tools[:3]) if playbook.recommended_tools else None
        summary = playbook.summary.rstrip(".")
        if tools:
            summary = f"{summary}. Start with {tools}."
        items.append(
            _append_reason(f"**{playbook.title}** — {summary}", _playbook_reason(playbook))
        )

    if project_workspace and project_workspace.enablement.recommendations:
        recommendation = project_workspace.enablement.recommendations[0]
        narrative = getattr(recommendation, "narrative", None)
        items.append(
            _append_reason(
                f"**Project guidance** — {recommendation.title}: {recommendation.description}",
                getattr(narrative, "why_this_helps", None),
            )
        )

    if not items:
        items.append(
            "Start with a short discovery pass: inspect the relevant files, run the quickest "
            "verification command you trust, and only then widen scope."
        )

    return CoachingSection(title="How to start this session", items=items[:3])


def _build_session_start_recommendations_section(
    profile,
    workflow_hint: str | None,
    project_name: str | None,
) -> CoachingSection:
    items: list[str] = []

    model_recommendations = list(getattr(profile, "model_recommendations", []) or [])
    matching_models = [
        recommendation
        for recommendation in model_recommendations
        if not workflow_hint
        or not recommendation.workflow_archetype
        or _normalize_hint(recommendation.workflow_archetype) == workflow_hint
    ]
    if matching_models:
        recommendation = matching_models[0]
        items.append(
            _append_reason(
                f"**Model choice** — {recommendation.title}: {recommendation.description}",
                _model_reason(recommendation),
            )
        )

    tool_recommendations = list(getattr(profile, "tool_recommendations", []) or [])
    matching_tools = [
        recommendation
        for recommendation in tool_recommendations
        if not project_name
        or project_name in recommendation.matching_projects
        or recommendation.project_context_match_count > 0
    ]
    if matching_tools or tool_recommendations:
        recommendation = (matching_tools or tool_recommendations)[0]
        items.append(
            _append_reason(
                f"**Tooling** — {recommendation.title}: {recommendation.description}",
                _tool_reason(recommendation),
            )
        )

    learning_paths = list(getattr(profile, "learning_paths", []) or [])
    if learning_paths and learning_paths[0].recommendations:
        recommendation = learning_paths[0].recommendations[0]
        items.append(
            _append_reason(
                f"**Reusable pattern** — {recommendation.title}: {recommendation.description}",
                _learning_reason(recommendation),
            )
        )

    if not items:
        items.append(
            "No strong model or tool recommendation yet. Keep the first pass light and gather "
            "evidence before escalating complexity."
        )

    return CoachingSection(title="What to reach for", items=items[:3])


def _build_watchouts_section(profile, project_workspace) -> CoachingSection:
    items: list[str] = []

    if project_workspace and project_workspace.workflow_summary.friction_hotspots:
        hotspot = project_workspace.workflow_summary.friction_hotspots[0]
        items.append(
            f"**Watch for {hotspot.friction_type}** — it shows up in "
            f"{hotspot.session_count} sessions on this project."
        )

    config_suggestions = list(getattr(profile, "config_suggestions", []) or [])
    if config_suggestions:
        suggestion = config_suggestions[0]
        items.append(f"**Setup check** — {suggestion.title}: {suggestion.description}")

    if project_workspace and project_workspace.enablement.permission_mode_counts:
        default_count = project_workspace.enablement.permission_mode_counts.get("default", 0)
        if default_count > 0:
            items.append(
                "Permission prompts are common on this project. Start with read-safe inspection "
                "before reaching for broader edits or shell commands."
            )

    if not items:
        items.append("No major watch-outs are standing out for this project right now.")

    return CoachingSection(title="What to watch for", items=items[:3])


def get_session_start_brief(
    db: Session,
    engineer_id: str,
    team_id: str | None = None,
    *,
    days: int = 90,
    project_name: str | None = None,
    workflow_hint: str | None = None,
    task_hint: str | None = None,
) -> CoachingBrief:
    from primer.server.services.engineer_profile_service import get_engineer_profile
    from primer.server.services.project_workspace_service import get_project_workspace

    now = datetime.now(tz=UTC)
    start_date = now - timedelta(days=days)
    normalized_workflow_hint = _normalize_hint(workflow_hint)

    profile = get_engineer_profile(
        db,
        engineer_id,
        start_date=start_date,
        end_date=now,
    )
    if profile is None:
        profile = SimpleNamespace(
            overview=SimpleNamespace(total_sessions=0, success_rate=None),
            workflow_playbooks=[],
            model_recommendations=[],
            tool_recommendations=[],
            learning_paths=[],
            config_suggestions=[],
        )

    project_workspace = None
    if project_name:
        project_workspace = get_project_workspace(
            db,
            project_name,
            team_id=team_id,
            engineer_id=None if team_id else engineer_id,
            start_date=start_date,
            end_date=now,
        )

    status_parts = ["Session-start brief"]
    total_sessions = getattr(profile.overview, "total_sessions", 0)
    if total_sessions:
        status_parts.append(f"{total_sessions} sessions in view")
    success_rate = getattr(profile.overview, "success_rate", None)
    if success_rate is not None:
        status_parts.append(f"{_fmt_pct(success_rate)} success rate")

    return CoachingBrief(
        status_summary=" · ".join(status_parts),
        sections=[
            _build_starting_pattern_section(
                profile,
                project_workspace,
                normalized_workflow_hint,
                project_name,
            ),
            _build_session_start_recommendations_section(
                profile,
                normalized_workflow_hint,
                project_name,
            ),
            _build_watchouts_section(profile, project_workspace),
        ],
        sessions_analyzed=total_sessions,
        generated_at=now.isoformat(),
        brief_type="session_start",
        context_summary=_context_summary(
            project_name=project_name,
            workflow_hint=workflow_hint,
            task_hint=task_hint,
        ),
    )
