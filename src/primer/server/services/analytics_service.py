from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import case, func
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
    ActivityHeatmap,
    CostAnalytics,
    DailyCostEntry,
    DailyStatsResponse,
    EngineerAnalytics,
    EngineerStats,
    FrictionReport,
    HeatmapCell,
    ModelCostBreakdown,
    ModelRanking,
    OverviewStats,
    ProjectAnalytics,
    ProjectStats,
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


def _compute_success_rate(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> float | None:
    """Compute success rate from session facets."""
    facets_q = db.query(SessionFacets.outcome).join(SessionModel)
    if engineer_id:
        facets_q = facets_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        facets_q = facets_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        facets_q = facets_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        facets_q = facets_q.filter(SessionModel.started_at <= end_date)
    facets_q = facets_q.filter(SessionFacets.outcome.isnot(None))
    outcomes = [row[0] for row in facets_q.all()]
    if not outcomes:
        return None
    return sum(1 for o in outcomes if o == "success") / len(outcomes)


def _build_overview(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> OverviewStats:
    """Internal helper that builds an OverviewStats without previous_period."""
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

    # Success rate
    success_rate = _compute_success_rate(db, team_id, engineer_id, start_date, end_date)

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
        success_rate=success_rate,
    )


def get_overview(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> OverviewStats:
    result = _build_overview(db, team_id, engineer_id, start_date, end_date)

    # Compute previous period for comparison (only when a date range is provided)
    if start_date and end_date:
        # Ensure both are tz-aware for safe subtraction
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=UTC)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=UTC)
        delta = end_date - start_date
        prev_end = start_date
        prev_start = prev_end - delta
        previous = _build_overview(db, team_id, engineer_id, prev_start, prev_end)
        if previous.total_sessions > 0:
            result.previous_period = previous
    elif start_date:
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=UTC)
        delta = datetime.now(UTC) - start_date
        prev_end = start_date
        prev_start = prev_end - delta
        previous = _build_overview(db, team_id, engineer_id, prev_start, prev_end)
        if previous.total_sessions > 0:
            result.previous_period = previous
    # No date range ("All") → skip deltas since comparing all-time vs an
    # arbitrary prior window produces misleading percentage changes.

    return result


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

    # Compute per-day success rates from facets
    date_set = {row.date for row in rows}
    success_rates: dict[str, float | None] = {}
    if date_set:
        sr_q = (
            db.query(
                func.date(SessionModel.started_at).label("date"),
                func.sum(case((SessionFacets.outcome == "success", 1), else_=0)).label("successes"),
                func.count(SessionFacets.outcome).label("total"),
            )
            .join(SessionFacets, SessionFacets.session_id == SessionModel.id)
            .filter(SessionModel.started_at.isnot(None))
            .filter(SessionFacets.outcome.isnot(None))
        )
        if engineer_id:
            sr_q = sr_q.filter(SessionModel.engineer_id == engineer_id)
        elif team_id:
            sr_q = sr_q.join(Engineer).filter(Engineer.team_id == team_id)
        if start_date:
            sr_q = sr_q.filter(SessionModel.started_at >= start_date)
        if end_date:
            sr_q = sr_q.filter(SessionModel.started_at <= end_date)
        sr_q = sr_q.group_by(func.date(SessionModel.started_at))
        for d, successes, total in sr_q.all():
            if total > 0:
                success_rates[str(d)] = successes / total

    return [
        DailyStatsResponse(
            date=row.date,
            session_count=row.session_count,
            message_count=row.message_count,
            tool_call_count=row.tool_call_count,
            success_rate=success_rates.get(str(row.date)),
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


def get_engineer_analytics(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    sort_by: str = "total_sessions",
    limit: int = 50,
) -> EngineerAnalytics:
    """Per-engineer analytics: sessions, tokens, cost, success rate, top tools."""
    # Base query grouping by engineer
    q = db.query(
        SessionModel.engineer_id,
        Engineer.name,
        Engineer.email,
        Engineer.team_id,
        Engineer.avatar_url,
        Engineer.github_username,
        func.count(SessionModel.id).label("total_sessions"),
        func.coalesce(
            func.sum(SessionModel.input_tokens) + func.sum(SessionModel.output_tokens), 0
        ).label("total_tokens"),
        func.avg(SessionModel.duration_seconds).label("avg_duration"),
    ).join(Engineer, Engineer.id == SessionModel.engineer_id)
    if engineer_id:
        q = q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        q = q.filter(Engineer.team_id == team_id)
    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)

    q = q.group_by(
        SessionModel.engineer_id,
        Engineer.name,
        Engineer.email,
        Engineer.team_id,
        Engineer.avatar_url,
        Engineer.github_username,
    )

    # Sorting
    token_sum = func.sum(SessionModel.input_tokens) + func.sum(SessionModel.output_tokens)
    sort_map = {
        "total_sessions": func.count(SessionModel.id).desc(),
        "total_tokens": token_sum.desc(),
        "avg_duration": func.avg(SessionModel.duration_seconds).desc(),
        "name": Engineer.name.asc(),
    }
    q = q.order_by(sort_map.get(sort_by, func.count(SessionModel.id).desc()))
    rows = q.limit(limit).all()

    engineers: list[EngineerStats] = []
    for row in rows:
        eid = row.engineer_id

        # Per-engineer cost
        cost_q = (
            db.query(
                ModelUsage.model_name,
                func.sum(ModelUsage.input_tokens),
                func.sum(ModelUsage.output_tokens),
                func.sum(ModelUsage.cache_read_tokens),
                func.sum(ModelUsage.cache_creation_tokens),
            )
            .join(SessionModel)
            .filter(SessionModel.engineer_id == eid)
        )
        if start_date:
            cost_q = cost_q.filter(SessionModel.started_at >= start_date)
        if end_date:
            cost_q = cost_q.filter(SessionModel.started_at <= end_date)
        cost_q = cost_q.group_by(ModelUsage.model_name)
        eng_cost = 0.0
        for name, inp, out, cr, cc in cost_q.all():
            eng_cost += estimate_cost(name, inp or 0, out or 0, cr or 0, cc or 0)

        # Per-engineer success rate
        sr = _compute_success_rate(db, engineer_id=eid, start_date=start_date, end_date=end_date)

        # Top tools for this engineer
        tool_q = (
            db.query(ToolUsage.tool_name, func.sum(ToolUsage.call_count).label("tc"))
            .join(SessionModel)
            .filter(SessionModel.engineer_id == eid)
        )
        if start_date:
            tool_q = tool_q.filter(SessionModel.started_at >= start_date)
        if end_date:
            tool_q = tool_q.filter(SessionModel.started_at <= end_date)
        tool_q = tool_q.group_by(ToolUsage.tool_name).order_by(
            func.sum(ToolUsage.call_count).desc()
        )
        top_tools = [t[0] for t in tool_q.limit(5).all()]

        engineers.append(
            EngineerStats(
                engineer_id=eid,
                name=row.name,
                email=row.email,
                team_id=row.team_id,
                avatar_url=row.avatar_url,
                github_username=row.github_username,
                total_sessions=row.total_sessions,
                total_tokens=row.total_tokens,
                estimated_cost=eng_cost,
                success_rate=sr,
                avg_duration=float(row.avg_duration) if row.avg_duration else None,
                top_tools=top_tools,
            )
        )

    return EngineerAnalytics(engineers=engineers, total_count=len(engineers))


def get_project_analytics(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    sort_by: str = "total_sessions",
    limit: int = 50,
) -> ProjectAnalytics:
    """Per-project analytics: sessions, engineers, tokens, cost, outcomes, tools."""
    q = db.query(
        SessionModel.project_name,
        func.count(SessionModel.id).label("total_sessions"),
        func.count(func.distinct(SessionModel.engineer_id)).label("unique_engineers"),
        func.coalesce(
            func.sum(SessionModel.input_tokens) + func.sum(SessionModel.output_tokens), 0
        ).label("total_tokens"),
    ).filter(SessionModel.project_name.isnot(None))

    if engineer_id:
        q = q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        q = q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)

    q = q.group_by(SessionModel.project_name)

    token_sum = func.sum(SessionModel.input_tokens) + func.sum(SessionModel.output_tokens)
    sort_map = {
        "total_sessions": func.count(SessionModel.id).desc(),
        "total_tokens": token_sum.desc(),
        "unique_engineers": func.count(func.distinct(SessionModel.engineer_id)).desc(),
        "project_name": SessionModel.project_name.asc(),
    }
    q = q.order_by(sort_map.get(sort_by, func.count(SessionModel.id).desc()))
    rows = q.limit(limit).all()

    projects: list[ProjectStats] = []
    for row in rows:
        pname = row.project_name

        # Per-project cost
        cost_q = (
            db.query(
                ModelUsage.model_name,
                func.sum(ModelUsage.input_tokens),
                func.sum(ModelUsage.output_tokens),
                func.sum(ModelUsage.cache_read_tokens),
                func.sum(ModelUsage.cache_creation_tokens),
            )
            .join(SessionModel)
            .filter(SessionModel.project_name == pname)
        )
        if engineer_id:
            cost_q = cost_q.filter(SessionModel.engineer_id == engineer_id)
        elif team_id:
            cost_q = cost_q.join(Engineer).filter(Engineer.team_id == team_id)
        if start_date:
            cost_q = cost_q.filter(SessionModel.started_at >= start_date)
        if end_date:
            cost_q = cost_q.filter(SessionModel.started_at <= end_date)
        cost_q = cost_q.group_by(ModelUsage.model_name)
        proj_cost = 0.0
        for name, inp, out, cr, cc in cost_q.all():
            proj_cost += estimate_cost(name, inp or 0, out or 0, cr or 0, cc or 0)

        # Outcome distribution
        outcome_q = (
            db.query(SessionFacets.outcome)
            .join(SessionModel)
            .filter(SessionModel.project_name == pname)
            .filter(SessionFacets.outcome.isnot(None))
        )
        if engineer_id:
            outcome_q = outcome_q.filter(SessionModel.engineer_id == engineer_id)
        elif team_id:
            outcome_q = outcome_q.join(Engineer).filter(Engineer.team_id == team_id)
        if start_date:
            outcome_q = outcome_q.filter(SessionModel.started_at >= start_date)
        if end_date:
            outcome_q = outcome_q.filter(SessionModel.started_at <= end_date)
        outcome_dist: dict[str, int] = {}
        for (o,) in outcome_q.all():
            outcome_dist[o] = outcome_dist.get(o, 0) + 1

        # Top tools
        tool_q = (
            db.query(ToolUsage.tool_name, func.sum(ToolUsage.call_count).label("tc"))
            .join(SessionModel)
            .filter(SessionModel.project_name == pname)
        )
        if engineer_id:
            tool_q = tool_q.filter(SessionModel.engineer_id == engineer_id)
        elif team_id:
            tool_q = tool_q.join(Engineer).filter(Engineer.team_id == team_id)
        if start_date:
            tool_q = tool_q.filter(SessionModel.started_at >= start_date)
        if end_date:
            tool_q = tool_q.filter(SessionModel.started_at <= end_date)
        tool_q = tool_q.group_by(ToolUsage.tool_name).order_by(
            func.sum(ToolUsage.call_count).desc()
        )
        top_tools = [t[0] for t in tool_q.limit(5).all()]

        projects.append(
            ProjectStats(
                project_name=pname,
                total_sessions=row.total_sessions,
                unique_engineers=row.unique_engineers,
                total_tokens=row.total_tokens,
                estimated_cost=proj_cost,
                outcome_distribution=outcome_dist,
                top_tools=top_tools,
            )
        )

    return ProjectAnalytics(projects=projects, total_count=len(projects))


def get_activity_heatmap(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> ActivityHeatmap:
    """Build a 7x24 heatmap of session activity by day-of-week and hour."""
    q = _base_session_query(db, team_id, engineer_id, start_date, end_date)
    q = q.filter(SessionModel.started_at.isnot(None))

    sessions = q.with_entities(SessionModel.started_at).all()

    grid: dict[tuple[int, int], int] = {}
    for (started_at,) in sessions:
        if started_at:
            dow = started_at.weekday()  # 0=Monday
            hour = started_at.hour
            grid[(dow, hour)] = grid.get((dow, hour), 0) + 1

    cells = [
        HeatmapCell(day_of_week=dow, hour=hour, count=count)
        for (dow, hour), count in sorted(grid.items())
    ]
    max_count = max((c.count for c in cells), default=0)

    return ActivityHeatmap(cells=cells, max_count=max_count)
