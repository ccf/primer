from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from primer.common.models import Session as SessionModel
from primer.common.models import SessionWorkflowProfile, Team
from primer.common.schemas import (
    CompareDelta,
    CompareResponse,
    CompareSnapshot,
    CompareWorkflowEntry,
)
from primer.server.services.analytics_service import (
    base_session_query,
    get_overview,
    get_productivity_metrics,
)
from primer.server.services.engineer_profile_service import get_engineer_profile
from primer.server.services.maturity_service import get_maturity_analytics
from primer.server.services.project_workspace_service import get_project_workspace
from primer.server.services.quality_service import get_quality_metrics


def get_compare_response(
    db: Session,
    *,
    mode: str,
    left_key: str | None = None,
    right_key: str | None = None,
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> CompareResponse:
    if mode == "team":
        if not left_key or not right_key:
            raise ValueError("team compare requires left_key and right_key")
        left = _build_team_snapshot(db, left_key, start_date=start_date, end_date=end_date)
        right = _build_team_snapshot(db, right_key, start_date=start_date, end_date=end_date)
    elif mode == "engineer":
        if not left_key or not right_key:
            raise ValueError("engineer compare requires left_key and right_key")
        left = _build_engineer_snapshot(db, left_key, start_date=start_date, end_date=end_date)
        right = _build_engineer_snapshot(db, right_key, start_date=start_date, end_date=end_date)
    elif mode == "project":
        if not left_key or not right_key:
            raise ValueError("project compare requires left_key and right_key")
        left = _build_project_snapshot(
            db,
            left_key,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
        )
        right = _build_project_snapshot(
            db,
            right_key,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
        )
    elif mode == "period":
        left, right = _build_period_snapshots(
            db,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
        )
    else:
        raise ValueError(f"Unsupported compare mode: {mode}")

    return CompareResponse(mode=mode, left=left, right=right, delta=_build_delta(left, right))


def _build_team_snapshot(
    db: Session,
    team_id: str,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> CompareSnapshot:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise ValueError("Team not found")

    overview = get_overview(db, team_id=team_id, start_date=start_date, end_date=end_date)
    productivity = get_productivity_metrics(
        db,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
    )
    quality = get_quality_metrics(db, team_id=team_id, start_date=start_date, end_date=end_date)
    maturity = get_maturity_analytics(db, team_id=team_id, start_date=start_date, end_date=end_date)

    return CompareSnapshot(
        label=team.name,
        total_sessions=overview.total_sessions,
        success_rate=overview.success_rate,
        total_cost=productivity.total_cost,
        avg_cost_per_session=productivity.avg_cost_per_session,
        cost_per_successful_outcome=productivity.cost_per_successful_outcome,
        pr_merge_rate=quality.overview.pr_merge_rate,
        findings_fix_rate=(
            quality.findings_overview.fix_rate if quality.findings_overview else None
        ),
        effectiveness_score=_avg(
            [
                profile.effectiveness_score
                for profile in maturity.engineer_profiles
                if profile.effectiveness_score is not None
            ]
        ),
        leverage_score=_avg(
            [
                profile.leverage_score
                for profile in maturity.engineer_profiles
                if profile.leverage_score is not None
            ]
        ),
        top_workflows=_get_top_workflows(
            db,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
        ),
    )


def _build_engineer_snapshot(
    db: Session,
    engineer_id: str,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> CompareSnapshot:
    profile = get_engineer_profile(db, engineer_id, start_date=start_date, end_date=end_date)
    if not profile:
        raise ValueError("Engineer not found")

    productivity = get_productivity_metrics(
        db,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )

    findings_fix_rate = None
    findings_overview = (
        profile.quality.get("findings_overview") if isinstance(profile.quality, dict) else None
    )
    if isinstance(findings_overview, dict):
        findings_fix_rate = findings_overview.get("fix_rate")

    top_workflows = []
    if profile.impact_review:
        top_workflows = [
            CompareWorkflowEntry(
                label=workflow.archetype,
                session_count=workflow.session_count,
                share_of_sessions=workflow.share_of_sessions,
            )
            for workflow in profile.impact_review.top_workflows[:3]
        ]

    return CompareSnapshot(
        label=profile.display_name or profile.name,
        total_sessions=profile.overview.total_sessions,
        success_rate=profile.overview.success_rate,
        total_cost=profile.overview.estimated_cost,
        avg_cost_per_session=productivity.avg_cost_per_session,
        cost_per_successful_outcome=productivity.cost_per_successful_outcome,
        pr_merge_rate=_parse_percentish(
            profile.quality.get("merge_rate") if isinstance(profile.quality, dict) else None
        ),
        findings_fix_rate=findings_fix_rate,
        effectiveness_score=(profile.effectiveness.score if profile.effectiveness else None),
        leverage_score=profile.leverage_score,
        top_workflows=top_workflows,
    )


def _build_project_snapshot(
    db: Session,
    project_name: str,
    *,
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> CompareSnapshot:
    workspace = get_project_workspace(
        db,
        project_name,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
    )
    if not workspace:
        raise ValueError("Project not found")

    return CompareSnapshot(
        label=workspace.project.project_name,
        total_sessions=workspace.overview.total_sessions,
        success_rate=workspace.overview.success_rate,
        total_cost=workspace.cost.total_estimated_cost,
        avg_cost_per_session=workspace.productivity.avg_cost_per_session,
        cost_per_successful_outcome=workspace.productivity.cost_per_successful_outcome,
        pr_merge_rate=workspace.quality.overview.pr_merge_rate,
        findings_fix_rate=(
            workspace.quality.findings_overview.fix_rate
            if workspace.quality.findings_overview
            else None
        ),
        effectiveness_score=(
            workspace.scorecard.effectiveness_score.score
            if workspace.scorecard.effectiveness_score
            else None
        ),
        leverage_score=None,
        top_workflows=[
            CompareWorkflowEntry(
                label=fingerprint.label,
                session_count=fingerprint.session_count,
                share_of_sessions=fingerprint.share_of_sessions,
            )
            for fingerprint in workspace.workflow_summary.fingerprints[:3]
        ],
    )


def _build_period_snapshots(
    db: Session,
    *,
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> tuple[CompareSnapshot, CompareSnapshot]:
    now = datetime.now(UTC)
    current_end = _ensure_utc(end_date) if end_date else now
    current_start = _ensure_utc(start_date) if start_date else current_end - timedelta(days=30)
    window = current_end - current_start
    if window <= timedelta(0):
        window = timedelta(days=30)
        current_start = current_end - window
    previous_end = current_start - timedelta(microseconds=1)
    previous_start = previous_end - window

    left = _build_period_snapshot(
        db,
        label="Selected Period",
        team_id=team_id,
        start_date=current_start,
        end_date=current_end,
    )
    right = _build_period_snapshot(
        db,
        label="Previous Period",
        team_id=team_id,
        start_date=previous_start,
        end_date=previous_end,
    )
    return left, right


def _build_period_snapshot(
    db: Session,
    *,
    label: str,
    team_id: str | None,
    start_date: datetime,
    end_date: datetime,
) -> CompareSnapshot:
    overview = get_overview(db, team_id=team_id, start_date=start_date, end_date=end_date)
    productivity = get_productivity_metrics(
        db,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
    )
    quality = get_quality_metrics(db, team_id=team_id, start_date=start_date, end_date=end_date)
    maturity = get_maturity_analytics(db, team_id=team_id, start_date=start_date, end_date=end_date)

    return CompareSnapshot(
        label=label,
        total_sessions=overview.total_sessions,
        success_rate=overview.success_rate,
        total_cost=productivity.total_cost,
        avg_cost_per_session=productivity.avg_cost_per_session,
        cost_per_successful_outcome=productivity.cost_per_successful_outcome,
        pr_merge_rate=quality.overview.pr_merge_rate,
        findings_fix_rate=(
            quality.findings_overview.fix_rate if quality.findings_overview else None
        ),
        effectiveness_score=_avg(
            [
                profile.effectiveness_score
                for profile in maturity.engineer_profiles
                if profile.effectiveness_score is not None
            ]
        ),
        leverage_score=_avg(
            [
                profile.leverage_score
                for profile in maturity.engineer_profiles
                if profile.leverage_score is not None
            ]
        ),
        top_workflows=_get_top_workflows(
            db,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
        ),
    )


def _get_top_workflows(
    db: Session,
    *,
    team_id: str | None = None,
    engineer_id: str | None = None,
    project_name: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 3,
) -> list[CompareWorkflowEntry]:
    query = (
        base_session_query(
            db,
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
            project_name=project_name,
        )
        .join(SessionWorkflowProfile, SessionWorkflowProfile.session_id == SessionModel.id)
        .with_entities(SessionWorkflowProfile.archetype)
    )
    rows = [row[0] for row in query.all() if row[0]]
    total = len(rows)
    if total == 0:
        return []
    counts: dict[str, int] = {}
    for row in rows:
        counts[row] = counts.get(row, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return [
        CompareWorkflowEntry(
            label=label,
            session_count=count,
            share_of_sessions=round(count / total, 3),
        )
        for label, count in ordered
    ]


def _build_delta(left: CompareSnapshot, right: CompareSnapshot) -> CompareDelta:
    return CompareDelta(
        total_sessions=left.total_sessions - right.total_sessions,
        success_rate=_subtract_nullable(left.success_rate, right.success_rate),
        total_cost=_subtract_nullable(left.total_cost, right.total_cost),
        avg_cost_per_session=_subtract_nullable(
            left.avg_cost_per_session, right.avg_cost_per_session
        ),
        cost_per_successful_outcome=_subtract_nullable(
            left.cost_per_successful_outcome, right.cost_per_successful_outcome
        ),
        pr_merge_rate=_subtract_nullable(left.pr_merge_rate, right.pr_merge_rate),
        findings_fix_rate=_subtract_nullable(left.findings_fix_rate, right.findings_fix_rate),
        effectiveness_score=_subtract_nullable(left.effectiveness_score, right.effectiveness_score),
        leverage_score=_subtract_nullable(left.leverage_score, right.leverage_score),
    )


def _subtract_nullable(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _parse_percentish(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.endswith("%"):
        try:
            return float(value[:-1]) / 100.0
        except ValueError:
            return None
    return None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
