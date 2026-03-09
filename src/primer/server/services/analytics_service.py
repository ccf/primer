from collections import Counter
from datetime import UTC, datetime
from datetime import date as date_type

from sqlalchemy import func
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.common.models import (
    Engineer,
    ModelUsage,
    SessionFacets,
    SessionMessage,
    ToolUsage,
)
from primer.common.models import (
    Session as SessionModel,
)
from primer.common.pricing import estimate_cost
from primer.common.schemas import (
    ActivityHeatmap,
    BenchmarkContext,
    BottleneckAnalytics,
    CostAnalytics,
    DailyCostEntry,
    DailyStatsResponse,
    EngineerAnalytics,
    EngineerBenchmark,
    EngineerBenchmarkResponse,
    EngineerStats,
    EngineerToolProfile,
    FrictionImpact,
    FrictionReport,
    FrictionTrend,
    HeatmapCell,
    ModelCostBreakdown,
    ModelRanking,
    OverviewStats,
    ProductivityMetrics,
    ProjectAnalytics,
    ProjectFriction,
    ProjectStats,
    ToolAdoptionAnalytics,
    ToolAdoptionEntry,
    ToolRanking,
    ToolTrendEntry,
)
from primer.common.source_capabilities import CAPABILITIES


def base_session_query(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    agent_type: str | None = None,
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
    if agent_type:
        q = q.filter(SessionModel.agent_type == agent_type)
    return q


def _agent_types_with_capability(capability_name: str) -> list[str]:
    return [
        agent_type
        for agent_type, capability in CAPABILITIES.items()
        if getattr(capability, capability_name)
    ]


def _filter_sessions_by_capability(query, capability_name: str):
    supported_agent_types = _agent_types_with_capability(capability_name)
    if not supported_agent_types:
        return query.filter(SessionModel.id.is_(None))
    return query.filter(SessionModel.agent_type.in_(supported_agent_types))


def _apply_session_scope_filters(
    query,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    if engineer_id:
        query = query.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        query = query.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        query = query.filter(SessionModel.started_at >= start_date)
    if end_date:
        query = query.filter(SessionModel.started_at <= end_date)
    return query


def _message_backed_stats(
    db: Session,
    *,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> tuple[int, int]:
    total_messages, session_count = _apply_session_scope_filters(
        _filter_sessions_by_capability(
            db.query(
                func.count(SessionMessage.id),
                func.count(func.distinct(SessionModel.id)),
            ).join(SessionModel, SessionMessage.session_id == SessionModel.id),
            "supports_transcript",
        ),
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    ).first() or (0, 0)
    return int(total_messages or 0), int(session_count or 0)


def _model_token_totals_by_group(
    db: Session,
    group_by_column,
    *,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, int]:
    rows = (
        _apply_session_scope_filters(
            _filter_sessions_by_capability(
                db.query(
                    group_by_column,
                    func.coalesce(func.sum(ModelUsage.input_tokens + ModelUsage.output_tokens), 0),
                ).join(SessionModel),
                "supports_model_usage",
            ),
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        )
        .group_by(group_by_column)
        .all()
    )
    return {
        group_key: int(total_tokens or 0)
        for group_key, total_tokens in rows
        if group_key is not None
    }


def _compute_success_rate(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> float | None:
    """Compute success rate from session facets."""
    facets_q = db.query(SessionFacets.outcome).join(SessionModel)
    facets_q = _filter_sessions_by_capability(facets_q, "supports_facets")
    if engineer_id:
        facets_q = facets_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        facets_q = facets_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        facets_q = facets_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        facets_q = facets_q.filter(SessionModel.started_at <= end_date)
    facets_q = facets_q.filter(SessionFacets.outcome.isnot(None))
    outcomes = [
        normalized
        for (outcome,) in facets_q.all()
        if (normalized := canonical_outcome(outcome)) is not None
    ]
    if not outcomes:
        return None
    return sum(1 for outcome in outcomes if is_success_outcome(outcome)) / len(outcomes)


def _build_overview(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> OverviewStats:
    """Internal helper that builds an OverviewStats without previous_period."""
    q = base_session_query(db, team_id, engineer_id, start_date, end_date)

    total_sessions = q.count()

    tool_agg = _apply_session_scope_filters(
        _filter_sessions_by_capability(
            db.query(func.coalesce(func.sum(ToolUsage.call_count), 0)).join(SessionModel),
            "supports_tool_calls",
        ),
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    ).first()
    model_agg = _apply_session_scope_filters(
        _filter_sessions_by_capability(
            db.query(
                func.coalesce(func.sum(ModelUsage.input_tokens), 0),
                func.coalesce(func.sum(ModelUsage.output_tokens), 0),
                func.coalesce(func.sum(ModelUsage.cache_read_tokens), 0),
            ).join(SessionModel),
            "supports_model_usage",
        ),
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    ).first()
    duration_agg = q.with_entities(func.avg(SessionModel.duration_seconds)).first()

    total_tool_calls = (tool_agg[0] or 0) if tool_agg else 0
    total_input_tokens = (model_agg[0] or 0) if model_agg else 0
    total_output_tokens = (model_agg[1] or 0) if model_agg else 0
    avg_duration = float(duration_agg[0]) if duration_agg and duration_agg[0] else None
    message_backed_total, message_backed_sessions = _message_backed_stats(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )
    total_messages = message_backed_total
    avg_messages = (
        message_backed_total / message_backed_sessions if message_backed_sessions > 0 else None
    )

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
    facets_q = _filter_sessions_by_capability(facets_q, "supports_facets")
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
        normalized_outcome = canonical_outcome(outcome)
        if normalized_outcome is None:
            continue
        outcome_counts[normalized_outcome] = outcome_counts.get(normalized_outcome, 0) + 1

    # Session type counts
    type_q = db.query(SessionFacets.session_type).join(SessionModel)
    type_q = _filter_sessions_by_capability(type_q, "supports_facets")
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
    # Guardrail: model-based metrics only participate for sources whose telemetry
    # explicitly supports model usage. Unsupported sources like Cursor must not
    # silently inflate token or cost aggregates with placeholder session fields.
    cost_q = db.query(
        ModelUsage.model_name,
        func.sum(ModelUsage.input_tokens),
        func.sum(ModelUsage.output_tokens),
        func.sum(ModelUsage.cache_read_tokens),
        func.sum(ModelUsage.cache_creation_tokens),
    ).join(SessionModel)
    cost_q = _filter_sessions_by_capability(cost_q, "supports_model_usage")
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

    # Agent type counts
    agent_q = q.filter(SessionModel.agent_type.isnot(None)).with_entities(SessionModel.agent_type)
    agent_type_counts: dict[str, int] = {}
    for (at,) in agent_q.all():
        agent_type_counts[at] = agent_type_counts.get(at, 0) + 1

    # Success rate
    success_rate = _compute_success_rate(db, team_id, engineer_id, start_date, end_date)

    # End reason counts
    er_q = q.filter(SessionModel.end_reason.isnot(None)).with_entities(SessionModel.end_reason)
    end_reason_counts: dict[str, int] = {}
    for (er,) in er_q.all():
        end_reason_counts[er] = end_reason_counts.get(er, 0) + 1

    # Cache hit rate from aggregated token sums
    total_cache_read = model_agg[2] or 0 if model_agg else 0
    total_input_for_cache = total_input_tokens
    cache_denom = total_cache_read + total_input_for_cache
    cache_hit_rate = round(total_cache_read / cache_denom, 3) if cache_denom > 0 else None

    # Avg health score
    from primer.server.services.session_insights_service import compute_session_health_score

    # Guardrail: health depends on facets-derived fields, so only sessions from
    # facet-capable sources with actual facet rows participate in the average.
    health_rows = db.query(
        SessionModel.duration_seconds,
        SessionFacets.outcome,
        SessionFacets.friction_counts,
        SessionFacets.user_satisfaction_counts,
        SessionFacets.primary_success,
    ).join(SessionFacets, SessionFacets.session_id == SessionModel.id)
    health_rows = _filter_sessions_by_capability(health_rows, "supports_facets")
    if engineer_id:
        health_rows = health_rows.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        health_rows = health_rows.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        health_rows = health_rows.filter(SessionModel.started_at >= start_date)
    if end_date:
        health_rows = health_rows.filter(SessionModel.started_at <= end_date)
    health_data = health_rows.all()

    avg_health_score = None
    if health_data:
        durations = [r.duration_seconds for r in health_data if r.duration_seconds is not None]
        if durations:
            sorted_dur = sorted(durations)
            mid = len(sorted_dur) // 2
            median_dur = (
                sorted_dur[mid]
                if len(sorted_dur) % 2 == 1
                else (sorted_dur[mid - 1] + sorted_dur[mid]) / 2
            )
        else:
            median_dur = None
        scores = [
            compute_session_health_score(
                outcome=r.outcome,
                friction_counts=r.friction_counts,
                duration_seconds=r.duration_seconds,
                median_duration=median_dur,
                satisfaction_counts=r.user_satisfaction_counts,
                primary_success=r.primary_success,
            )
            for r in health_data
        ]
        avg_health_score = round(sum(scores) / len(scores), 1) if scores else None

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
        end_reason_counts=end_reason_counts,
        cache_hit_rate=cache_hit_rate,
        avg_health_score=avg_health_score,
        agent_type_counts=agent_type_counts,
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
    message_counts: dict[str, int] = {}
    message_q = (
        _apply_session_scope_filters(
            _filter_sessions_by_capability(
                db.query(
                    func.date(SessionModel.started_at).label("date"),
                    func.count(SessionMessage.id).label("message_count"),
                ).join(SessionMessage, SessionMessage.session_id == SessionModel.id),
                "supports_transcript",
            ).filter(SessionModel.started_at.isnot(None)),
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        )
        .group_by(func.date(SessionModel.started_at))
        .order_by(func.date(SessionModel.started_at).desc())
    )
    for d, message_count in message_q.limit(days).all():
        message_counts[str(d)] = int(message_count or 0)
    tool_counts: dict[str, int] = {}
    tool_q = (
        _apply_session_scope_filters(
            _filter_sessions_by_capability(
                db.query(
                    func.date(SessionModel.started_at).label("date"),
                    func.coalesce(func.sum(ToolUsage.call_count), 0).label("tool_call_count"),
                ).join(ToolUsage, ToolUsage.session_id == SessionModel.id),
                "supports_tool_calls",
            ).filter(SessionModel.started_at.isnot(None)),
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        )
        .group_by(func.date(SessionModel.started_at))
        .order_by(func.date(SessionModel.started_at).desc())
    )
    for d, tool_call_count in tool_q.limit(days).all():
        tool_counts[str(d)] = int(tool_call_count or 0)

    # Compute per-day success rates from facets
    date_set = {row.date for row in rows}
    success_rates: dict[str, float | None] = {}
    if date_set:
        sr_q = (
            db.query(
                func.date(SessionModel.started_at).label("date"),
                SessionFacets.outcome,
            )
            .join(SessionFacets, SessionFacets.session_id == SessionModel.id)
            .filter(SessionModel.started_at.isnot(None))
            .filter(SessionFacets.outcome.isnot(None))
        )
        sr_q = _filter_sessions_by_capability(sr_q, "supports_facets")
        if engineer_id:
            sr_q = sr_q.filter(SessionModel.engineer_id == engineer_id)
        elif team_id:
            sr_q = sr_q.join(Engineer).filter(Engineer.team_id == team_id)
        if start_date:
            sr_q = sr_q.filter(SessionModel.started_at >= start_date)
        if end_date:
            sr_q = sr_q.filter(SessionModel.started_at <= end_date)
        daily_outcomes: dict[str, list[str]] = {}
        for d, outcome in sr_q.all():
            normalized_outcome = canonical_outcome(outcome)
            if normalized_outcome is None:
                continue
            date_key = str(d)
            daily_outcomes.setdefault(date_key, []).append(normalized_outcome)
        for date_key, outcomes in daily_outcomes.items():
            if outcomes:
                success_rates[date_key] = sum(
                    1 for outcome in outcomes if is_success_outcome(outcome)
                ) / len(outcomes)

    return [
        DailyStatsResponse(
            date=row.date,
            session_count=row.session_count,
            message_count=message_counts.get(str(row.date), 0),
            tool_call_count=tool_counts.get(str(row.date), 0),
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
    facets_q = _filter_sessions_by_capability(facets_q, "supports_facets")
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
    q = _filter_sessions_by_capability(q, "supports_tool_calls")
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
    q = _filter_sessions_by_capability(q, "supports_model_usage")
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
    q = _filter_sessions_by_capability(q, "supports_model_usage")
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
    daily_q = _filter_sessions_by_capability(daily_q, "supports_model_usage")
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
    token_totals_by_engineer = _model_token_totals_by_group(
        db,
        SessionModel.engineer_id,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )

    # Base query grouping by engineer
    q = db.query(
        SessionModel.engineer_id,
        Engineer.name,
        Engineer.email,
        Engineer.team_id,
        Engineer.avatar_url,
        Engineer.github_username,
        func.count(SessionModel.id).label("total_sessions"),
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
    sort_map = {
        "total_sessions": func.count(SessionModel.id).desc(),
        "avg_duration": func.avg(SessionModel.duration_seconds).desc(),
        "name": Engineer.name.asc(),
    }
    # estimated_cost and success_rate are computed post-query, so skip SQL limit
    python_sort = sort_by in ("estimated_cost", "success_rate", "total_tokens")
    q = q.order_by(sort_map.get(sort_by, func.count(SessionModel.id).desc()))
    rows = q.all() if python_sort else q.limit(limit).all()

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
        cost_q = _filter_sessions_by_capability(cost_q, "supports_model_usage")
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
        tool_q = _filter_sessions_by_capability(tool_q, "supports_tool_calls")
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
                total_tokens=token_totals_by_engineer.get(eid, 0),
                estimated_cost=eng_cost,
                success_rate=sr,
                avg_duration=float(row.avg_duration) if row.avg_duration else None,
                top_tools=top_tools,
            )
        )

    # Post-query sorting for computed fields
    if sort_by == "estimated_cost":
        engineers.sort(key=lambda e: e.estimated_cost or 0, reverse=True)
        engineers = engineers[:limit]
    elif sort_by == "success_rate":
        engineers.sort(key=lambda e: e.success_rate or 0, reverse=True)
        engineers = engineers[:limit]
    elif sort_by == "total_tokens":
        engineers.sort(key=lambda e: e.total_tokens, reverse=True)
        engineers = engineers[:limit]

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
    token_totals_by_project = _model_token_totals_by_group(
        db,
        SessionModel.project_name,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )

    q = db.query(
        SessionModel.project_name,
        func.count(SessionModel.id).label("total_sessions"),
        func.count(func.distinct(SessionModel.engineer_id)).label("unique_engineers"),
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

    sort_map = {
        "total_sessions": func.count(SessionModel.id).desc(),
        "unique_engineers": func.count(func.distinct(SessionModel.engineer_id)).desc(),
        "project_name": SessionModel.project_name.asc(),
    }
    q = q.order_by(sort_map.get(sort_by, func.count(SessionModel.id).desc()))
    rows = q.all() if sort_by == "total_tokens" else q.limit(limit).all()

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
        cost_q = _filter_sessions_by_capability(cost_q, "supports_model_usage")
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
        outcome_q = _filter_sessions_by_capability(outcome_q, "supports_facets")
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
            normalized_outcome = canonical_outcome(o)
            if normalized_outcome is None:
                continue
            outcome_dist[normalized_outcome] = outcome_dist.get(normalized_outcome, 0) + 1

        # Top tools
        tool_q = (
            db.query(ToolUsage.tool_name, func.sum(ToolUsage.call_count).label("tc"))
            .join(SessionModel)
            .filter(SessionModel.project_name == pname)
        )
        tool_q = _filter_sessions_by_capability(tool_q, "supports_tool_calls")
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
                total_tokens=token_totals_by_project.get(pname, 0),
                estimated_cost=proj_cost,
                outcome_distribution=outcome_dist,
                top_tools=top_tools,
            )
        )

    if sort_by == "total_tokens":
        projects.sort(key=lambda p: p.total_tokens, reverse=True)
        projects = projects[:limit]

    return ProjectAnalytics(projects=projects, total_count=len(projects))


def get_activity_heatmap(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> ActivityHeatmap:
    """Build a 7x24 heatmap of session activity by day-of-week and hour."""
    q = base_session_query(db, team_id, engineer_id, start_date, end_date)
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


def get_productivity_metrics(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> ProductivityMetrics:
    """Compute ROI / productivity metrics."""
    q = base_session_query(db, team_id, engineer_id, start_date, end_date)

    # Session counts and total duration
    agg = q.with_entities(
        func.count(SessionModel.id),
        func.sum(SessionModel.duration_seconds),
    ).first()
    total_sessions = agg[0] or 0
    total_duration = float(agg[1]) if agg[1] else 0.0

    # Count adopters (active engineers with sessions in range only)
    active_ids = {
        e.id
        for e in db.query(Engineer.id)
        .filter(Engineer.is_active == True)  # noqa: E712
        .all()
    }
    session_engineer_ids = {
        row[0] for row in q.with_entities(SessionModel.engineer_id).distinct().all()
    }
    engineers_with_sessions = len(session_engineer_ids & active_ids)

    # Total active engineers in scope
    eng_q = db.query(func.count(Engineer.id)).filter(Engineer.is_active == True)  # noqa: E712
    if engineer_id:
        eng_q = eng_q.filter(Engineer.id == engineer_id)
    elif team_id:
        eng_q = eng_q.filter(Engineer.team_id == team_id)
    total_active_engineers = eng_q.scalar() or 0

    # Compute total cost
    cost_q = db.query(
        ModelUsage.model_name,
        func.sum(ModelUsage.input_tokens),
        func.sum(ModelUsage.output_tokens),
        func.sum(ModelUsage.cache_read_tokens),
        func.sum(ModelUsage.cache_creation_tokens),
    ).join(SessionModel)
    cost_q = _filter_sessions_by_capability(cost_q, "supports_model_usage")
    if engineer_id:
        cost_q = cost_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        cost_q = cost_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        cost_q = cost_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        cost_q = cost_q.filter(SessionModel.started_at <= end_date)
    cost_q = cost_q.group_by(ModelUsage.model_name)
    total_cost = 0.0
    for name, inp, out, cr, cc in cost_q.all():
        total_cost += estimate_cost(name, inp or 0, out or 0, cr or 0, cc or 0)

    # Guardrail: per-session cost averages only include sessions from sources
    # that can actually provide model telemetry, otherwise partial sources like
    # Cursor dilute the metric with unsupported zero-cost participation.
    cost_session_q = db.query(func.count(func.distinct(SessionModel.id))).join(ModelUsage)
    cost_session_q = _filter_sessions_by_capability(cost_session_q, "supports_model_usage")
    if engineer_id:
        cost_session_q = cost_session_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        cost_session_q = cost_session_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        cost_session_q = cost_session_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        cost_session_q = cost_session_q.filter(SessionModel.started_at <= end_date)
    cost_session_count = cost_session_q.scalar() or 0

    # Guardrail: cost-per-success should only count successful sessions that
    # also contributed measured model telemetry. Otherwise facet-capable but
    # cost-unmeasured sessions can dilute the denominator and understate cost.
    success_q = (
        db.query(SessionFacets.outcome).join(SessionModel).filter(SessionFacets.outcome.isnot(None))
    )
    success_q = _filter_sessions_by_capability(success_q, "supports_facets")
    success_q = _filter_sessions_by_capability(success_q, "supports_model_usage")
    success_q = success_q.filter(SessionModel.id.in_(db.query(ModelUsage.session_id).distinct()))
    if engineer_id:
        success_q = success_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        success_q = success_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        success_q = success_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        success_q = success_q.filter(SessionModel.started_at <= end_date)
    success_count = sum(1 for (outcome,) in success_q.all() if is_success_outcome(outcome))

    # Compute days in range
    if start_date and end_date:
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=UTC)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=UTC)
        days_in_range = max((end_date - start_date).days, 1)
    else:
        # Use date range from actual sessions
        date_range = q.with_entities(
            func.min(SessionModel.started_at), func.max(SessionModel.started_at)
        ).first()
        if date_range[0] and date_range[1]:
            s, e = date_range[0], date_range[1]
            if hasattr(s, "tzinfo") and s.tzinfo is None:
                s = s.replace(tzinfo=UTC)
            if hasattr(e, "tzinfo") and e.tzinfo is None:
                e = e.replace(tzinfo=UTC)
            days_in_range = max((e - s).days, 1)
        else:
            days_in_range = 1

    active_eng_count = max(total_active_engineers, 1)
    sessions_per_engineer_per_day = total_sessions / (active_eng_count * days_in_range)

    avg_cost_per_session = total_cost / cost_session_count if cost_session_count > 0 else None
    cost_per_success = total_cost / success_count if success_count > 0 else None

    # Time saved estimation
    multiplier = settings.productivity_time_multiplier
    hourly_rate = settings.productivity_hourly_rate
    estimated_time_saved = (
        (total_duration / 3600) * (multiplier - 1) if total_duration > 0 else None
    )
    estimated_value = estimated_time_saved * hourly_rate if estimated_time_saved else None

    adoption_rate = (
        min((engineers_with_sessions / total_active_engineers) * 100, 100.0)
        if total_active_engineers > 0
        else 0.0
    )

    # Power users: engineers with > 2x average session count
    avg_sessions = total_sessions / engineers_with_sessions if engineers_with_sessions > 0 else 0
    power_threshold = avg_sessions * 2
    power_users = 0
    if power_threshold > 0:
        per_eng = (
            q.with_entities(SessionModel.engineer_id, func.count(SessionModel.id).label("cnt"))
            .group_by(SessionModel.engineer_id)
            .all()
        )
        power_users = sum(1 for _, cnt in per_eng if cnt > power_threshold)

    roi_ratio = (
        estimated_value / total_cost if total_cost > 0 and estimated_value is not None else None
    )

    return ProductivityMetrics(
        sessions_per_engineer_per_day=round(sessions_per_engineer_per_day, 3),
        avg_cost_per_session=(
            round(avg_cost_per_session, 4) if avg_cost_per_session is not None else None
        ),
        cost_per_successful_outcome=(
            round(cost_per_success, 4) if cost_per_success is not None else None
        ),
        estimated_time_saved_hours=(
            round(estimated_time_saved, 1) if estimated_time_saved is not None else None
        ),
        estimated_value_created=(
            round(estimated_value, 2) if estimated_value is not None else None
        ),
        adoption_rate=round(adoption_rate, 1),
        power_users=power_users,
        total_engineers_in_scope=total_active_engineers,
        total_cost=round(total_cost, 4),
        roi_ratio=round(roi_ratio, 2) if roi_ratio is not None else None,
    )


def get_engineer_benchmarks(
    db: Session,
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> EngineerBenchmarkResponse:
    """Compute per-engineer benchmarks with percentiles and vs-team-avg."""
    token_totals_by_engineer = _model_token_totals_by_group(
        db,
        SessionModel.engineer_id,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
    )

    # Grouped query by engineer
    q = db.query(
        SessionModel.engineer_id,
        Engineer.name,
        Engineer.display_name,
        Engineer.avatar_url,
        func.count(SessionModel.id).label("total_sessions"),
        func.avg(SessionModel.duration_seconds).label("avg_duration"),
    ).join(Engineer, Engineer.id == SessionModel.engineer_id)

    if team_id:
        q = q.filter(Engineer.team_id == team_id)
    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)

    q = q.group_by(
        SessionModel.engineer_id,
        Engineer.name,
        Engineer.display_name,
        Engineer.avatar_url,
    )
    rows = q.all()

    if not rows:
        return EngineerBenchmarkResponse(
            engineers=[],
            benchmark=BenchmarkContext(
                team_avg_sessions=0,
                team_avg_tokens=0,
                team_avg_cost=0,
                team_avg_success_rate=0,
                team_avg_duration=None,
            ),
        )

    # Per-engineer cost and success rate
    eng_data: list[dict] = []
    for row in rows:
        eid = row.engineer_id

        # Cost
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
        cost_q = _filter_sessions_by_capability(cost_q, "supports_model_usage")
        if start_date:
            cost_q = cost_q.filter(SessionModel.started_at >= start_date)
        if end_date:
            cost_q = cost_q.filter(SessionModel.started_at <= end_date)
        cost_q = cost_q.group_by(ModelUsage.model_name)
        eng_cost = sum(
            estimate_cost(name, inp or 0, out or 0, cr or 0, cc or 0)
            for name, inp, out, cr, cc in cost_q.all()
        )

        # Success rate
        sr = _compute_success_rate(db, engineer_id=eid, start_date=start_date, end_date=end_date)

        eng_data.append(
            {
                "engineer_id": eid,
                "name": row.name,
                "display_name": row.display_name,
                "avatar_url": row.avatar_url,
                "total_sessions": row.total_sessions,
                "total_tokens": token_totals_by_engineer.get(eid, 0),
                "estimated_cost": eng_cost,
                "success_rate": sr,
                "avg_duration": float(row.avg_duration) if row.avg_duration else None,
            }
        )

    count = len(eng_data)

    # Team averages
    avg_sessions = sum(e["total_sessions"] for e in eng_data) / count
    avg_tokens = sum(e["total_tokens"] for e in eng_data) / count
    avg_cost = sum(e["estimated_cost"] for e in eng_data) / count
    sr_vals = [e["success_rate"] for e in eng_data if e["success_rate"] is not None]
    avg_sr = sum(sr_vals) / len(sr_vals) if sr_vals else 0
    dur_vals = [e["avg_duration"] for e in eng_data if e["avg_duration"] is not None]
    avg_dur = sum(dur_vals) / len(dur_vals) if dur_vals else None

    # Percentile computation: sort, then rank / count * 100
    sessions_sorted = sorted(e["total_sessions"] for e in eng_data)
    tokens_sorted = sorted(e["total_tokens"] for e in eng_data)
    cost_sorted = sorted(e["estimated_cost"] for e in eng_data)

    def _percentile(sorted_vals: list, value) -> int:
        rank = 0
        for v in sorted_vals:
            if v <= value:
                rank += 1
            else:
                break
        return round((rank / len(sorted_vals)) * 100) if sorted_vals else 0

    engineers: list[EngineerBenchmark] = []
    for e in eng_data:
        vs_team: dict[str, float] = {}
        if avg_sessions > 0:
            vs_team["sessions"] = round(
                ((e["total_sessions"] - avg_sessions) / avg_sessions) * 100, 1
            )
        if avg_tokens > 0:
            vs_team["tokens"] = round(((e["total_tokens"] - avg_tokens) / avg_tokens) * 100, 1)
        if avg_cost > 0:
            vs_team["cost"] = round(((e["estimated_cost"] - avg_cost) / avg_cost) * 100, 1)

        engineers.append(
            EngineerBenchmark(
                engineer_id=e["engineer_id"],
                name=e["name"],
                display_name=e["display_name"],
                avatar_url=e["avatar_url"],
                total_sessions=e["total_sessions"],
                total_tokens=e["total_tokens"],
                estimated_cost=round(e["estimated_cost"], 4),
                success_rate=round(e["success_rate"], 3) if e["success_rate"] is not None else None,
                avg_duration=round(e["avg_duration"], 1) if e["avg_duration"] is not None else None,
                percentile_sessions=_percentile(sessions_sorted, e["total_sessions"]),
                percentile_tokens=_percentile(tokens_sorted, e["total_tokens"]),
                percentile_cost=_percentile(cost_sorted, e["estimated_cost"]),
                vs_team_avg=vs_team,
            )
        )

    # Sort by sessions descending
    engineers.sort(key=lambda e: e.total_sessions, reverse=True)

    return EngineerBenchmarkResponse(
        engineers=engineers,
        benchmark=BenchmarkContext(
            team_avg_sessions=round(avg_sessions, 1),
            team_avg_tokens=round(avg_tokens, 0),
            team_avg_cost=round(avg_cost, 4),
            team_avg_success_rate=round(avg_sr, 3),
            team_avg_duration=round(avg_dur, 1) if avg_dur is not None else None,
        ),
    )


def get_bottleneck_analytics(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> BottleneckAnalytics:
    """Analyse friction patterns across sessions for bottleneck detection."""
    # Fetch sessions with their facets (inner join so only sessions with
    # facets data are included in friction rate denominators)
    q = db.query(SessionModel, SessionFacets).join(
        SessionFacets, SessionFacets.session_id == SessionModel.id
    )
    q = _filter_sessions_by_capability(q, "supports_facets")
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

    rows = q.all()

    total_sessions = len(rows)
    if total_sessions == 0:
        return BottleneckAnalytics(
            friction_impacts=[],
            project_friction=[],
            friction_trends=[],
            total_sessions_analyzed=0,
            sessions_with_any_friction=0,
            overall_friction_rate=0.0,
        )

    # --- Friction Impact Analysis ---
    # Track per friction type: occurrences, sessions, outcomes, details
    type_occurrences: Counter[str] = Counter()
    type_sessions: dict[str, set[str]] = {}
    type_details: dict[str, list[str]] = {}
    # Track outcomes for sessions with/without each friction type
    type_outcomes_with: dict[str, list[str]] = {}

    sessions_with_friction: set[str] = set()
    # Map session_id → outcome for computing per-type baselines
    session_outcomes: dict[str, str] = {}

    # --- Project Friction ---
    project_sessions: dict[str, int] = {}
    project_friction_sessions: dict[str, set[str]] = {}
    project_friction_counts: dict[str, Counter[str]] = {}

    # --- Friction Trends ---
    daily_friction: dict[str, int] = {}
    daily_friction_sessions: dict[str, set[str]] = {}
    daily_total_sessions: dict[str, set[str]] = {}

    for session, facets in rows:
        sid = session.id
        outcome = canonical_outcome(facets.outcome) if facets else None

        date_key = session.started_at.strftime("%Y-%m-%d") if session.started_at else None
        project = session.project_name or "unknown"

        # Track project sessions
        project_sessions[project] = project_sessions.get(project, 0) + 1

        # Track daily total sessions
        if date_key:
            if date_key not in daily_total_sessions:
                daily_total_sessions[date_key] = set()
            daily_total_sessions[date_key].add(sid)

        friction_counts = facets.friction_counts if facets else None
        if friction_counts:
            has_friction = False
            detail_assigned = False
            for friction_type, count in friction_counts.items():
                if count > 0:
                    has_friction = True
                    type_occurrences[friction_type] += count

                    if friction_type not in type_sessions:
                        type_sessions[friction_type] = set()
                    type_sessions[friction_type].add(sid)

                    if outcome:
                        if friction_type not in type_outcomes_with:
                            type_outcomes_with[friction_type] = []
                        type_outcomes_with[friction_type].append(outcome)

                    # Only attribute friction_detail to one type per session
                    # since the detail is session-level, not type-specific
                    if facets.friction_detail and not detail_assigned:
                        if friction_type not in type_details:
                            type_details[friction_type] = []
                        if len(type_details[friction_type]) < 10:
                            type_details[friction_type].append(facets.friction_detail)
                            detail_assigned = True

                    # Project friction tracking
                    if project not in project_friction_counts:
                        project_friction_counts[project] = Counter()
                    project_friction_counts[project][friction_type] += count

                    # Daily friction tracking
                    if date_key:
                        daily_friction[date_key] = daily_friction.get(date_key, 0) + count

            if has_friction:
                sessions_with_friction.add(sid)

                if project not in project_friction_sessions:
                    project_friction_sessions[project] = set()
                project_friction_sessions[project].add(sid)

                if date_key:
                    if date_key not in daily_friction_sessions:
                        daily_friction_sessions[date_key] = set()
                    daily_friction_sessions[date_key].add(sid)
        # Track all session outcomes for per-type baseline calculation
        if outcome:
            session_outcomes[sid] = outcome

    # Build friction impacts
    def _success_rate(outcomes: list[str]) -> float | None:
        if not outcomes:
            return None
        return sum(1 for outcome in outcomes if is_success_outcome(outcome)) / len(outcomes)

    all_session_ids = set(session_outcomes.keys())

    friction_impacts: list[FrictionImpact] = []
    for ft, occ_count in type_occurrences.most_common():
        sr_with = _success_rate(type_outcomes_with.get(ft, []))
        # Per-type baseline: success rate of sessions WITHOUT this specific type
        sessions_without_ft = all_session_ids - type_sessions.get(ft, set())
        outcomes_without_ft = [session_outcomes[s] for s in sessions_without_ft]
        sr_without = _success_rate(outcomes_without_ft)
        impact = None
        if sr_with is not None and sr_without is not None:
            impact = round(sr_without - sr_with, 3)

        friction_impacts.append(
            FrictionImpact(
                friction_type=ft,
                occurrence_count=occ_count,
                sessions_affected=len(type_sessions.get(ft, set())),
                success_rate_with=round(sr_with, 3) if sr_with is not None else None,
                success_rate_without=round(sr_without, 3) if sr_without is not None else None,
                impact_score=impact,
                sample_details=type_details.get(ft, []),
            )
        )

    # Build project friction
    project_friction_list: list[ProjectFriction] = []
    for proj, total in project_sessions.items():
        friction_sids = project_friction_sessions.get(proj, set())
        friction_count = len(friction_sids)
        proj_counter = project_friction_counts.get(proj, Counter())
        top_types = [ft for ft, _ in proj_counter.most_common(3)]
        total_fc = sum(proj_counter.values())

        project_friction_list.append(
            ProjectFriction(
                project_name=proj,
                total_sessions=total,
                sessions_with_friction=friction_count,
                friction_rate=round(friction_count / total, 3) if total > 0 else 0.0,
                top_friction_types=top_types,
                total_friction_count=total_fc,
            )
        )
    project_friction_list.sort(key=lambda p: p.total_friction_count, reverse=True)

    # Build friction trends
    all_dates = sorted(set(daily_total_sessions.keys()))
    friction_trends: list[FrictionTrend] = []
    for d in all_dates:
        parts = d.split("-")
        friction_trends.append(
            FrictionTrend(
                date=date_type(int(parts[0]), int(parts[1]), int(parts[2])),
                total_friction_count=daily_friction.get(d, 0),
                sessions_with_friction=len(daily_friction_sessions.get(d, set())),
                total_sessions=len(daily_total_sessions.get(d, set())),
            )
        )

    sessions_with_count = len(sessions_with_friction)
    return BottleneckAnalytics(
        friction_impacts=friction_impacts,
        project_friction=project_friction_list,
        friction_trends=friction_trends,
        total_sessions_analyzed=total_sessions,
        sessions_with_any_friction=sessions_with_count,
        overall_friction_rate=round(sessions_with_count / total_sessions, 3)
        if total_sessions > 0
        else 0.0,
    )


def get_tool_adoption_analytics(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 20,
) -> ToolAdoptionAnalytics:
    """Compute tool adoption analytics: per-tool adoption, trends, engineer profiles."""

    # --- Total engineers in scope ---
    eng_q = db.query(func.count(func.distinct(SessionModel.engineer_id)))
    eng_q = _filter_sessions_by_capability(eng_q, "supports_tool_calls")
    if engineer_id:
        eng_q = eng_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        eng_q = eng_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        eng_q = eng_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        eng_q = eng_q.filter(SessionModel.started_at <= end_date)
    total_engineers = eng_q.scalar() or 0

    # --- 1. Tool Adoption ---
    tool_q = db.query(
        ToolUsage.tool_name,
        func.sum(ToolUsage.call_count).label("total_calls"),
        func.count(func.distinct(ToolUsage.session_id)).label("session_count"),
        func.count(func.distinct(SessionModel.engineer_id)).label("engineer_count"),
    ).join(SessionModel)
    tool_q = _filter_sessions_by_capability(tool_q, "supports_tool_calls")
    if engineer_id:
        tool_q = tool_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        tool_q = tool_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        tool_q = tool_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        tool_q = tool_q.filter(SessionModel.started_at <= end_date)
    tool_q = tool_q.group_by(ToolUsage.tool_name).order_by(func.sum(ToolUsage.call_count).desc())
    tool_rows = tool_q.limit(limit).all()

    tool_adoption: list[ToolAdoptionEntry] = []
    for name, total_calls, session_count, eng_count in tool_rows:
        adoption_rate = (eng_count / total_engineers * 100) if total_engineers > 0 else 0.0
        avg_per_session = total_calls / session_count if session_count > 0 else 0.0
        tool_adoption.append(
            ToolAdoptionEntry(
                tool_name=name,
                total_calls=total_calls,
                session_count=session_count,
                engineer_count=eng_count,
                adoption_rate=round(adoption_rate, 1),
                avg_calls_per_session=round(avg_per_session, 1),
            )
        )

    # --- 2. Tool Trends (top 5 tools, daily) ---
    top_5_names = [t.tool_name for t in tool_adoption[:5]]
    tool_trends: list[ToolTrendEntry] = []
    if top_5_names:
        trend_q = (
            db.query(
                func.date(SessionModel.started_at).label("date"),
                ToolUsage.tool_name,
                func.sum(ToolUsage.call_count).label("call_count"),
                func.count(func.distinct(ToolUsage.session_id)).label("session_count"),
            )
            .join(SessionModel)
            .filter(
                ToolUsage.tool_name.in_(top_5_names),
                SessionModel.started_at.isnot(None),
            )
        )
        trend_q = _filter_sessions_by_capability(trend_q, "supports_tool_calls")
        if engineer_id:
            trend_q = trend_q.filter(SessionModel.engineer_id == engineer_id)
        elif team_id:
            trend_q = trend_q.join(Engineer).filter(Engineer.team_id == team_id)
        if start_date:
            trend_q = trend_q.filter(SessionModel.started_at >= start_date)
        if end_date:
            trend_q = trend_q.filter(SessionModel.started_at <= end_date)
        trend_q = trend_q.group_by(
            func.date(SessionModel.started_at), ToolUsage.tool_name
        ).order_by(func.date(SessionModel.started_at))

        for d, name, calls, sc in trend_q.all():
            tool_trends.append(
                ToolTrendEntry(date=d, tool_name=name, call_count=calls, session_count=sc)
            )

    # --- 3. Engineer Profiles ---
    prof_q = (
        db.query(
            SessionModel.engineer_id,
            Engineer.name,
            func.count(func.distinct(ToolUsage.tool_name)).label("tools_used"),
            func.sum(ToolUsage.call_count).label("total_tool_calls"),
        )
        .join(ToolUsage, ToolUsage.session_id == SessionModel.id)
        .join(Engineer, Engineer.id == SessionModel.engineer_id)
    )
    prof_q = _filter_sessions_by_capability(prof_q, "supports_tool_calls")
    if engineer_id:
        prof_q = prof_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        prof_q = prof_q.filter(Engineer.team_id == team_id)
    if start_date:
        prof_q = prof_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        prof_q = prof_q.filter(SessionModel.started_at <= end_date)
    prof_q = prof_q.group_by(SessionModel.engineer_id, Engineer.name).order_by(
        func.count(func.distinct(ToolUsage.tool_name)).desc()
    )
    prof_rows = prof_q.limit(50).all()

    engineer_profiles: list[EngineerToolProfile] = []
    for eid, ename, tools_used, total_calls in prof_rows:
        # Top 5 tools for this engineer
        top_q = (
            db.query(ToolUsage.tool_name, func.sum(ToolUsage.call_count).label("tc"))
            .join(SessionModel)
            .filter(SessionModel.engineer_id == eid)
        )
        top_q = _filter_sessions_by_capability(top_q, "supports_tool_calls")
        if start_date:
            top_q = top_q.filter(SessionModel.started_at >= start_date)
        if end_date:
            top_q = top_q.filter(SessionModel.started_at <= end_date)
        top_q = top_q.group_by(ToolUsage.tool_name).order_by(func.sum(ToolUsage.call_count).desc())
        top_tools = [t[0] for t in top_q.limit(5).all()]

        engineer_profiles.append(
            EngineerToolProfile(
                engineer_id=eid,
                name=ename,
                tools_used=tools_used,
                total_tool_calls=total_calls,
                top_tools=top_tools,
            )
        )

    # --- Aggregate stats ---
    # Separate count query so total_tools_discovered isn't bounded by `limit`
    total_tools_q = db.query(func.count(func.distinct(ToolUsage.tool_name))).join(SessionModel)
    total_tools_q = _filter_sessions_by_capability(total_tools_q, "supports_tool_calls")
    if engineer_id:
        total_tools_q = total_tools_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        total_tools_q = total_tools_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        total_tools_q = total_tools_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        total_tools_q = total_tools_q.filter(SessionModel.started_at <= end_date)
    total_tools_discovered = total_tools_q.scalar() or 0

    # Avg tools per engineer from all engineers (not just top-50 profiles)
    tools_per_eng_q = db.query(
        func.count(func.distinct(ToolUsage.tool_name)).label("tool_count"),
    ).join(SessionModel)
    tools_per_eng_q = _filter_sessions_by_capability(tools_per_eng_q, "supports_tool_calls")
    if engineer_id:
        tools_per_eng_q = tools_per_eng_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        tools_per_eng_q = tools_per_eng_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        tools_per_eng_q = tools_per_eng_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        tools_per_eng_q = tools_per_eng_q.filter(SessionModel.started_at <= end_date)
    tools_per_eng_sub = tools_per_eng_q.group_by(SessionModel.engineer_id).subquery()
    avg_tools_val = db.query(func.avg(tools_per_eng_sub.c.tool_count)).scalar()
    avg_tools = float(avg_tools_val) if avg_tools_val else 0.0

    return ToolAdoptionAnalytics(
        tool_adoption=tool_adoption,
        tool_trends=tool_trends,
        engineer_profiles=engineer_profiles,
        total_engineers=total_engineers,
        total_tools_discovered=total_tools_discovered,
        avg_tools_per_engineer=round(avg_tools, 1),
    )
