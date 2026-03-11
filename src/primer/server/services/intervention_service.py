from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from primer.common.models import Engineer, Intervention, Team
from primer.common.models import Session as SessionModel
from primer.common.schemas import (
    InterventionCreate,
    InterventionEffectivenessGroup,
    InterventionEffectivenessResponse,
    InterventionEffectivenessSummary,
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
SUCCESS_RATE_EPSILON = 0.01
DECIMAL_DELTA_EPSILON = 0.01


@dataclass
class _EffectivenessRollup:
    key: str
    label: str
    completed_interventions: int = 0
    measured_interventions: int = 0
    improved_interventions: int = 0
    completion_days: list[float] = field(default_factory=list)
    success_rate_deltas: list[float] = field(default_factory=list)
    friction_deltas: list[float] = field(default_factory=list)
    findings_per_pr_deltas: list[float] = field(default_factory=list)
    avg_cost_per_session_deltas: list[float] = field(default_factory=list)

    def add(
        self,
        *,
        completion_days: float | None,
        success_rate_delta: float | None,
        friction_delta: float | None,
        findings_per_pr_delta: float | None,
        avg_cost_per_session_delta: float | None,
        improved: bool,
        measured: bool,
    ) -> None:
        self.completed_interventions += 1
        if completion_days is not None:
            self.completion_days.append(completion_days)
        if measured:
            self.measured_interventions += 1
            if improved:
                self.improved_interventions += 1
        if success_rate_delta is not None:
            self.success_rate_deltas.append(success_rate_delta)
        if friction_delta is not None:
            self.friction_deltas.append(friction_delta)
        if findings_per_pr_delta is not None:
            self.findings_per_pr_deltas.append(findings_per_pr_delta)
        if avg_cost_per_session_delta is not None:
            self.avg_cost_per_session_deltas.append(avg_cost_per_session_delta)


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
    for update_field, value in updates.items():
        setattr(intervention, update_field, value)

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


def list_interventions_for_team(
    db: Session,
    team_id: str,
    *,
    engineer_id: str | None = None,
    project_name: str | None = None,
    status: str | None = None,
) -> list[InterventionResponse]:
    interventions = _query_interventions_visible_to_team(
        db,
        team_id,
        engineer_id=engineer_id,
        project_name=project_name,
        status=status,
    ).all()
    return _build_responses(db, interventions)


def get_intervention_effectiveness_report(
    db: Session,
    *,
    team_id: str | None = None,
    engineer_id: str | None = None,
    owner_engineer_id: str | None = None,
    project_name: str | None = None,
) -> InterventionEffectivenessResponse:
    interventions = _query_interventions(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        owner_engineer_id=owner_engineer_id,
        project_name=project_name,
    ).all()
    return _build_effectiveness_report(db, interventions)


def get_intervention_effectiveness_report_for_engineer(
    db: Session,
    engineer_id: str,
    *,
    project_name: str | None = None,
) -> InterventionEffectivenessResponse:
    query = db.query(Intervention).filter(
        or_(
            Intervention.engineer_id == engineer_id,
            Intervention.owner_engineer_id == engineer_id,
        )
    )
    if project_name:
        query = query.filter(Intervention.project_name == project_name)
    interventions = query.order_by(
        Intervention.updated_at.desc(),
        Intervention.created_at.desc(),
    ).all()
    return _build_effectiveness_report(db, interventions)


def get_intervention_effectiveness_report_for_team(
    db: Session,
    team_id: str,
    *,
    engineer_id: str | None = None,
    project_name: str | None = None,
) -> InterventionEffectivenessResponse:
    interventions = _query_interventions_visible_to_team(
        db,
        team_id,
        engineer_id=engineer_id,
        project_name=project_name,
    ).all()
    return _build_effectiveness_report(db, interventions)


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


def _query_interventions(
    db: Session,
    *,
    team_id: str | None = None,
    engineer_id: str | None = None,
    owner_engineer_id: str | None = None,
    project_name: str | None = None,
    status: str | None = None,
):
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
    return query.order_by(
        Intervention.updated_at.desc(),
        Intervention.created_at.desc(),
    )


def _query_interventions_visible_to_team(
    db: Session,
    team_id: str,
    *,
    engineer_id: str | None = None,
    project_name: str | None = None,
    status: str | None = None,
):
    team_engineers = select(Engineer.id).where(Engineer.team_id == team_id)
    query = db.query(Intervention).filter(
        or_(
            Intervention.team_id == team_id,
            Intervention.engineer_id.in_(team_engineers),
            Intervention.owner_engineer_id.in_(team_engineers),
        )
    )
    if engineer_id:
        query = query.filter(Intervention.engineer_id == engineer_id)
    if project_name:
        query = query.filter(Intervention.project_name == project_name)
    if status:
        query = query.filter(Intervention.status == status)
    return query.order_by(
        Intervention.updated_at.desc(),
        Intervention.created_at.desc(),
    )


def _build_effectiveness_report(
    db: Session,
    interventions: list[Intervention],
) -> InterventionEffectivenessResponse:
    completed = [
        intervention for intervention in interventions if intervention.status == "completed"
    ]
    if not completed:
        empty_summary = InterventionEffectivenessSummary(
            total_interventions=len(interventions),
            completed_interventions=0,
            measured_interventions=0,
            improved_interventions=0,
        )
        return InterventionEffectivenessResponse(
            summary=empty_summary,
            by_team=[],
            by_project=[],
            by_engineer_cohort=[],
        )

    team_ids = {intervention.team_id for intervention in completed if intervention.team_id}
    engineer_ids = {
        engineer_id
        for intervention in completed
        for engineer_id in (
            intervention.engineer_id,
            intervention.owner_engineer_id,
        )
        if engineer_id
    }
    team_map = {team.id: team for team in db.query(Team).filter(Team.id.in_(team_ids)).all()}
    engineer_map = {
        engineer.id: engineer
        for engineer in db.query(Engineer).filter(Engineer.id.in_(engineer_ids)).all()
    }
    first_session_rows = (
        db.query(SessionModel.engineer_id, func.min(SessionModel.started_at))
        .filter(SessionModel.engineer_id.in_(engineer_ids))
        .group_by(SessionModel.engineer_id)
        .all()
    )
    first_session_by_engineer = {
        engineer_id: _ensure_utc(first_started_at)
        for engineer_id, first_started_at in first_session_rows
        if engineer_id and first_started_at
    }

    now = datetime.now(UTC)
    summary_rollup = _EffectivenessRollup(key="summary", label="Summary")
    team_rollups: dict[str, _EffectivenessRollup] = {}
    project_rollups: dict[str, _EffectivenessRollup] = {}
    cohort_rollups: dict[str, _EffectivenessRollup] = {}

    for intervention in completed:
        baseline_metrics = (
            InterventionMetricsSnapshot.model_validate(intervention.baseline_metrics)
            if intervention.baseline_metrics
            else None
        )
        current_metrics = None
        if intervention.baseline_start_at and intervention.baseline_end_at:
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

        measured = baseline_metrics is not None and current_metrics is not None
        success_rate_delta = _higher_is_better_delta(
            baseline_metrics.success_rate if baseline_metrics else None,
            current_metrics.success_rate if current_metrics else None,
        )
        friction_delta = _lower_is_better_delta(
            baseline_metrics.friction_events if baseline_metrics else None,
            current_metrics.friction_events if current_metrics else None,
        )
        findings_per_pr_delta = _lower_is_better_delta(
            baseline_metrics.findings_per_pr if baseline_metrics else None,
            current_metrics.findings_per_pr if current_metrics else None,
        )
        avg_cost_per_session_delta = _lower_is_better_delta(
            baseline_metrics.avg_cost_per_session if baseline_metrics else None,
            current_metrics.avg_cost_per_session if current_metrics else None,
        )
        improved = _is_improved(
            success_rate_delta=success_rate_delta,
            friction_delta=friction_delta,
            findings_per_pr_delta=findings_per_pr_delta,
            avg_cost_per_session_delta=avg_cost_per_session_delta,
        )
        completion_days = _completion_days(intervention)
        team_key, team_label = _team_group(intervention, engineer_map, team_map)
        project_key, project_label = _project_group(intervention)
        cohort_key, cohort_label = _cohort_group(
            intervention.engineer_id,
            first_session_by_engineer,
            now,
        )

        rollup_kwargs = {
            "completion_days": completion_days,
            "success_rate_delta": success_rate_delta,
            "friction_delta": friction_delta,
            "findings_per_pr_delta": findings_per_pr_delta,
            "avg_cost_per_session_delta": avg_cost_per_session_delta,
            "improved": improved,
            "measured": measured,
        }
        summary_rollup.add(**rollup_kwargs)
        team_rollups.setdefault(team_key, _EffectivenessRollup(team_key, team_label)).add(
            **rollup_kwargs
        )
        project_rollups.setdefault(
            project_key, _EffectivenessRollup(project_key, project_label)
        ).add(**rollup_kwargs)
        cohort_rollups.setdefault(cohort_key, _EffectivenessRollup(cohort_key, cohort_label)).add(
            **rollup_kwargs
        )

    return InterventionEffectivenessResponse(
        summary=_rollup_to_summary(summary_rollup, total_interventions=len(interventions)),
        by_team=_sorted_group_rollups(team_rollups),
        by_project=_sorted_group_rollups(project_rollups),
        by_engineer_cohort=_sorted_group_rollups(cohort_rollups),
    )


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


def _completion_days(intervention: Intervention) -> float | None:
    if intervention.completed_at is None:
        return None
    created_at = _ensure_utc(intervention.created_at)
    completed_at = _ensure_utc(intervention.completed_at)
    return max((completed_at - created_at).total_seconds() / 86400, 0.0)


def _higher_is_better_delta(
    baseline: float | None,
    current: float | None,
) -> float | None:
    if baseline is None or current is None:
        return None
    return current - baseline


def _lower_is_better_delta(
    baseline: float | int | None,
    current: float | int | None,
) -> float | None:
    if baseline is None or current is None:
        return None
    return float(baseline) - float(current)


def _is_improved(
    *,
    success_rate_delta: float | None,
    friction_delta: float | None,
    findings_per_pr_delta: float | None,
    avg_cost_per_session_delta: float | None,
) -> bool:
    positive = 0
    negative = 0
    for delta, epsilon in (
        (success_rate_delta, SUCCESS_RATE_EPSILON),
        (friction_delta, 0.0),
        (findings_per_pr_delta, DECIMAL_DELTA_EPSILON),
        (avg_cost_per_session_delta, DECIMAL_DELTA_EPSILON),
    ):
        if delta is None:
            continue
        if delta > epsilon:
            positive += 1
        elif delta < -epsilon:
            negative += 1
    return positive > negative and positive > 0


def _team_group(
    intervention: Intervention,
    engineer_map: dict[str, Engineer],
    team_map: dict[str, Team],
) -> tuple[str, str]:
    team_id = intervention.team_id
    if team_id is None and intervention.engineer_id:
        target_engineer = engineer_map.get(intervention.engineer_id)
        team_id = target_engineer.team_id if target_engineer else None
    if team_id is None and intervention.owner_engineer_id:
        team_id = (
            engineer_map.get(intervention.owner_engineer_id).team_id
            if engineer_map.get(intervention.owner_engineer_id)
            else None
        )
    if team_id is None:
        return "organization", "Organization"
    return team_id, team_map.get(team_id).name if team_map.get(team_id) else "Unknown team"


def _project_group(intervention: Intervention) -> tuple[str, str]:
    if not intervention.project_name:
        return "unscoped", "Unscoped"
    return intervention.project_name, intervention.project_name


def _cohort_group(
    engineer_id: str | None,
    first_session_by_engineer: dict[str, datetime],
    now: datetime,
) -> tuple[str, str]:
    if not engineer_id:
        return "unscoped", "Unscoped"
    first_session = first_session_by_engineer.get(engineer_id)
    if first_session is None:
        return "experienced", "Experienced"
    days = (now - first_session).days
    if days <= 30:
        return "new_hire", "New Hire"
    if days <= 90:
        return "ramping", "Ramping"
    return "experienced", "Experienced"


def _rollup_to_summary(
    rollup: _EffectivenessRollup,
    *,
    total_interventions: int,
) -> InterventionEffectivenessSummary:
    return InterventionEffectivenessSummary(
        total_interventions=total_interventions,
        completed_interventions=rollup.completed_interventions,
        measured_interventions=rollup.measured_interventions,
        improved_interventions=rollup.improved_interventions,
        improvement_rate=_ratio(rollup.improved_interventions, rollup.measured_interventions),
        avg_completion_days=_average(rollup.completion_days),
        avg_success_rate_delta=_average(rollup.success_rate_deltas),
        avg_friction_delta=_average(rollup.friction_deltas),
        avg_findings_per_pr_delta=_average(rollup.findings_per_pr_deltas),
        avg_cost_per_session_delta=_average(rollup.avg_cost_per_session_deltas),
    )


def _sorted_group_rollups(
    rollups: dict[str, _EffectivenessRollup],
) -> list[InterventionEffectivenessGroup]:
    groups = [
        InterventionEffectivenessGroup(
            key=rollup.key,
            label=rollup.label,
            completed_interventions=rollup.completed_interventions,
            measured_interventions=rollup.measured_interventions,
            improved_interventions=rollup.improved_interventions,
            improvement_rate=_ratio(rollup.improved_interventions, rollup.measured_interventions),
            avg_completion_days=_average(rollup.completion_days),
            avg_success_rate_delta=_average(rollup.success_rate_deltas),
            avg_friction_delta=_average(rollup.friction_deltas),
            avg_findings_per_pr_delta=_average(rollup.findings_per_pr_deltas),
            avg_cost_per_session_delta=_average(rollup.avg_cost_per_session_deltas),
        )
        for rollup in rollups.values()
    ]
    return sorted(
        groups,
        key=lambda item: (
            -item.measured_interventions,
            -item.completed_interventions,
            item.label.lower(),
        ),
    )


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _engineer_summary(engineer: Engineer | None) -> InterventionEngineerSummary | None:
    if engineer is None:
        return None
    return InterventionEngineerSummary(id=engineer.id, name=engineer.name, email=engineer.email)
