from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.schemas import (
    ActivityHeatmap,
    CostAnalytics,
    DailyStatsResponse,
    EngineerAnalytics,
    EngineerBenchmarkResponse,
    FrictionReport,
    ModelRanking,
    OverviewStats,
    ProductivityMetrics,
    ProjectAnalytics,
    Recommendation,
    ToolRanking,
)
from primer.server.deps import AuthContext, get_auth_context, require_role
from primer.server.services.analytics_service import (
    get_activity_heatmap,
    get_cost_analytics,
    get_daily_stats,
    get_engineer_analytics,
    get_engineer_benchmarks,
    get_friction_report,
    get_model_rankings,
    get_overview,
    get_productivity_metrics,
    get_project_analytics,
    get_tool_rankings,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def _resolve_scope(
    auth: AuthContext, requested_team_id: str | None
) -> tuple[str | None, str | None]:
    """Return (team_id, engineer_id) based on role."""
    if auth.role == "admin":
        return requested_team_id, None
    if auth.role == "team_lead":
        return auth.team_id, None
    # engineer
    return None, auth.engineer_id


@router.get("/overview", response_model=OverviewStats)
def overview(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_overview(db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date)


@router.get("/daily", response_model=list[DailyStatsResponse])
def daily(
    team_id: str | None = None,
    days: int = Query(default=30, le=365),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_daily_stats(
        db, team_id=tid, days=days, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/friction", response_model=list[FrictionReport])
def friction(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_friction_report(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/tools", response_model=list[ToolRanking])
def tools(
    team_id: str | None = None,
    limit: int = Query(default=20, le=100),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_tool_rankings(
        db, team_id=tid, limit=limit, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/models", response_model=list[ModelRanking])
def models(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_model_rankings(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/costs", response_model=CostAnalytics)
def costs(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_cost_analytics(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/recommendations", response_model=list[Recommendation])
def recommendations(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.synthesis_service import get_recommendations

    tid, eid = _resolve_scope(auth, team_id)
    return get_recommendations(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/engineers", response_model=EngineerAnalytics)
def engineer_analytics(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    sort_by: str = Query(default="total_sessions"),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_engineer_analytics(
        db,
        team_id=tid,
        engineer_id=eid,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        limit=limit,
    )


@router.get("/projects", response_model=ProjectAnalytics)
def project_analytics(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    sort_by: str = Query(default="total_sessions"),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_project_analytics(
        db,
        team_id=tid,
        engineer_id=eid,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        limit=limit,
    )


@router.get("/productivity", response_model=ProductivityMetrics)
def productivity(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_productivity_metrics(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/engineers/benchmarks", response_model=EngineerBenchmarkResponse)
def engineer_benchmarks(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("team_lead", "admin")),
):
    tid = team_id if auth.role == "admin" else auth.team_id
    return get_engineer_benchmarks(db, team_id=tid, start_date=start_date, end_date=end_date)


@router.get("/activity-heatmap", response_model=ActivityHeatmap)
def activity_heatmap(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_activity_heatmap(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )
