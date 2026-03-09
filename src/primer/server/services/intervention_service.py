from datetime import UTC, datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from primer.common.models import Engineer, Intervention, Team
from primer.common.schemas import (
    InterventionCreate,
    InterventionEngineerSummary,
    InterventionMetricsSnapshot,
    InterventionResponse,
    InterventionUpdate,
)
from primer.server.services.analytics_service import (
    get_friction_report,
    get_overview,
    get_productivity_metrics,
)
from primer.server.services.quality_service import get_quality_metrics

DEFAULT_MEASUREMENT_WINDOW = timedelta(days=30)


def list_interventions(
    db: Session,
    *,
    team_id: str | None = None,
    engineer_id: str | None = None,
    owner_engineer_id: str | None = None,
    project_name: str | None = None,
    status: str | None = None,
) -> list[InterventionResponse]:
    query = db.query(Intervention)
    if team_id:
        query = query.filter(Intervention.team_id == team_id)
    if engineer_id:
        query = query.filter(Intervention.engineer_id == engineer_id)
    if owner_engineer_id:
        query = query.filter(Intervention.owner_engineer_id == owner_engineer_id)
    if project_name:
        query = query.filter(Intervention.project_name == project_name)
    if status:
        query = query.filter(Intervention.status == status)
    interventions = query.order_by(
        Intervention.updated_at.desc(),
        Intervention.created_at.desc(),
    ).all()
    return _build_responses(db, interventions)


def create_intervention(
    db: Session,
    payload: InterventionCreate,
    *,
    created_by_engineer_id: str | None = None,
) -> InterventionResponse:
    baseline_start, baseline_end = _resolve_measurement_window(
        payload.baseline_start_at,
        payload.baseline_end_at,
    )
    baseline_metrics = capture_metrics_snapshot(
        db,
        team_id=payload.team_id,
        engineer_id=payload.engineer_id,
        project_name=payload.project_name,
        window_start=baseline_start,
        window_end=baseline_end,
    )

    intervention = Intervention(
        team_id=payload.team_id,
        engineer_id=payload.engineer_id,
        owner_engineer_id=payload.owner_engineer_id,
        created_by_engineer_id=created_by_engineer_id,
        project_name=payload.project_name,
        category=payload.category,
        severity=payload.severity,
        status=payload.status,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        source_type=payload.source_type,
        source_title=payload.source_title,
        evidence=payload.evidence,
        baseline_start_at=baseline_start,
        baseline_end_at=baseline_end,
        baseline_metrics=baseline_metrics.model_dump(mode="json"),
        completed_at=datetime.now(UTC) if payload.status == "completed" else None,
    )
    db.add(intervention)
    db.flush()
    return _build_responses(db, [intervention], include_current_metrics=True)[0]


def get_intervention(db: Session, intervention_id: str) -> Intervention | None:
    return db.query(Intervention).filter(Intervention.id == intervention_id).first()


def update_intervention(
    db: Session,
    intervention: Intervention,
    payload: InterventionUpdate,
) -> InterventionResponse:
    before_scope = (
        intervention.team_id,
        intervention.engineer_id,
        intervention.project_name,
    )
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(intervention, field, value)

    if payload.status is not None:
        intervention.completed_at = datetime.now(UTC) if payload.status == "completed" else None

    after_scope = (
        intervention.team_id,
        intervention.engineer_id,
        intervention.project_name,
    )
    if before_scope != after_scope:
        baseline_start, baseline_end = _resolve_measurement_window(
            intervention.baseline_start_at,
            intervention.baseline_end_at,
        )
        intervention.baseline_start_at = baseline_start
        intervention.baseline_end_at = baseline_end
        intervention.baseline_metrics = capture_metrics_snapshot(
            db,
            team_id=intervention.team_id,
            engineer_id=intervention.engineer_id,
            project_name=intervention.project_name,
            window_start=baseline_start,
            window_end=baseline_end,
        ).model_dump(mode="json")

    db.flush()
    return _build_responses(db, [intervention], include_current_metrics=True)[0]


def capture_metrics_snapshot(
    db: Session,
    *,
    team_id: str | None,
    engineer_id: str | None,
    project_name: str | None,
    window_start: datetime,
    window_end: datetime,
) -> InterventionMetricsSnapshot:
    overview = get_overview(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=window_start,
        end_date=window_end,
        project_name=project_name,
    )
    productivity = get_productivity_metrics(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=window_start,
        end_date=window_end,
        project_name=project_name,
    )
    friction = get_friction_report(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=window_start,
        end_date=window_end,
        project_name=project_name,
    )
    quality = get_quality_metrics(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=window_start,
        end_date=window_end,
        project_name=project_name,
    )
    total_prs = quality.overview.total_prs
    findings_per_pr = quality.findings_overview.total_findings / total_prs if total_prs else None
    return InterventionMetricsSnapshot(
        window_start=window_start,
        window_end=window_end,
        total_sessions=overview.total_sessions,
        success_rate=overview.success_rate,
        avg_cost_per_session=productivity.avg_cost_per_session,
        cost_per_successful_outcome=productivity.cost_per_successful_outcome,
        friction_events=sum(item.count for item in friction),
        total_prs=total_prs,
        findings_per_pr=findings_per_pr,
    )


def intervention_visible_to_engineer(intervention: Intervention, engineer_id: str) -> bool:
    return intervention.engineer_id == engineer_id or intervention.owner_engineer_id == engineer_id


def intervention_visible_to_team(db: Session, intervention: Intervention, team_id: str) -> bool:
    if intervention.team_id == team_id:
        return True
    related_engineer_ids = [intervention.engineer_id, intervention.owner_engineer_id]
    if not any(related_engineer_ids):
        return False
    return (
        db.query(Engineer.id)
        .filter(
            Engineer.team_id == team_id,
            Engineer.id.in_([engineer_id for engineer_id in related_engineer_ids if engineer_id]),
        )
        .first()
        is not None
    )


def list_interventions_for_engineer(db: Session, engineer_id: str, status: str | None = None):
    query = db.query(Intervention).filter(
        or_(
            Intervention.engineer_id == engineer_id,
            Intervention.owner_engineer_id == engineer_id,
        )
    )
    if status:
        query = query.filter(Intervention.status == status)
    interventions = query.order_by(
        Intervention.updated_at.desc(),
        Intervention.created_at.desc(),
    ).all()
    return _build_responses(db, interventions)


def _build_responses(
    db: Session,
    interventions: list[Intervention],
    *,
    include_current_metrics: bool = False,
) -> list[InterventionResponse]:
    if not interventions:
        return []

    team_ids = {intervention.team_id for intervention in interventions if intervention.team_id}
    engineer_ids = {
        engineer_id
        for intervention in interventions
        for engineer_id in (
            intervention.engineer_id,
            intervention.owner_engineer_id,
        )
        if engineer_id
    }
    team_names = {team.id: team.name for team in db.query(Team).filter(Team.id.in_(team_ids)).all()}
    engineer_map = {
        engineer.id: engineer
        for engineer in db.query(Engineer).filter(Engineer.id.in_(engineer_ids)).all()
    }

    responses: list[InterventionResponse] = []
    now = datetime.now(UTC)
    for intervention in interventions:
        baseline_metrics = (
            InterventionMetricsSnapshot.model_validate(intervention.baseline_metrics)
            if intervention.baseline_metrics
            else None
        )
        current_metrics = None
        if (
            include_current_metrics
            and intervention.baseline_start_at
            and intervention.baseline_end_at
        ):
            current_start, current_end = _current_measurement_window(
                intervention.baseline_start_at,
                intervention.baseline_end_at,
                now=now,
            )
            current_metrics = capture_metrics_snapshot(
                db,
                team_id=intervention.team_id,
                engineer_id=intervention.engineer_id,
                project_name=intervention.project_name,
                window_start=current_start,
                window_end=current_end,
            )
        responses.append(
            InterventionResponse(
                id=intervention.id,
                team_id=intervention.team_id,
                team_name=team_names.get(intervention.team_id) if intervention.team_id else None,
                engineer_id=intervention.engineer_id,
                engineer=_engineer_summary(engineer_map.get(intervention.engineer_id)),
                owner_engineer_id=intervention.owner_engineer_id,
                owner_engineer=_engineer_summary(engineer_map.get(intervention.owner_engineer_id)),
                created_by_engineer_id=intervention.created_by_engineer_id,
                project_name=intervention.project_name,
                category=intervention.category,
                severity=intervention.severity,
                status=intervention.status,
                title=intervention.title,
                description=intervention.description,
                due_date=intervention.due_date,
                completed_at=intervention.completed_at,
                source_type=intervention.source_type,
                source_title=intervention.source_title,
                evidence=intervention.evidence,
                baseline_start_at=intervention.baseline_start_at,
                baseline_end_at=intervention.baseline_end_at,
                baseline_metrics=baseline_metrics,
                current_metrics=current_metrics,
                created_at=intervention.created_at,
                updated_at=intervention.updated_at,
            )
        )
    return responses


def _resolve_measurement_window(
    baseline_start_at: datetime | None,
    baseline_end_at: datetime | None,
) -> tuple[datetime, datetime]:
    end_at = _ensure_utc(baseline_end_at) if baseline_end_at else datetime.now(UTC)
    if baseline_start_at:
        start_at = _ensure_utc(baseline_start_at)
    else:
        start_at = end_at - DEFAULT_MEASUREMENT_WINDOW
    if start_at > end_at:
        start_at, end_at = end_at - DEFAULT_MEASUREMENT_WINDOW, end_at
    return start_at, end_at


def _current_measurement_window(
    baseline_start_at: datetime,
    baseline_end_at: datetime,
    *,
    now: datetime,
) -> tuple[datetime, datetime]:
    baseline_start = _ensure_utc(baseline_start_at)
    baseline_end = _ensure_utc(baseline_end_at)
    window = baseline_end - baseline_start
    if window <= timedelta(0):
        window = DEFAULT_MEASUREMENT_WINDOW
    return now - window, now


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _engineer_summary(engineer: Engineer | None) -> InterventionEngineerSummary | None:
    if engineer is None:
        return None
    return InterventionEngineerSummary(id=engineer.id, name=engineer.name, email=engineer.email)
