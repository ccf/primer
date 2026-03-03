"""FinOps analytics service: cache analytics, cost modeling, forecasting, budgets."""

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from primer.common.models import Budget, Engineer, ModelUsage, Team
from primer.common.models import Session as SessionModel
from primer.common.pricing import PLAN_TIERS, estimate_cost, get_pricing
from primer.common.schemas import (
    BudgetCreate,
    BudgetStatus,
    BudgetUpdate,
    CacheAnalyticsResponse,
    CostForecastResponse,
    CostModelingResponse,
    DailyCacheEntry,
    DailyCostEntry,
    EngineerCacheEfficiency,
    EngineerCostComparison,
    ForecastPoint,
    ModelCacheBreakdown,
    PlanAllocationSummary,
    PlanTier,
)

# ---------------------------------------------------------------------------
# Cache Analytics
# ---------------------------------------------------------------------------


def get_cache_analytics(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> CacheAnalyticsResponse:
    """Cache hit rate, savings, daily trend, and per-model breakdown."""

    # Base filter for sessions
    def _apply_filters(q):
        if engineer_id:
            q = q.filter(SessionModel.engineer_id == engineer_id)
        elif team_id:
            q = q.join(Engineer, Engineer.id == SessionModel.engineer_id).filter(
                Engineer.team_id == team_id
            )
        if start_date:
            q = q.filter(SessionModel.started_at >= start_date)
        if end_date:
            q = q.filter(SessionModel.started_at <= end_date)
        return q

    # --- Aggregate totals ---
    agg_q = db.query(
        func.coalesce(func.sum(ModelUsage.cache_read_tokens), 0),
        func.coalesce(func.sum(ModelUsage.cache_creation_tokens), 0),
        func.coalesce(func.sum(ModelUsage.input_tokens), 0),
    ).join(SessionModel, SessionModel.id == ModelUsage.session_id)
    agg_q = _apply_filters(agg_q)
    agg = agg_q.first()
    total_cr = int(agg[0]) if agg else 0
    total_cc = int(agg[1]) if agg else 0
    total_inp = int(agg[2]) if agg else 0

    denom = total_cr + total_inp
    hit_rate = round(total_cr / denom, 4) if denom > 0 else None

    # Savings: per-model cache_read * (input_price - cache_read_price)
    savings = _compute_total_savings(db, _apply_filters)

    # --- Daily trend ---
    daily_q = (
        db.query(
            func.date(SessionModel.started_at).label("d"),
            func.coalesce(func.sum(ModelUsage.cache_read_tokens), 0),
            func.coalesce(func.sum(ModelUsage.cache_creation_tokens), 0),
            func.coalesce(func.sum(ModelUsage.input_tokens), 0),
        )
        .join(SessionModel, SessionModel.id == ModelUsage.session_id)
        .filter(SessionModel.started_at.isnot(None))
    )
    daily_q = _apply_filters(daily_q)
    daily_q = daily_q.group_by(func.date(SessionModel.started_at)).order_by(
        func.date(SessionModel.started_at)
    )

    daily_trend: list[DailyCacheEntry] = []
    for d, cr, cc, inp in daily_q.all():
        d_denom = int(cr) + int(inp)
        daily_trend.append(
            DailyCacheEntry(
                date=d,
                cache_read_tokens=int(cr),
                cache_creation_tokens=int(cc),
                input_tokens=int(inp),
                cache_hit_rate=round(int(cr) / d_denom, 3) if d_denom > 0 else None,
            )
        )

    # --- Per-model breakdown ---
    model_q = db.query(
        ModelUsage.model_name,
        func.coalesce(func.sum(ModelUsage.cache_read_tokens), 0),
        func.coalesce(func.sum(ModelUsage.cache_creation_tokens), 0),
        func.coalesce(func.sum(ModelUsage.input_tokens), 0),
    ).join(SessionModel, SessionModel.id == ModelUsage.session_id)
    model_q = _apply_filters(model_q)
    model_q = model_q.group_by(ModelUsage.model_name)

    model_breakdown: list[ModelCacheBreakdown] = []
    for name, cr, cc, inp in model_q.all():
        cr, cc, inp = int(cr), int(cc), int(inp)
        m_denom = cr + inp
        pricing = get_pricing(name)
        est_savings = round(cr * (pricing.input_per_token - pricing.cache_read_per_token), 4)
        model_breakdown.append(
            ModelCacheBreakdown(
                model_name=name,
                cache_read_tokens=cr,
                cache_creation_tokens=cc,
                input_tokens=inp,
                cache_hit_rate=round(cr / m_denom, 3) if m_denom > 0 else None,
                estimated_savings=est_savings,
            )
        )
    model_breakdown.sort(key=lambda m: m.estimated_savings, reverse=True)

    # --- Per-engineer cache breakdown ---
    eng_model_q = db.query(
        SessionModel.engineer_id,
        ModelUsage.model_name,
        func.coalesce(func.sum(ModelUsage.cache_read_tokens), 0),
        func.coalesce(func.sum(ModelUsage.input_tokens), 0),
    ).join(SessionModel, SessionModel.id == ModelUsage.session_id)
    eng_model_q = _apply_filters(eng_model_q)
    eng_model_q = eng_model_q.group_by(SessionModel.engineer_id, ModelUsage.model_name)

    # Accumulate per-engineer: savings, cache_read, input
    eng_data: dict[str, dict] = {}
    for eid, model_name, cr_val, inp_val in eng_model_q.all():
        cr_val, inp_val = int(cr_val), int(inp_val)
        pricing = get_pricing(model_name)
        model_savings = cr_val * (pricing.input_per_token - pricing.cache_read_per_token)
        if eid not in eng_data:
            eng_data[eid] = {"savings": 0.0, "cache_read": 0, "input": 0}
        eng_data[eid]["savings"] += model_savings
        eng_data[eid]["cache_read"] += cr_val
        eng_data[eid]["input"] += inp_val

    # Look up engineer names
    eng_ids = list(eng_data.keys())
    eng_name_map: dict[str, str] = {}
    if eng_ids:
        for eng in db.query(Engineer.id, Engineer.name).filter(Engineer.id.in_(eng_ids)).all():
            eng_name_map[eng.id] = eng.name

    # Compute per-engineer hit rates
    for d in eng_data.values():
        denom = d["cache_read"] + d["input"]
        d["hit_rate"] = round(d["cache_read"] / denom, 4) if denom > 0 else None

    # Team-average hit rate and weighted avg price delta
    total_team_cr = sum(d["cache_read"] for d in eng_data.values())
    total_team_inp = sum(d["input"] for d in eng_data.values())
    total_team_savings = sum(d["savings"] for d in eng_data.values())
    team_denom = total_team_cr + total_team_inp
    team_avg_rate = total_team_cr / team_denom if team_denom > 0 else 0
    avg_value_per_cached = total_team_savings / total_team_cr if total_team_cr > 0 else 0

    # Build engineer breakdown with potential upside
    engineer_breakdown: list[EngineerCacheEfficiency] = []
    total_potential = 0.0
    for eid, d in eng_data.items():
        potential = 0.0
        their_rate = d["hit_rate"] or 0
        if their_rate < team_avg_rate and d["input"] > 0:
            additional_cached = (team_avg_rate - their_rate) * (d["cache_read"] + d["input"])
            potential = additional_cached * avg_value_per_cached
        total_potential += potential
        engineer_breakdown.append(
            EngineerCacheEfficiency(
                engineer_id=eid,
                engineer_name=eng_name_map.get(eid, eid),
                cache_hit_rate=d["hit_rate"],
                estimated_savings=round(d["savings"], 4),
                potential_additional_savings=round(potential, 4),
                total_cache_read_tokens=d["cache_read"],
                total_input_tokens=d["input"],
            )
        )
    engineer_breakdown.sort(key=lambda e: e.estimated_savings, reverse=True)

    return CacheAnalyticsResponse(
        total_cache_read_tokens=total_cr,
        total_cache_creation_tokens=total_cc,
        total_input_tokens=total_inp,
        cache_hit_rate=hit_rate,
        cache_savings_estimate=savings,
        daily_cache_trend=daily_trend,
        model_cache_breakdown=model_breakdown,
        engineer_cache_breakdown=engineer_breakdown,
        total_potential_additional_savings=round(total_potential, 4),
    )


def _compute_total_savings(db: Session, apply_filters) -> float | None:
    """Compute total cache savings across all models using per-model pricing."""
    model_q = db.query(
        ModelUsage.model_name,
        func.coalesce(func.sum(ModelUsage.cache_read_tokens), 0),
    ).join(SessionModel, SessionModel.id == ModelUsage.session_id)
    model_q = apply_filters(model_q)
    model_q = model_q.group_by(ModelUsage.model_name)

    total_savings = 0.0
    any_data = False
    for name, cr in model_q.all():
        cr = int(cr)
        if cr > 0:
            any_data = True
            pricing = get_pricing(name)
            total_savings += cr * (pricing.input_per_token - pricing.cache_read_per_token)
    return round(total_savings, 4) if any_data else None


# ---------------------------------------------------------------------------
# Cost Modeling (Subscription vs API)
# ---------------------------------------------------------------------------


def get_cost_modeling(
    db: Session,
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> CostModelingResponse:
    """Compare API costs vs plan tier costs per engineer with optimal allocation."""

    # Determine period
    now = datetime.utcnow()
    eff_start = start_date or (now - timedelta(days=30))
    eff_end = end_date or now
    period_days = max((eff_end - eff_start).days, 1)

    plan_tiers = [PlanTier(**t) for t in PLAN_TIERS]

    # Per-engineer API costs
    q = (
        db.query(
            SessionModel.engineer_id,
            ModelUsage.model_name,
            func.sum(ModelUsage.input_tokens).label("inp"),
            func.sum(ModelUsage.output_tokens).label("out"),
            func.sum(ModelUsage.cache_read_tokens).label("cr"),
            func.sum(ModelUsage.cache_creation_tokens).label("cc"),
        )
        .join(ModelUsage, ModelUsage.session_id == SessionModel.id)
        .filter(SessionModel.started_at >= eff_start)
        .filter(SessionModel.started_at <= eff_end)
    )
    if team_id:
        q = q.join(Engineer, Engineer.id == SessionModel.engineer_id).filter(
            Engineer.team_id == team_id
        )
    q = q.group_by(SessionModel.engineer_id, ModelUsage.model_name)

    # Build per-engineer cost map
    engineer_costs: dict[str, float] = {}
    for eid, model, inp, out, cr, cc in q.all():
        inp, out, cr, cc = inp or 0, out or 0, cr or 0, cc or 0
        cost = estimate_cost(model, inp, out, cr, cc)
        engineer_costs[eid] = engineer_costs.get(eid, 0.0) + cost

    # Look up engineer names and billing modes
    eids = list(engineer_costs.keys())
    if not eids:
        return CostModelingResponse(
            period_days=period_days,
            plan_tiers=plan_tiers,
            engineers=[],
            allocation=[
                PlanAllocationSummary(
                    plan=t["name"],
                    label=t["label"],
                    monthly_cost_per_seat=t["monthly_cost"],
                    engineer_count=0,
                    total_monthly_cost=0,
                )
                for t in PLAN_TIERS
            ],
            total_api_cost_monthly=0,
            total_optimal_cost_monthly=0,
            total_savings_monthly=0,
        )

    engineers_db = db.query(Engineer).filter(Engineer.id.in_(eids)).all()
    eng_map = {e.id: e for e in engineers_db}

    # Billing mode from most recent session
    billing_modes: dict[str, str | None] = {}
    for eid in eids:
        latest = (
            db.query(SessionModel.billing_mode)
            .filter(SessionModel.engineer_id == eid)
            .filter(SessionModel.started_at >= eff_start)
            .filter(SessionModel.started_at <= eff_end)
            .filter(SessionModel.billing_mode.isnot(None))
            .order_by(SessionModel.started_at.desc())
            .first()
        )
        billing_modes[eid] = latest[0] if latest else None

    # Paid tiers (excluding api_key which has monthly_cost=0)
    paid_tiers = [t for t in PLAN_TIERS if t["monthly_cost"] > 0]

    comparisons: list[EngineerCostComparison] = []
    total_api_monthly = 0.0
    total_optimal_monthly = 0.0
    allocation_counts: dict[str, int] = {t["name"]: 0 for t in PLAN_TIERS}

    for eid, api_cost in sorted(engineer_costs.items(), key=lambda x: x[1]):
        eng = eng_map.get(eid)
        name = eng.name if eng else eid

        # Extrapolate to monthly
        monthly_api = api_cost * 30 / period_days
        daily_avg = api_cost / period_days

        # Find best plan: the highest tier still cheaper than API cost.
        # paid_tiers is sorted ascending (pro $20, max_5x $100, max_20x $200).
        # We want the most expensive tier that's still below the engineer's monthly
        # API spend — higher tiers offer more capacity for the price.
        best_plan = "api_key"
        best_cost = monthly_api

        for tier in paid_tiers:
            if tier["monthly_cost"] < monthly_api:
                best_plan = tier["name"]
                best_cost = tier["monthly_cost"]

        savings = monthly_api - best_cost
        allocation_counts[best_plan] += 1
        total_api_monthly += monthly_api
        total_optimal_monthly += best_cost

        comparisons.append(
            EngineerCostComparison(
                engineer_id=eid,
                engineer_name=name,
                monthly_api_cost=round(monthly_api, 2),
                recommended_plan=best_plan,
                recommended_plan_cost=round(best_cost, 2),
                savings_vs_api=round(savings, 2),
                current_billing_mode=billing_modes.get(eid),
                daily_avg_cost=round(daily_avg, 2),
            )
        )

    # Build allocation summary
    allocation = [
        PlanAllocationSummary(
            plan=t["name"],
            label=t["label"],
            monthly_cost_per_seat=t["monthly_cost"],
            engineer_count=allocation_counts[t["name"]],
            total_monthly_cost=round(
                allocation_counts[t["name"]] * t["monthly_cost"]
                if t["monthly_cost"] > 0
                else sum(
                    e.monthly_api_cost for e in comparisons if e.recommended_plan == "api_key"
                ),
                2,
            ),
        )
        for t in PLAN_TIERS
    ]

    return CostModelingResponse(
        period_days=period_days,
        plan_tiers=plan_tiers,
        engineers=comparisons,
        allocation=allocation,
        total_api_cost_monthly=round(total_api_monthly, 2),
        total_optimal_cost_monthly=round(total_optimal_monthly, 2),
        total_savings_monthly=round(total_api_monthly - total_optimal_monthly, 2),
    )


# ---------------------------------------------------------------------------
# Cost Forecasting
# ---------------------------------------------------------------------------


def get_cost_forecast(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    forecast_days: int = 30,
) -> CostForecastResponse:
    """Historical daily costs + linear regression forecast with confidence band."""

    # Historical daily costs
    q = (
        db.query(
            func.date(SessionModel.started_at).label("date"),
            ModelUsage.model_name,
            func.sum(ModelUsage.input_tokens).label("inp"),
            func.sum(ModelUsage.output_tokens).label("out"),
            func.sum(ModelUsage.cache_read_tokens).label("cr"),
            func.sum(ModelUsage.cache_creation_tokens).label("cc"),
            func.count(func.distinct(SessionModel.id)).label("sc"),
        )
        .join(ModelUsage, ModelUsage.session_id == SessionModel.id)
        .filter(SessionModel.started_at.isnot(None))
    )
    if engineer_id:
        q = q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        q = q.join(Engineer, Engineer.id == SessionModel.engineer_id).filter(
            Engineer.team_id == team_id
        )
    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)
    q = q.group_by(func.date(SessionModel.started_at), ModelUsage.model_name)

    # Aggregate per-day costs from per-model rows
    daily_costs: dict[str, float] = {}
    for d, model, inp, out, cr, cc, _sc in q.all():
        inp, out, cr, cc = inp or 0, out or 0, cr or 0, cc or 0
        cost = estimate_cost(model, inp, out, cr, cc)
        day_key = str(d)
        daily_costs[day_key] = daily_costs.get(day_key, 0.0) + cost

    # For session count per day, run a simpler aggregation from the already-fetched data.
    # Since we can't deduplicate perfectly from grouped rows, we fall back to a
    # separate lightweight query for per-day distinct session counts.
    sc_q = db.query(
        func.date(SessionModel.started_at).label("date"),
        func.count(func.distinct(SessionModel.id)).label("sc"),
    ).filter(SessionModel.started_at.isnot(None))
    if engineer_id:
        sc_q = sc_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        sc_q = sc_q.join(Engineer, Engineer.id == SessionModel.engineer_id).filter(
            Engineer.team_id == team_id
        )
    if start_date:
        sc_q = sc_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        sc_q = sc_q.filter(SessionModel.started_at <= end_date)
    sc_q = sc_q.group_by(func.date(SessionModel.started_at))

    daily_sc: dict[str, int] = {}
    for d, sc in sc_q.all():
        daily_sc[str(d)] = sc or 0

    daily_map: dict[str, tuple[float, int]] = {}
    for day_key, cost in daily_costs.items():
        daily_map[day_key] = (cost, daily_sc.get(day_key, 0))

    # Sort by date
    sorted_days = sorted(daily_map.items())
    historical = [
        DailyCostEntry(date=d, estimated_cost=round(c, 4), session_count=sc)
        for d, (c, sc) in sorted_days
    ]

    if len(historical) < 2:
        return CostForecastResponse(
            historical=historical,
            forecast=[],
            monthly_projection=round(
                sum(c for _, (c, _) in sorted_days) * 30 / max(len(sorted_days), 1), 2
            ),
            trend_direction="stable",
        )

    # Linear regression
    costs = [c for _, (c, _) in sorted_days]
    n = len(costs)
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(costs) / n
    ss_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, costs, strict=True))
    ss_xx = sum((x - x_mean) ** 2 for x in xs)
    slope = ss_xy / ss_xx if ss_xx > 0 else 0
    intercept = y_mean - slope * x_mean

    # Residual std dev
    residuals = [costs[i] - (slope * i + intercept) for i in range(n)]
    residual_std = (sum(r**2 for r in residuals) / max(n - 2, 1)) ** 0.5

    # Trend direction
    slope_pct = slope / y_mean if y_mean > 0 else 0
    if slope_pct > 0.05:
        trend = "increasing"
    elif slope_pct < -0.05:
        trend = "decreasing"
    else:
        trend = "stable"

    # Forecast
    from datetime import date as date_type

    last_date = date_type.fromisoformat(sorted_days[-1][0])
    forecast_points: list[ForecastPoint] = []
    for i in range(1, forecast_days + 1):
        fd = last_date + timedelta(days=i)
        x = n - 1 + i
        projected = max(slope * x + intercept, 0)
        upper = max(projected + residual_std, 0)
        lower = max(projected - residual_std, 0)
        forecast_points.append(
            ForecastPoint(
                date=fd.isoformat(),
                projected_cost=round(projected, 4),
                upper_bound=round(upper, 4),
                lower_bound=round(lower, 4),
            )
        )

    # Extrapolate to 30 days even if forecast_days < 30
    if forecast_days >= 30:
        monthly_projection = sum(fp.projected_cost for fp in forecast_points[:30])
    elif forecast_points:
        avg_daily = sum(fp.projected_cost for fp in forecast_points) / len(forecast_points)
        monthly_projection = avg_daily * 30
    else:
        monthly_projection = 0.0

    return CostForecastResponse(
        historical=historical,
        forecast=forecast_points,
        monthly_projection=round(monthly_projection, 2),
        trend_direction=trend,
    )


