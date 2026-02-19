from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import get_db
from primer.common.schemas import (
    ActivityHeatmap,
    BottleneckAnalytics,
    ClaudePRComparisonResponse,
    ConfigOptimizationResponse,
    CostAnalytics,
    DailyStatsResponse,
    EngineerAnalytics,
    EngineerBenchmarkResponse,
    EngineerProfileResponse,
    FrictionReport,
    GitHubStatusResponse,
    GitHubSyncResponse,
    LearningPathsResponse,
    MaturityAnalyticsResponse,
    ModelRanking,
    NarrativeResponse,
    NarrativeStatusResponse,
    OnboardingAccelerationResponse,
    OverviewStats,
    PatternSharingResponse,
    PersonalizedTipsResponse,
    ProductivityMetrics,
    ProjectAnalytics,
    QualityMetricsResponse,
    Recommendation,
    SessionInsightsResponse,
    SkillInventoryResponse,
    TimeToTeamAverageResponse,
    ToolAdoptionAnalytics,
    ToolRanking,
)
from primer.server.deps import AuthContext, get_auth_context, require_role
from primer.server.services.analytics_service import (
    get_activity_heatmap,
    get_bottleneck_analytics,
    get_cost_analytics,
    get_daily_stats,
    get_engineer_analytics,
    get_engineer_benchmarks,
    get_friction_report,
    get_model_rankings,
    get_overview,
    get_productivity_metrics,
    get_project_analytics,
    get_tool_adoption_analytics,
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
    if auth.role == "admin":
        tid = team_id
    elif not auth.team_id:
        raise HTTPException(status_code=400, detail="No team assigned")
    else:
        tid = auth.team_id
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


@router.get("/bottlenecks", response_model=BottleneckAnalytics)
def bottlenecks(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_bottleneck_analytics(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/tool-adoption", response_model=ToolAdoptionAnalytics)
def tool_adoption(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_tool_adoption_analytics(
        db,
        team_id=tid,
        engineer_id=eid,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@router.get("/config-optimization", response_model=ConfigOptimizationResponse)
def config_optimization(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.insights_service import get_config_optimization

    tid, eid = _resolve_scope(auth, team_id)
    return get_config_optimization(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/personalized-tips", response_model=PersonalizedTipsResponse)
def personalized_tips(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.insights_service import get_personalized_tips

    tid, eid = _resolve_scope(auth, team_id)
    return get_personalized_tips(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/skill-inventory", response_model=SkillInventoryResponse)
def skill_inventory(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.insights_service import get_skill_inventory

    tid, eid = _resolve_scope(auth, team_id)
    return get_skill_inventory(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/learning-paths", response_model=LearningPathsResponse)
def learning_paths(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.insights_service import get_learning_paths

    tid, eid = _resolve_scope(auth, team_id)
    return get_learning_paths(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/pattern-sharing", response_model=PatternSharingResponse)
def pattern_sharing(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.insights_service import get_pattern_sharing

    tid, eid = _resolve_scope(auth, team_id)
    return get_pattern_sharing(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/onboarding-acceleration", response_model=OnboardingAccelerationResponse)
def onboarding_acceleration(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.insights_service import get_onboarding_acceleration

    tid, eid = _resolve_scope(auth, team_id)
    return get_onboarding_acceleration(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/quality-metrics", response_model=QualityMetricsResponse)
def quality_metrics(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.quality_service import get_quality_metrics

    tid, eid = _resolve_scope(auth, team_id)
    return get_quality_metrics(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/session-insights", response_model=SessionInsightsResponse)
def session_insights(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.session_insights_service import get_session_insights

    tid, eid = _resolve_scope(auth, team_id)
    return get_session_insights(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/maturity", response_model=MaturityAnalyticsResponse)
def maturity_analytics(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.maturity_service import get_maturity_analytics

    tid, eid = _resolve_scope(auth, team_id)
    return get_maturity_analytics(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.post("/github/sync", response_model=GitHubSyncResponse)
def sync_github_data(
    repository: str | None = None,
    since_days: int = Query(default=30, le=365),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    from primer.common.models import GitRepository
    from primer.server.services.github_service import sync_repository

    totals = {"repos_synced": 0, "prs_found": 0, "commits_correlated": 0}

    repos = [repository] if repository else [r.full_name for r in db.query(GitRepository).all()]

    for full_name in repos:
        stats = sync_repository(db, full_name, since_days=since_days)
        totals["repos_synced"] += 1
        totals["prs_found"] += stats["prs_found"]
        totals["commits_correlated"] += stats["commits_correlated"]

    db.commit()
    return GitHubSyncResponse(**totals)


@router.get("/github/status", response_model=GitHubStatusResponse)
def github_status(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    from primer.common.models import GitRepository, PullRequest
    from primer.server.services.github_service import is_configured

    return GitHubStatusResponse(
        configured=is_configured(),
        app_id=settings.github_app_id,
        installation_id=settings.github_installation_id,
        repos_count=db.query(GitRepository).count(),
        prs_count=db.query(PullRequest).count(),
    )


@router.get("/engineers/{engineer_id}/profile", response_model=EngineerProfileResponse)
def engineer_profile(
    engineer_id: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.common.models import Engineer
    from primer.server.services.engineer_profile_service import get_engineer_profile

    # Auth: engineer can view own; team_lead can view team members; admin any
    if auth.role == "engineer" and auth.engineer_id != engineer_id:
        raise HTTPException(status_code=403, detail="Cannot view another engineer's profile")
    if auth.role == "team_lead":
        eng = db.query(Engineer).filter(Engineer.id == engineer_id).first()
        if not eng or eng.team_id != auth.team_id:
            raise HTTPException(status_code=403, detail="Not your team's engineer")

    result = get_engineer_profile(db, engineer_id, start_date, end_date)
    if not result:
        raise HTTPException(status_code=404, detail="Engineer not found")
    return result


@router.get("/claude-pr-comparison", response_model=ClaudePRComparisonResponse)
def claude_pr_comparison(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.quality_service import get_claude_pr_comparison

    tid, eid = _resolve_scope(auth, team_id)
    return get_claude_pr_comparison(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/time-to-team-average", response_model=TimeToTeamAverageResponse)
def time_to_team_average(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.common.models import Engineer
    from primer.server.services.insights_service import get_time_to_team_average

    # Time-to-team-average needs team-wide data, not single-engineer scope.
    # For engineers, resolve their team_id so the team avg is meaningful.
    if auth.role == "admin":
        tid = team_id
    elif auth.role == "team_lead":
        tid = auth.team_id
    else:
        eng = db.query(Engineer.team_id).filter(Engineer.id == auth.engineer_id).first()
        if not eng or not eng.team_id:
            raise HTTPException(status_code=403, detail="No team assigned")
        tid = eng.team_id

    return get_time_to_team_average(
        db, team_id=tid, engineer_id=None, start_date=start_date, end_date=end_date
    )


@router.get("/narrative/status", response_model=NarrativeStatusResponse)
def narrative_status(
    auth: AuthContext = Depends(get_auth_context),
):
    if not settings.anthropic_api_key:
        return NarrativeStatusResponse(
            available=False, reason="PRIMER_ANTHROPIC_API_KEY not configured"
        )
    return NarrativeStatusResponse(available=True)


@router.get("/narrative", response_model=NarrativeResponse)
def narrative(
    scope: str = Query(default="engineer", pattern="^(engineer|team|org)$"),
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    force_refresh: bool = False,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.common.models import Engineer
    from primer.server.services.narrative_service import generate_narrative

    # Resolve scope parameters
    if scope == "engineer":
        if engineer_id:
            # Admin or team_lead viewing another engineer's narrative
            if auth.role == "admin":
                eid = engineer_id
            elif auth.role == "team_lead":
                eng = db.query(Engineer).filter(Engineer.id == engineer_id).first()
                if not eng or eng.team_id != auth.team_id:
                    raise HTTPException(status_code=403, detail="Not your team's engineer")
                eid = engineer_id
            else:
                raise HTTPException(
                    status_code=403, detail="Only admin or team_lead can view other engineers"
                )
        else:
            if not auth.engineer_id:
                raise HTTPException(status_code=400, detail="Engineer scope requires engineer auth")
            eid = auth.engineer_id
        tid = None
    elif scope == "team":
        tid, _ = _resolve_scope(auth, team_id)
        if not tid:
            raise HTTPException(status_code=400, detail="No team context available")
        eid = None
    else:  # org
        if auth.role not in ("admin", "team_lead"):
            raise HTTPException(status_code=403, detail="Org scope requires admin or team_lead")
        tid = None
        eid = None

    try:
        result = generate_narrative(
            db,
            scope=scope,
            team_id=tid,
            engineer_id=eid,
            start_date=start_date,
            end_date=end_date,
            force_refresh=force_refresh,
        )
        db.commit()
        return result
    except ValueError as e:
        error_msg = str(e)
        if "not configured" in error_msg:
            raise HTTPException(status_code=503, detail=error_msg) from None
        if "Insufficient data" in error_msg:
            raise HTTPException(status_code=422, detail=error_msg) from None
        raise HTTPException(status_code=500, detail=error_msg) from None
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None
