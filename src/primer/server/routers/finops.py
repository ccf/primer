"""FinOps router: cache analytics, cost modeling, forecasting, budgets."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.schemas import (
    BudgetCreate,
    BudgetStatus,
    BudgetUpdate,
    CacheAnalyticsResponse,
    CostForecastResponse,
    CostModelingResponse,
)
from primer.server.deps import AuthContext, get_auth_context, require_role
from primer.server.services.finops_service import (
    create_budget,
    delete_budget,
    get_cache_analytics,
    get_cost_forecast,
    get_cost_modeling,
    list_budgets,
    update_budget,
)

router = APIRouter(prefix="/api/v1/finops", tags=["finops"])


def _resolve_scope(
    auth: AuthContext, requested_team_id: str | None
) -> tuple[str | None, str | None]:
    """Return (team_id, engineer_id) based on role."""
    if auth.role == "admin":
        return requested_team_id, None
    if auth.role == "team_lead":
        return auth.team_id, None
    return None, auth.engineer_id


@router.get("/cache", response_model=CacheAnalyticsResponse)
def cache_analytics(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_cache_analytics(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )


@router.get("/cost-modeling", response_model=CostModelingResponse)
def cost_modeling(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin", "team_lead")),
):
    tid, _ = _resolve_scope(auth, team_id)
    return get_cost_modeling(
        db,
        team_id=tid,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/forecast", response_model=CostForecastResponse)
def cost_forecast(
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    forecast_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    tid, eid = _resolve_scope(auth, team_id)
    return get_cost_forecast(
        db,
        team_id=tid,
        engineer_id=eid,
        start_date=start_date,
        end_date=end_date,
        forecast_days=forecast_days,
    )


@router.get("/budgets", response_model=list[BudgetStatus])
def budgets_list(
    team_id: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin", "team_lead")),
):
    tid, _ = _resolve_scope(auth, team_id)
    return list_budgets(db, team_id=tid)


@router.post("/budgets", response_model=BudgetStatus, status_code=201)
def budgets_create(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_role("admin", "team_lead")),
):
    result = create_budget(db, payload)
    db.commit()
    return result


@router.patch("/budgets/{budget_id}", response_model=BudgetStatus)
def budgets_update(
    budget_id: str,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_role("admin", "team_lead")),
):
    result = update_budget(db, budget_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.commit()
    return result


@router.delete("/budgets/{budget_id}", status_code=204)
def budgets_delete(
    budget_id: str,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_role("admin", "team_lead")),
):
    if not delete_budget(db, budget_id):
        raise HTTPException(status_code=404, detail="Budget not found")
    db.commit()