# ---------------------------------------------------------------------------
# Budget CRUD + Status
# ---------------------------------------------------------------------------


def list_budgets(
    db: Session,
    team_id: str | None = None,
) -> list[BudgetStatus]:
    """List all budgets with computed spend/status."""
    q = db.query(Budget)
    if team_id:
        q = q.filter(Budget.team_id == team_id)
    budgets = q.order_by(Budget.created_at.desc()).all()

    results: list[BudgetStatus] = []
    for b in budgets:
        status = _compute_budget_status(db, b)
        results.append(status)
    return results


def get_budget(db: Session, budget_id: str) -> Budget | None:
    """Fetch a single budget by ID."""
    return db.query(Budget).filter(Budget.id == budget_id).first()


def create_budget(db: Session, payload: BudgetCreate) -> BudgetStatus:
    budget = Budget(
        team_id=payload.team_id,
        name=payload.name,
        amount=payload.amount,
        period=payload.period,
        alert_threshold_pct=payload.alert_threshold_pct,
    )
    db.add(budget)
    db.flush()
    return _compute_budget_status(db, budget)


def update_budget(db: Session, budget_id: str, payload: BudgetUpdate) -> BudgetStatus | None:
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        return None
    for field in ["name", "amount", "period", "alert_threshold_pct"]:
        value = getattr(payload, field, None)
        if value is not None:
            setattr(budget, field, value)
    db.flush()
    return _compute_budget_status(db, budget)


