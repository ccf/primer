"""Coaching brief service — synthesizes multiple analytics into actionable guidance."""

from datetime import UTC, datetime, timedelta

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
        if profile.model_count <= 1:
            items.append(
                f"You use {profile.model_count} model. "
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
        items.append(
            "Your tool usage is well-diversified. "
            "Look at the Growth page for shared patterns from top performers."
        )
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
