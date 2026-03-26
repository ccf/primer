from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from primer.common.schemas import PersonalRecap, PersonalRecapsResponse
from primer.server.services.engineer_profile_service import get_engineer_profile

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def get_personal_recaps(
    db: Session,
    engineer_id: str,
) -> PersonalRecapsResponse:
    now = datetime.now(tz=UTC)
    daily_start = now - timedelta(days=1)
    weekly_start = now - timedelta(days=7)

    daily_profile = get_engineer_profile(
        db,
        engineer_id,
        start_date=daily_start,
        end_date=now,
    )
    weekly_profile = get_engineer_profile(
        db,
        engineer_id,
        start_date=weekly_start,
        end_date=now,
    )

    return PersonalRecapsResponse(
        daily=_build_recap("daily", daily_profile),
        weekly=_build_recap("weekly", weekly_profile),
        generated_at=now.isoformat(),
    )


def _build_recap(period: str, profile) -> PersonalRecap:
    period_label = "today" if period == "daily" else "this week"
    if profile is None or profile.overview.total_sessions == 0:
        return PersonalRecap(
            period=period,  # type: ignore[arg-type]
            headline=f"No captured sessions {period_label}",
            summary=(
                f"Primer has not captured enough activity {period_label} to build a recap yet."
            ),
            sessions_analyzed=0,
            wins=[],
            watchouts=[],
            next_steps=["Keep syncing sessions so Primer can build the next recap."],
        )

    overview = profile.overview
    impact = profile.impact_review
    success_rate = overview.success_rate
    top_workflow = None
    if impact and impact.top_workflows:
        top_workflow = _format_workflow_label(impact.top_workflows[0].archetype)

    if period == "daily":
        if overview.total_sessions == 1:
            headline = "You had one meaningful AI session today"
        elif success_rate is not None and success_rate >= 0.75:
            headline = f"You kept momentum across {overview.total_sessions} sessions today"
        else:
            headline = f"You logged {overview.total_sessions} sessions today"
    else:
        if impact and impact.trajectory_signal == "improving":
            headline = "Your weekly momentum is improving"
        elif success_rate is not None and success_rate >= 0.75:
            headline = "You had a strong week of AI-assisted delivery"
        else:
            headline = f"You logged {overview.total_sessions} sessions this week"

    summary_parts = [
        f"{overview.total_sessions} session{'s' if overview.total_sessions != 1 else ''}"
    ]
    if success_rate is not None:
        summary_parts.append(f"{round(success_rate * 100)}% success")
    if overview.estimated_cost is not None:
        summary_parts.append(f"${overview.estimated_cost:.2f} estimated spend")
    if top_workflow:
        summary_parts.append(f"top workflow: {top_workflow}")
    summary = " · ".join(summary_parts)

    wins = list(getattr(impact, "strengths", [])[:2]) if impact else []
    watchouts = _build_watchouts(profile, impact)[:2]
    next_steps = _build_next_steps(profile, impact)[:3]

    return PersonalRecap(
        period=period,  # type: ignore[arg-type]
        headline=headline,
        summary=summary,
        sessions_analyzed=overview.total_sessions,
        success_rate=success_rate,
        estimated_cost=overview.estimated_cost,
        top_workflow=top_workflow,
        wins=wins,
        watchouts=watchouts,
        next_steps=next_steps,
    )


def _build_watchouts(profile, impact) -> list[str]:
    watchouts: list[str] = []
    friction = sorted(profile.friction, key=lambda row: row.count, reverse=True)
    for row in friction[:2]:
        if row.count > 0:
            watchouts.append(
                f"{row.friction_type} showed up {row.count} time{'s' if row.count != 1 else ''}."
            )
    if not watchouts and impact:
        watchouts.extend(list(impact.focus_areas[:2]))
    if not watchouts:
        watchouts.append("No major recurring drag signals stood out in this window.")
    return watchouts


def _build_next_steps(profile, impact) -> list[str]:
    next_steps: list[str] = []
    if impact and impact.next_step_title and impact.next_step_description:
        next_steps.append(f"{impact.next_step_title} — {impact.next_step_description}")
    if not next_steps and profile.tool_recommendations:
        recommendation = profile.tool_recommendations[0]
        next_steps.append(f"{recommendation.title} — {recommendation.description}")
    if not next_steps and profile.model_recommendations:
        recommendation = profile.model_recommendations[0]
        next_steps.append(f"{recommendation.title} — {recommendation.description}")
    if not next_steps and profile.workflow_playbooks:
        playbook = profile.workflow_playbooks[0]
        next_steps.append(f"{playbook.title} — {playbook.summary}")
    if not next_steps:
        next_steps.append("Keep building session history to sharpen the next recommendation.")
    return next_steps


def _format_workflow_label(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace("_", " ").replace("-", " ").title()