def delete_budget(db: Session, budget_id: str) -> bool:
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        return False
    db.delete(budget)
    db.flush()
    return True


def _compute_budget_status(db: Session, budget: Budget) -> BudgetStatus:
    """Compute current spend, burn rate, and projected end-of-period for a budget."""
    now = datetime.utcnow()

    # Determine period boundaries
    if budget.period == "quarterly":
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        period_start = now.replace(
            month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        if quarter_month + 3 > 12:
            period_end = period_start.replace(year=period_start.year + 1, month=1)
        else:
            period_end = period_start.replace(month=quarter_month + 3)
    else:  # monthly
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            period_end = period_start.replace(year=now.year + 1, month=1)
        else:
            period_end = period_start.replace(month=now.month + 1)

    days_in_period = max((period_end - period_start).days, 1)
    days_elapsed = max((now - period_start).days, 1)

    # Sum estimated_cost for period
    cost_q = (
        db.query(
            ModelUsage.model_name,
            func.sum(ModelUsage.input_tokens),
            func.sum(ModelUsage.output_tokens),
            func.sum(ModelUsage.cache_read_tokens),
            func.sum(ModelUsage.cache_creation_tokens),
        )
        .join(SessionModel, SessionModel.id == ModelUsage.session_id)
        .filter(SessionModel.started_at >= period_start)
        .filter(SessionModel.started_at <= now)
    )
    if budget.team_id:
        cost_q = cost_q.join(Engineer, Engineer.id == SessionModel.engineer_id).filter(
            Engineer.team_id == budget.team_id
        )
    cost_q = cost_q.group_by(ModelUsage.model_name)

    current_spend = 0.0
    for model, inp, out, cr, cc in cost_q.all():
        inp, out, cr, cc = inp or 0, out or 0, cr or 0, cc or 0
        current_spend += estimate_cost(model, inp, out, cr, cc)

    burn_rate = current_spend / days_elapsed
    projected = burn_rate * days_in_period
    pct_used = (current_spend / budget.amount * 100) if budget.amount > 0 else 0

    if pct_used > 100:
        status = "over_budget"
    elif pct_used > budget.alert_threshold_pct:
        status = "warning"
    else:
        status = "on_track"

    # Team name lookup
    team_name = None
    if budget.team_id:
        team = db.query(Team).filter(Team.id == budget.team_id).first()
        team_name = team.name if team else None

    return BudgetStatus(
        id=budget.id,
        name=budget.name,
        team_id=budget.team_id,
        team_name=team_name,
        amount=budget.amount,
        period=budget.period,
        current_spend=round(current_spend, 2),
        burn_rate_daily=round(burn_rate, 2),
        projected_end_of_period=round(projected, 2),
        alert_threshold_pct=budget.alert_threshold_pct,
        pct_used=round(pct_used, 1),
        status=status,
    )
