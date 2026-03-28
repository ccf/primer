from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from primer.common.models import Alert, NarrativeCache, Team
from primer.common.schemas import NextStepPlanAction, NextStepPlanResponse
from primer.server.services.project_workspace_service import get_project_workspace
from primer.server.services.synthesis_service import get_recommendations

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def get_next_step_plan(
    db: Session,
    *,
    team_id: str | None = None,
    project_name: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    days: int = 14,
    limit: int = 5,
) -> NextStepPlanResponse:
    now = datetime.now(tz=UTC)
    period_end = _ensure_utc(end_date) if end_date else now
    period_start = _ensure_utc(start_date) if start_date else period_end - timedelta(days=days)

    actions: list[NextStepPlanAction] = []
    actions.extend(
        _alert_actions(
            db,
            team_id=team_id,
            period_start=period_start,
            period_end=period_end,
        )
    )
    actions.extend(
        _project_actions(
            db,
            team_id=team_id,
            project_name=project_name,
            period_start=period_start,
            period_end=period_end,
        )
    )
    actions.extend(
        _narrative_actions(
            db,
            team_id=team_id,
            period_start=period_start,
            period_end=period_end,
        )
    )
    actions.extend(
        _recommendation_actions(
            db,
            team_id=team_id,
            period_start=period_start,
            period_end=period_end,
        )
    )

    deduped = _dedupe_actions(actions)
    deduped.sort(key=_action_sort_key)
    deduped = deduped[:limit]

    scope_label = _scope_label(db, team_id=team_id, project_name=project_name)
    summary = (
        f"{len(deduped)} next-step action{'s' if len(deduped) != 1 else ''} synthesized from "
        "recent alerts, narratives, and project findings."
        if deduped
        else "No urgent next-step actions are standing out right now."
    )

    return NextStepPlanResponse(
        scope_label=scope_label,
        summary=summary,
        generated_at=now.isoformat(),
        actions=deduped,
    )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _scope_label(db: Session, *, team_id: str | None, project_name: str | None) -> str:
    if project_name:
        return project_name
    if team_id:
        team = db.query(Team.name).filter(Team.id == team_id).first()
        return team[0] if team else "Team"
    return "Organization"


def _alert_actions(
    db: Session,
    *,
    team_id: str | None,
    period_start: datetime,
    period_end: datetime,
) -> list[NextStepPlanAction]:
    query = db.query(Alert).filter(
        Alert.dismissed.is_(False),
        Alert.detected_at >= period_start,
        Alert.detected_at <= period_end,
    )
    if team_id:
        query = query.filter(Alert.team_id == team_id)

    rows = query.order_by(Alert.detected_at.desc()).limit(3).all()
    actions: list[NextStepPlanAction] = []
    for alert in rows:
        actions.append(
            NextStepPlanAction(
                action_id=f"alert:{alert.id}",
                title=alert.title,
                description=alert.message,
                priority="high" if alert.severity in {"warning", "critical"} else "medium",
                source_type="alert",
                source_title=alert.alert_type,
                category="alert_response",
                severity=alert.severity,
                evidence={
                    "metric_name": alert.metric_name,
                    "expected_value": alert.expected_value,
                    "actual_value": alert.actual_value,
                },
            )
        )
    return actions


def _project_actions(
    db: Session,
    *,
    team_id: str | None,
    project_name: str | None,
    period_start: datetime,
    period_end: datetime,
) -> list[NextStepPlanAction]:
    if not project_name:
        return []
    workspace = get_project_workspace(
        db,
        project_name,
        team_id=team_id,
        start_date=period_start,
        end_date=period_end,
    )
    if workspace is None:
        return []

    actions: list[NextStepPlanAction] = []
    for recommendation in workspace.enablement.recommendations[:3]:
        actions.append(
            NextStepPlanAction(
                action_id=f"project:{project_name}:{recommendation.title}",
                title=recommendation.title,
                description=recommendation.description,
                priority="high" if recommendation.severity == "warning" else "medium",
                source_type="project_finding",
                source_title="project enablement",
                category=recommendation.category,
                severity=recommendation.severity,
                project_name=project_name,
                evidence=recommendation.evidence or {},
                narrative=recommendation.narrative,
            )
        )
    return actions


def _narrative_actions(
    db: Session,
    *,
    team_id: str | None,
    period_start: datetime,
    period_end: datetime,
) -> list[NextStepPlanAction]:
    from primer.server.services.narrative_service import _date_range_key

    scope = "team" if team_id else "org"
    scope_id = team_id if team_id else None
    cached = (
        db.query(NarrativeCache)
        .filter(
            NarrativeCache.scope == scope,
            NarrativeCache.scope_id == scope_id if scope_id else NarrativeCache.scope_id.is_(None),
            NarrativeCache.date_range_key == _date_range_key(period_start, period_end),
            NarrativeCache.expires_at > datetime.now(UTC),
        )
        .first()
    )
    if cached is None:
        return []

    actions: list[NextStepPlanAction] = []
    for section in cached.sections or []:
        if not isinstance(section, dict):
            continue
        title = section.get("title")
        content = section.get("content")
        if not isinstance(title, str) or not isinstance(content, str):
            continue
        if "recommend" not in title.lower():
            continue
        actions.append(
            NextStepPlanAction(
                action_id=f"narrative:{title}",
                title=title,
                description=content,
                priority="medium",
                source_type="narrative",
                source_title=scope,
                category="narrative",
                severity="info",
                evidence={},
            )
        )
    return actions[:2]


def _recommendation_actions(
    db: Session,
    *,
    team_id: str | None,
    period_start: datetime,
    period_end: datetime,
) -> list[NextStepPlanAction]:
    recommendations = get_recommendations(
        db,
        team_id=team_id,
        start_date=period_start,
        end_date=period_end,
    )
    actions: list[NextStepPlanAction] = []
    for recommendation in recommendations[:3]:
        actions.append(
            NextStepPlanAction(
                action_id=f"recommendation:{recommendation.category}:{recommendation.title}",
                title=recommendation.title,
                description=recommendation.description,
                priority="high" if recommendation.severity == "warning" else "medium",
                source_type="recommendation",
                source_title=recommendation.category,
                category=recommendation.category,
                severity=recommendation.severity,
                evidence=recommendation.evidence or {},
                narrative=recommendation.narrative,
            )
        )
    return actions


def _dedupe_actions(actions: list[NextStepPlanAction]) -> list[NextStepPlanAction]:
    seen: set[tuple[str, str]] = set()
    deduped: list[NextStepPlanAction] = []
    for action in actions:
        key = (action.title.strip().lower(), action.source_type)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(action)
    return deduped


def _action_sort_key(action: NextStepPlanAction) -> tuple[int, int, str]:
    priority_score = {"high": 2, "medium": 1, "low": 0}
    source_score = {"alert": 3, "project_finding": 2, "recommendation": 1, "narrative": 0}
    return (
        -priority_score.get(action.priority, 0),
        -source_score.get(action.source_type, 0),
        action.title,
    )
