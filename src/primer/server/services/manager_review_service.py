from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from primer.common.schemas import ManagerReviewPack, ManagerReviewSection
from primer.server.services.analytics_service import (
    get_cost_analytics,
    get_friction_report,
    get_overview,
    get_productivity_metrics,
)
from primer.server.services.insights_service import get_skill_inventory
from primer.server.services.quality_service import get_quality_metrics
from primer.server.services.synthesis_service import get_recommendations

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def get_weekly_manager_review_pack(
    db: Session,
    *,
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    days: int = 7,
) -> ManagerReviewPack:
    now = datetime.now(tz=UTC)
    period_end = _ensure_utc(end_date) if end_date else now
    period_start = _ensure_utc(start_date) if start_date else period_end - timedelta(days=days)
    previous_start = period_start - (period_end - period_start)
    previous_end = period_start

    current_overview = get_overview(
        db,
        team_id=team_id,
        start_date=period_start,
        end_date=period_end,
    )
    previous_overview = get_overview(
        db,
        team_id=team_id,
        start_date=previous_start,
        end_date=previous_end,
    )
    productivity = get_productivity_metrics(
        db,
        team_id=team_id,
        start_date=period_start,
        end_date=period_end,
    )
    previous_productivity = get_productivity_metrics(
        db,
        team_id=team_id,
        start_date=previous_start,
        end_date=previous_end,
    )
    quality = get_quality_metrics(
        db,
        team_id=team_id,
        start_date=period_start,
        end_date=period_end,
    )
    previous_quality = get_quality_metrics(
        db,
        team_id=team_id,
        start_date=previous_start,
        end_date=previous_end,
    )
    friction = get_friction_report(
        db,
        team_id=team_id,
        start_date=period_start,
        end_date=period_end,
    )
    previous_friction = get_friction_report(
        db,
        team_id=team_id,
        start_date=previous_start,
        end_date=previous_end,
    )
    costs = get_cost_analytics(
        db,
        team_id=team_id,
        start_date=period_start,
        end_date=period_end,
    )
    skills = get_skill_inventory(
        db,
        team_id=team_id,
        start_date=period_start,
        end_date=period_end,
    )
    recommendations = get_recommendations(
        db,
        team_id=team_id,
        start_date=period_start,
        end_date=period_end,
    )

    scope = "team" if team_id else "org"
    scope_label = _resolve_scope_label(db, team_id)
    headline = _build_headline(scope_label, current_overview, previous_overview)
    sections = [
        _build_quality_section(quality, previous_quality),
        _build_friction_section(friction, previous_friction),
        _build_growth_section(skills),
        _build_cost_section(costs, productivity, previous_productivity),
    ]
    recommended_actions = [
        f"{recommendation.title} — {recommendation.description}"
        for recommendation in recommendations[:3]
    ]
    if not recommended_actions:
        recommended_actions = ["No urgent action is standing out this week."]

    return ManagerReviewPack(
        scope=scope,  # type: ignore[arg-type]
        scope_label=scope_label,
        period_start=period_start.date().isoformat(),
        period_end=period_end.date().isoformat(),
        sessions_analyzed=current_overview.total_sessions,
        headline=headline,
        sections=sections,
        recommended_actions=recommended_actions,
        generated_at=now.isoformat(),
    )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _resolve_scope_label(db: Session, team_id: str | None) -> str:
    if not team_id:
        return "Organization"
    from primer.common.models import Team

    team = db.query(Team.name).filter(Team.id == team_id).first()
    return team[0] if team else "Team"


def _build_headline(scope_label: str, current_overview, previous_overview) -> str:
    session_delta = current_overview.total_sessions - previous_overview.total_sessions
    success_rate = current_overview.success_rate
    parts = [f"{scope_label} logged {current_overview.total_sessions} sessions"]
    if success_rate is not None:
        parts.append(f"{round(success_rate * 100)}% succeeded")
    if session_delta > 0:
        parts.append(f"{session_delta} more than the prior week")
    elif session_delta < 0:
        parts.append(f"{abs(session_delta)} fewer than the prior week")
    return " · ".join(parts)


