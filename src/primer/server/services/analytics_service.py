from collections import Counter
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from primer.common.models import (
    Engineer,
    ModelUsage,
    SessionFacets,
    ToolUsage,
)
from primer.common.models import (
    Session as SessionModel,
)
from primer.common.pricing import estimate_cost
from primer.common.schemas import (
    CostAnalytics,
    DailyCostEntry,
    DailyStatsResponse,
    FrictionReport,
    ModelCostBreakdown,
    ModelRanking,
    OverviewStats,
    ToolRanking,
)


def _base_session_query(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    q = db.query(SessionModel)
    if engineer_id:
        q = q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        q = q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)
    return q


def get_overview(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> OverviewStats:
    q = _base_session_query(db, team_id, engineer_id, start_date, end_date)

    total_sessions = q.count()

    agg = q.with_entities(
        func.sum(SessionModel.message_count),
        func.sum(SessionModel.tool_call_count),
        func.sum(SessionModel.input_tokens),
        func.sum(SessionModel.output_tokens),
        func.avg(SessionModel.duration_seconds),
    ).first()

    total_messages = agg[0] or 0
    total_tool_calls = agg[1] or 0
    total_input_tokens = agg[2] or 0
    total_output_tokens = agg[3] or 0
    avg_duration = float(agg[4]) if agg[4] else None
    avg_messages = total_messages / total_sessions if total_sessions > 0 else None

    # Count unique engineers
    eng_q = db.query(func.count(func.distinct(SessionModel.engineer_id)))
    if engineer_id:
        eng_q = eng_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        eng_q = eng_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        eng_q = eng_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        eng_q = eng_q.filter(SessionModel.started_at <= end_date)
    total_engineers = eng_q.scalar() or 0

    # Outcome counts from facets
    facets_q = db.query(SessionFacets.outcome).join(SessionModel)
    if engineer_id:
        facets_q = facets_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        facets_q = facets_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        facets_q = facets_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        facets_q = facets_q.filter(SessionModel.started_at <= end_date)
    outcome_counts: dict[str, int] = {}
    for (outcome,) in facets_q.filter(SessionFacets.outcome.isnot(None)).all():
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

    # Session type counts
    type_q = db.query(SessionFacets.session_type).join(SessionModel)
    if engineer_id:
        type_q = type_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        type_q = type_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        type_q = type_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        type_q = type_q.filter(SessionModel.started_at <= end_date)
    session_type_counts: dict[str, int] = {}
    for (st,) in type_q.filter(SessionFacets.session_type.isnot(None)).all():
        session_type_counts[st] = session_type_counts.get(st, 0) + 1

    # Estimated cost from model usages
    cost_q = db.query(
        ModelUsage.model_name,
        func.sum(ModelUsage.input_tokens),
        func.sum(ModelUsage.output_tokens),
        func.sum(ModelUsage.cache_read_tokens),
        func.sum(ModelUsage.cache_creation_tokens),
    ).join(SessionModel)
    if engineer_id:
        cost_q = cost_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        cost_q = cost_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        cost_q = cost_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        cost_q = cost_q.filter(SessionModel.started_at <= end_date)
    cost_q = cost_q.group_by(ModelUsage.model_name)

    estimated_cost = 0.0
    for name, inp, out, cr, cc in cost_q.all():
        estimated_cost += estimate_cost(name, inp or 0, out or 0, cr or 0, cc or 0)

    return OverviewStats(
        total_sessions=total_sessions,
        total_engineers=total_engineers,
        total_messages=total_messages,
        total_tool_calls=total_tool_calls,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        estimated_cost=estimated_cost if estimated_cost > 0 else None,
        avg_session_duration=avg_duration,
        avg_messages_per_session=avg_messages,
        outcome_counts=outcome_counts,
        session_type_counts=session_type_counts,
    )


def get_daily_stats(
    db: Session,
    team_id: str | None = None,
    days: int = 30,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[DailyStatsResponse]:
    q = db.query(
        func.date(SessionModel.started_at).label("date"),
        func.count(SessionModel.id).label("session_count"),
        func.coalesce(func.sum(SessionModel.message_count), 0).label("message_count"),
        func.coalesce(func.sum(SessionModel.tool_call_count), 0).label("tool_call_count"),
    ).filter(SessionModel.started_at.isnot(None))

    if engineer_id:
        q = q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        q = q.join(Engineer).filter(Engineer.team_id == team_id)

    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)

    q = q.group_by(func.date(SessionModel.started_at)).order_by(
        func.date(SessionModel.started_at).desc()
    )

    rows = q.limit(days).all()
    return [
        DailyStatsResponse(
            date=row.date,
            session_count=row.session_count,
            message_count=row.message_count,
            tool_call_count=row.tool_call_count,
        )
        for row in rows
    ]


def get_friction_report(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[FrictionReport]:
    facets_q = db.query(SessionFacets).join(SessionModel)
    if engineer_id:
        facets_q = facets_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        facets_q = facets_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        facets_q = facets_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        facets_q = facets_q.filter(SessionModel.started_at <= end_date)

    friction_counter: Counter[str] = Counter()
    friction_details: dict[str, list[str]] = {}

    for facet in facets_q.filter(SessionFacets.friction_counts.isnot(None)).all():
        counts = facet.friction_counts or {}
        for friction_type, count in counts.items():
            friction_counter[friction_type] += count
            if facet.friction_detail and friction_type not in friction_details:
                friction_details[friction_type] = []
            if facet.friction_detail:
                friction_details[friction_type].append(facet.friction_detail)

    return [
        FrictionReport(
            friction_type=ft,
            count=count,
            details=friction_details.get(ft, [])[:10],  # cap details
        )
        for ft, count in friction_counter.most_common()
    ]


def get_tool_rankings(
    db: Session,
    team_id: str | None = None,
    limit: int = 20,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[ToolRanking]:
    q = db.query(
        ToolUsage.tool_name,
        func.sum(ToolUsage.call_count).label("total_calls"),
        func.count(func.distinct(ToolUsage.session_id)).label("session_count"),
    ).join(SessionModel)
    if engineer_id:
        q = q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        q = q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)
    q = q.group_by(ToolUsage.tool_name).order_by(func.sum(ToolUsage.call_count).desc())
    return [
        ToolRanking(tool_name=name, total_calls=total, session_count=sc)
        for name, total, sc in q.limit(limit).all()
    ]


def get_model_rankings(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[ModelRanking]:
    q = db.query(
        ModelUsage.model_name,
        func.sum(ModelUsage.input_tokens).label("total_input"),
        func.sum(ModelUsage.output_tokens).label("total_output"),
        func.count(func.distinct(ModelUsage.session_id)).label("session_count"),
    ).join(SessionModel)
    if engineer_id:
        q = q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        q = q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)
    q = q.group_by(ModelUsage.model_name).order_by(func.sum(ModelUsage.input_tokens).desc())
    return [
        ModelRanking(
            model_name=name,
            total_input_tokens=ti,
            total_output_tokens=to,
            session_count=sc,
        )
        for name, ti, to, sc in q.all()
    ]


def get_cost_analytics(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> CostAnalytics:
    """Compute cost breakdown by model and daily cost trend."""
    # Per-model breakdown
    q = db.query(
        ModelUsage.model_name,
        func.sum(ModelUsage.input_tokens).label("input_tokens"),
        func.sum(ModelUsage.output_tokens).label("output_tokens"),
        func.sum(ModelUsage.cache_read_tokens).label("cache_read_tokens"),
        func.sum(ModelUsage.cache_creation_tokens).label("cache_creation_tokens"),
    ).join(SessionModel)
    if engineer_id:
        q = q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        q = q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)
    q = q.group_by(ModelUsage.model_name)

    total_cost = 0.0
    breakdown: list[ModelCostBreakdown] = []
    for name, inp, out, cr, cc in q.all():
        inp, out, cr, cc = inp or 0, out or 0, cr or 0, cc or 0
        cost = estimate_cost(name, inp, out, cr, cc)
        total_cost += cost
        breakdown.append(
            ModelCostBreakdown(
                model_name=name,
                input_tokens=inp,
                output_tokens=out,
                cache_read_tokens=cr,
                cache_creation_tokens=cc,
                estimated_cost=cost,
            )
        )
    breakdown.sort(key=lambda m: m.estimated_cost, reverse=True)

    # Daily cost trend
    daily_q = (
        db.query(
            func.date(SessionModel.started_at).label("date"),
            ModelUsage.model_name,
            func.sum(ModelUsage.input_tokens).label("input_tokens"),
            func.sum(ModelUsage.output_tokens).label("output_tokens"),
            func.sum(ModelUsage.cache_read_tokens).label("cache_read_tokens"),
            func.sum(ModelUsage.cache_creation_tokens).label("cache_creation_tokens"),
            func.count(func.distinct(SessionModel.id)).label("session_count"),
        )
        .join(SessionModel)
        .filter(SessionModel.started_at.isnot(None))
    )
    if engineer_id:
        daily_q = daily_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        daily_q = daily_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        daily_q = daily_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        daily_q = daily_q.filter(SessionModel.started_at <= end_date)
    daily_q = daily_q.group_by(func.date(SessionModel.started_at), ModelUsage.model_name).order_by(
        func.date(SessionModel.started_at)
    )

    daily_map: dict[str, DailyCostEntry] = {}
    for d, name, inp, out, cr, cc, sc in daily_q.all():
        cost = estimate_cost(name, inp or 0, out or 0, cr or 0, cc or 0)
        date_str = str(d)
        if date_str in daily_map:
            entry = daily_map[date_str]
            daily_map[date_str] = DailyCostEntry(
                date=entry.date,
                estimated_cost=entry.estimated_cost + cost,
                session_count=max(entry.session_count, sc),
            )
        else:
            daily_map[date_str] = DailyCostEntry(date=d, estimated_cost=cost, session_count=sc)

    daily_costs = sorted(daily_map.values(), key=lambda e: e.date)

    return CostAnalytics(
        total_estimated_cost=total_cost,
        model_breakdown=breakdown,
        daily_costs=daily_costs,
    )
