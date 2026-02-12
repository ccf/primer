from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.schemas import (
    FrictionReport,
    ModelRanking,
    OverviewStats,
    Recommendation,
    ToolRanking,
)
from primer.server.deps import require_admin
from primer.server.services.analytics_service import (
    get_friction_report,
    get_model_rankings,
    get_overview,
    get_tool_rankings,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewStats)
def overview(
    team_id: str | None = None,
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    return get_overview(db, team_id=team_id)


@router.get("/friction", response_model=list[FrictionReport])
def friction(
    team_id: str | None = None,
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    return get_friction_report(db, team_id=team_id)


@router.get("/tools", response_model=list[ToolRanking])
def tools(
    team_id: str | None = None,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    return get_tool_rankings(db, team_id=team_id, limit=limit)


@router.get("/models", response_model=list[ModelRanking])
def models(
    team_id: str | None = None,
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    return get_model_rankings(db, team_id=team_id)


@router.get("/recommendations", response_model=list[Recommendation])
def recommendations(
    team_id: str | None = None,
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    from primer.server.services.synthesis_service import get_recommendations

    return get_recommendations(db, team_id=team_id)