def _build_quality_section(current, previous) -> ManagerReviewSection:
    overview = current.overview
    previous_overview = previous.overview
    bullets: list[str] = [
        f"{overview.total_prs} PRs tracked this week.",
        f"Merge rate: {_format_pct(overview.pr_merge_rate)}"
        + _delta_text(overview.pr_merge_rate, previous_overview.pr_merge_rate),
    ]
    if current.findings_overview:
        bullets.append(f"Findings fix rate: {_format_pct(current.findings_overview.fix_rate)}.")
    summary = (
        f"Review and merge quality centered on {overview.total_prs} PRs with "
        f"{_format_pct(overview.pr_merge_rate)} merge rate."
    )
    return ManagerReviewSection(title="Quality", summary=summary, bullets=bullets)


def _build_friction_section(current, previous) -> ManagerReviewSection:
    current_total = sum(item.count for item in current)
    previous_total = sum(item.count for item in previous)
    top = current[0] if current else None
    bullets: list[str] = []
    if top:
        bullets.append(f"Top drag: {top.friction_type} ({top.count} occurrences).")
    if len(current) > 1:
        second = current[1]
        bullets.append(f"Second drag: {second.friction_type} ({second.count} occurrences).")
    if not bullets:
        bullets.append("No meaningful friction spikes were captured this week.")
    summary = (
        f"{current_total} total friction events"
        + _delta_text(current_total, previous_total, value_formatter=str)
        + "."
    )
    return ManagerReviewSection(title="Friction", summary=summary, bullets=bullets)


def _build_growth_section(skills) -> ManagerReviewSection:
    bullets: list[str] = []
    for gap in skills.team_skill_gaps[:3]:
        bullets.append(
            f"{gap.skill}: {gap.coverage_pct:.1f}% coverage "
            f"({gap.engineers_with_skill}/{gap.total_engineers} engineers)."
        )
    if not bullets:
        bullets.append("No major team skill gaps stood out in this window.")
    summary = (
        f"{skills.total_engineers} engineers contributed to the sampled growth signal with "
        f"{len(skills.team_skill_gaps)} notable gaps."
    )
    return ManagerReviewSection(title="Growth", summary=summary, bullets=bullets)


def _build_cost_section(costs, current_productivity, previous_productivity) -> ManagerReviewSection:
    top_workflow = costs.workflow_breakdown[0] if costs.workflow_breakdown else None
    bullets: list[str] = [
        f"Total spend: ${costs.total_estimated_cost:.2f}.",
        "Cost per successful outcome: "
        f"{_format_cost(current_productivity.cost_per_successful_outcome)}"
        + _delta_text(
            current_productivity.cost_per_successful_outcome,
            previous_productivity.cost_per_successful_outcome,
            value_formatter=_format_cost,
        ),
    ]
    if top_workflow:
        bullets.append(
            f"Most expensive workflow slice: {top_workflow.label} "
            f"at ${top_workflow.total_estimated_cost:.2f}."
        )
    summary = (
        f"Weekly spend landed at ${costs.total_estimated_cost:.2f} with "
        f"{_format_cost(current_productivity.cost_per_successful_outcome)} cost per success."
    )
    return ManagerReviewSection(title="Cost", summary=summary, bullets=bullets)


def _format_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{round(value * 100)}%"


def _format_cost(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"${value:.2f}"


def _delta_text(current, previous, value_formatter=None) -> str:
    if current is None or previous is None:
        return ""
    delta = current - previous
    if abs(delta) < 1e-9:
        return " (flat vs prior week)"
    formatter = value_formatter or (lambda value: f"{value:.2f}")
    direction = "up" if delta > 0 else "down"
    return f" ({direction} {formatter(abs(delta))} vs prior week)"
