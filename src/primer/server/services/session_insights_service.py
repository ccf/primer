from collections import Counter
from datetime import date as date_type

from sqlalchemy import func
from sqlalchemy.orm import Session

from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.common.models import (
    ModelUsage,
    SessionFacets,
)
from primer.common.models import (
    Session as SessionModel,
)
from primer.common.pricing import estimate_cost
from primer.common.schemas import (
    CacheEfficiencyMetrics,
    DailyCacheEntry,
    DailyHealthEntry,
    DailySatisfaction,
    EndReasonBreakdown,
    FrictionCluster,
    GoalAnalytics,
    GoalCategoryBreakdown,
    GoalTypeBreakdown,
    PermissionModeAnalysis,
    PrimarySuccessAnalysis,
    SatisfactionSummary,
    SessionHealthDistribution,
    SessionInsightsResponse,
)
from primer.server.services.analytics_service import base_session_query

_PRIMARY_SUCCESS_BUCKETS = {
    "full": "full",
    "partial": "partial",
    "correct_code_edits": "full",
    "multi_file_changes": "full",
    "good_debugging": "full",
    "none": "none",
    "failure": "none",
}


def _primary_success_bucket(primary_success: str | None) -> str:
    """Map legacy and category-style primary_success labels into stable buckets."""
    if primary_success is None:
        return "unknown"
    return _PRIMARY_SUCCESS_BUCKETS.get(primary_success, "unknown")


def _primary_success_health_modifier(primary_success: str | None) -> float:
    """Return the health-score modifier for primary_success."""
    if primary_success is None:
        return 0.0

    normalized_primary_success = primary_success.strip()
    if not normalized_primary_success:
        return 0.0
    if normalized_primary_success in {"none", "failure"}:
        return -5.0
    return 5.0


def compute_session_health_score(
    outcome: str | None,
    friction_counts: dict | None,
    duration_seconds: float | None,
    median_duration: float | None,
    satisfaction_counts: dict | None,
    primary_success: str | None,
) -> float:
    """Compute a 0-100 health score for a single session."""
    score = 100.0
    normalized_outcome = canonical_outcome(outcome)

    # Outcome penalty
    if normalized_outcome == "success":
        pass
    elif normalized_outcome == "partial":
        score -= 20
    elif normalized_outcome == "failure":
        score -= 40
    elif normalized_outcome is None:
        score -= 10

    # Friction penalty
    if friction_counts:
        friction_types = sum(1 for v in friction_counts.values() if v > 0)
        score -= min(friction_types * 10, 30)

    # Duration penalty
    if duration_seconds is not None and median_duration and median_duration > 0:
        ratio = duration_seconds / median_duration
        if ratio > 2.0:
            score -= 10
        elif ratio > 1.5:
            score -= 5

    # Satisfaction bonus/penalty
    if satisfaction_counts:
        satisfied = satisfaction_counts.get("satisfied", 0)
        dissatisfied = satisfaction_counts.get("dissatisfied", 0)
        total = satisfied + dissatisfied + satisfaction_counts.get("neutral", 0)
        if total > 0:
            net_ratio = (satisfied - dissatisfied) / total
            score += max(min(net_ratio * 15, 5), -15)

    # Primary success modifier
    score += _primary_success_health_modifier(primary_success)

    return max(0.0, min(100.0, score))


def _compute_end_reason_breakdown(
    db: Session,
    session_ids_q,
) -> list[EndReasonBreakdown]:
    """Group sessions by end_reason with counts, avg duration, success rate."""
    rows = (
        db.query(
            SessionModel.end_reason,
            func.count(SessionModel.id).label("cnt"),
            func.avg(SessionModel.duration_seconds).label("avg_dur"),
        )
        .filter(SessionModel.id.in_(session_ids_q))
        .filter(SessionModel.end_reason.isnot(None))
        .group_by(SessionModel.end_reason)
        .order_by(func.count(SessionModel.id).desc())
        .all()
    )

    results = []
    for end_reason, count, avg_dur in rows:
        outcome_rows = (
            db.query(SessionFacets.outcome)
            .join(SessionModel, SessionModel.id == SessionFacets.session_id)
            .filter(SessionModel.id.in_(session_ids_q))
            .filter(SessionModel.end_reason == end_reason)
            .filter(SessionFacets.outcome.isnot(None))
            .all()
        )
        outcomes = [
            normalized
            for (outcome,) in outcome_rows
            if (normalized := canonical_outcome(outcome)) is not None
        ]
        sr = (
            sum(1 for outcome in outcomes if is_success_outcome(outcome)) / len(outcomes)
            if outcomes
            else None
        )

        results.append(
            EndReasonBreakdown(
                end_reason=end_reason,
                count=count,
                avg_duration=round(float(avg_dur), 1) if avg_dur else None,
                success_rate=round(sr, 3) if sr is not None else None,
            )
        )
    return results


def _compute_satisfaction_summary(
    db: Session,
    session_ids_q,
) -> SatisfactionSummary:
    """Aggregate user_satisfaction_counts JSON from session facets."""
    rows = (
        db.query(SessionFacets.user_satisfaction_counts, SessionModel.started_at)
        .join(SessionModel, SessionModel.id == SessionFacets.session_id)
        .filter(SessionModel.id.in_(session_ids_q))
        .filter(SessionFacets.user_satisfaction_counts.isnot(None))
        .all()
    )

    total_satisfied = 0
    total_neutral = 0
    total_dissatisfied = 0
    daily: dict[str, dict[str, int]] = {}

    for sat_counts, started_at in rows:
        if not sat_counts:
            continue
        s = sat_counts.get("satisfied", 0)
        n = sat_counts.get("neutral", 0)
        d = sat_counts.get("dissatisfied", 0)
        total_satisfied += s
        total_neutral += n
        total_dissatisfied += d

        if started_at:
            date_key = started_at.strftime("%Y-%m-%d")
            if date_key not in daily:
                daily[date_key] = {"satisfied": 0, "neutral": 0, "dissatisfied": 0}
            daily[date_key]["satisfied"] += s
            daily[date_key]["neutral"] += n
            daily[date_key]["dissatisfied"] += d

    total = total_satisfied + total_neutral + total_dissatisfied
    sat_rate = total_satisfied / total if total > 0 else None

    trend = [
        DailySatisfaction(
            date=date_type(int(d[:4]), int(d[5:7]), int(d[8:10])),
            satisfied=v["satisfied"],
            neutral=v["neutral"],
            dissatisfied=v["dissatisfied"],
        )
        for d, v in sorted(daily.items())
    ]

    return SatisfactionSummary(
        total_sessions_with_data=len(rows),
        satisfied_count=total_satisfied,
        neutral_count=total_neutral,
        dissatisfied_count=total_dissatisfied,
        satisfaction_rate=round(sat_rate, 3) if sat_rate is not None else None,
        trend=trend,
    )


def _compute_friction_clusters(
    db: Session,
    session_ids_q,
) -> list[FrictionCluster]:
    """Group friction by type, deduplicate details, sample up to 5."""
    rows = (
        db.query(SessionFacets.friction_counts, SessionFacets.friction_detail)
        .join(SessionModel, SessionModel.id == SessionFacets.session_id)
        .filter(SessionModel.id.in_(session_ids_q))
        .filter(SessionFacets.friction_counts.isnot(None))
        .all()
    )

    type_counts: Counter[str] = Counter()
    type_details: dict[str, list[str]] = {}

    for friction_counts, friction_detail in rows:
        if not friction_counts:
            continue
        for friction_type, count in friction_counts.items():
            if count > 0:
                type_counts[friction_type] += count
                if friction_detail:
                    if friction_type not in type_details:
                        type_details[friction_type] = []
                    if friction_detail not in type_details[friction_type]:
                        type_details[friction_type].append(friction_detail)

    return [
        FrictionCluster(
            cluster_label=ft,
            occurrence_count=cnt,
            sample_details=type_details.get(ft, [])[:5],
        )
        for ft, cnt in type_counts.most_common()
    ]


def _compute_cache_efficiency(
    db: Session,
    session_ids_q,
) -> CacheEfficiencyMetrics:
    """Compute cache efficiency from model usages."""
    # Aggregate totals
    agg = (
        db.query(
            func.coalesce(func.sum(ModelUsage.cache_read_tokens), 0),
            func.coalesce(func.sum(ModelUsage.cache_creation_tokens), 0),
            func.coalesce(func.sum(ModelUsage.input_tokens), 0),
        )
        .join(SessionModel, SessionModel.id == ModelUsage.session_id)
        .filter(SessionModel.id.in_(session_ids_q))
        .first()
    )
    total_cr = int(agg[0]) if agg else 0
    total_cc = int(agg[1]) if agg else 0
    total_inp = int(agg[2]) if agg else 0

    denom = total_cr + total_inp
    hit_rate = total_cr / denom if denom > 0 else None

    # Savings estimate: cache reads are cheaper than full input
    # savings = cache_read_tokens * (input_price - cache_read_price)
    # Use average Sonnet 4 pricing for estimate
    savings = None
    if total_cr > 0:
        from primer.common.pricing import get_pricing

        pricing = get_pricing("claude-sonnet-4")
        savings = total_cr * (pricing.input_per_token - pricing.cache_read_per_token)
        savings = round(savings, 4)

    # Daily trend
    daily_rows = (
        db.query(
            func.date(SessionModel.started_at).label("d"),
            func.coalesce(func.sum(ModelUsage.cache_read_tokens), 0),
            func.coalesce(func.sum(ModelUsage.cache_creation_tokens), 0),
            func.coalesce(func.sum(ModelUsage.input_tokens), 0),
        )
        .join(SessionModel, SessionModel.id == ModelUsage.session_id)
        .filter(SessionModel.id.in_(session_ids_q))
        .filter(SessionModel.started_at.isnot(None))
        .group_by(func.date(SessionModel.started_at))
        .order_by(func.date(SessionModel.started_at))
        .all()
    )

    daily_trend = []
    for d, cr, cc, inp in daily_rows:
        d_denom = cr + inp
        daily_trend.append(
            DailyCacheEntry(
                date=d,
                cache_read_tokens=int(cr),
                cache_creation_tokens=int(cc),
                input_tokens=int(inp),
                cache_hit_rate=round(cr / d_denom, 3) if d_denom > 0 else None,
            )
        )

    return CacheEfficiencyMetrics(
        total_cache_read_tokens=total_cr,
        total_cache_creation_tokens=total_cc,
        total_input_tokens=total_inp,
        cache_hit_rate=round(hit_rate, 3) if hit_rate is not None else None,
        cache_savings_estimate=savings,
        daily_cache_trend=daily_trend,
    )


def _compute_permission_mode_analysis(
    db: Session,
    session_ids_q,
) -> list[PermissionModeAnalysis]:
    """Group sessions by permission_mode with success rate and friction."""
    rows = (
        db.query(
            SessionModel.permission_mode,
            func.count(SessionModel.id).label("cnt"),
            func.avg(SessionModel.duration_seconds).label("avg_dur"),
        )
        .filter(SessionModel.id.in_(session_ids_q))
        .filter(SessionModel.permission_mode.isnot(None))
        .group_by(SessionModel.permission_mode)
        .order_by(func.count(SessionModel.id).desc())
        .all()
    )

    results = []
    for mode, count, avg_dur in rows:
        outcome_rows = (
            db.query(SessionFacets.outcome)
            .join(SessionModel, SessionModel.id == SessionFacets.session_id)
            .filter(SessionModel.id.in_(session_ids_q))
            .filter(SessionModel.permission_mode == mode)
            .filter(SessionFacets.outcome.isnot(None))
            .all()
        )
        outcomes = [
            normalized
            for (outcome,) in outcome_rows
            if (normalized := canonical_outcome(outcome)) is not None
        ]
        sr = (
            round(sum(1 for outcome in outcomes if is_success_outcome(outcome)) / len(outcomes), 3)
            if outcomes
            else None
        )

        # Avg friction count
        friction_rows = (
            db.query(SessionFacets.friction_counts)
            .join(SessionModel, SessionModel.id == SessionFacets.session_id)
            .filter(SessionModel.id.in_(session_ids_q))
            .filter(SessionModel.permission_mode == mode)
            .filter(SessionFacets.friction_counts.isnot(None))
            .all()
        )
        if friction_rows:
            total_friction = 0
            for (fc,) in friction_rows:
                if fc:
                    total_friction += sum(fc.values())
            avg_friction = total_friction / len(friction_rows)
        else:
            avg_friction = None

        results.append(
            PermissionModeAnalysis(
                mode=mode,
                session_count=count,
                success_rate=sr,
                avg_duration=round(float(avg_dur), 1) if avg_dur else None,
                avg_friction_count=round(avg_friction, 2) if avg_friction is not None else None,
            )
        )
    return results


def _compute_health_scores(
    db: Session,
    session_ids_q,
) -> SessionHealthDistribution:
    """Compute per-session health scores and aggregate into distribution."""
    # Fetch sessions with facets
    rows = (
        db.query(
            SessionModel.duration_seconds,
            SessionModel.started_at,
            SessionFacets.outcome,
            SessionFacets.friction_counts,
            SessionFacets.user_satisfaction_counts,
            SessionFacets.primary_success,
        )
        .outerjoin(SessionFacets, SessionFacets.session_id == SessionModel.id)
        .filter(SessionModel.id.in_(session_ids_q))
        .all()
    )

    if not rows:
        return SessionHealthDistribution(
            avg_score=0.0,
            median_score=0.0,
            buckets={"excellent": 0, "good": 0, "fair": 0, "poor": 0},
        )

    # Compute median duration for relative comparison
    durations = [r.duration_seconds for r in rows if r.duration_seconds is not None]
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

    scores: list[float] = []
    daily_scores: dict[str, list[float]] = {}

    for row in rows:
        score = compute_session_health_score(
            outcome=row.outcome,
            friction_counts=row.friction_counts,
            duration_seconds=row.duration_seconds,
            median_duration=median_dur,
            satisfaction_counts=row.user_satisfaction_counts,
            primary_success=row.primary_success,
        )
        scores.append(score)

        if row.started_at:
            date_key = row.started_at.strftime("%Y-%m-%d")
            if date_key not in daily_scores:
                daily_scores[date_key] = []
            daily_scores[date_key].append(score)

    avg_score = sum(scores) / len(scores)
    sorted_scores = sorted(scores)
    mid = len(sorted_scores) // 2
    median_score = (
        sorted_scores[mid]
        if len(sorted_scores) % 2 == 1
        else (sorted_scores[mid - 1] + sorted_scores[mid]) / 2
    )

    buckets = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
    for s in scores:
        if s >= 80:
            buckets["excellent"] += 1
        elif s >= 60:
            buckets["good"] += 1
        elif s >= 40:
            buckets["fair"] += 1
        else:
            buckets["poor"] += 1

    trend = [
        DailyHealthEntry(
            date=date_type(int(d[:4]), int(d[5:7]), int(d[8:10])),
            avg_score=round(sum(ss) / len(ss), 1),
            session_count=len(ss),
        )
        for d, ss in sorted(daily_scores.items())
    ]

    return SessionHealthDistribution(
        avg_score=round(avg_score, 1),
        median_score=round(median_score, 1),
        buckets=buckets,
        daily_trend=trend,
    )


def _compute_goal_analytics(
    db: Session,
    session_ids_q,
) -> GoalAnalytics:
    """Slice by session_type and goal_categories with cost/success metrics."""
    # Session type breakdown
    type_rows = (
        db.query(
            SessionFacets.session_type,
            SessionFacets.outcome,
        )
        .join(SessionModel, SessionModel.id == SessionFacets.session_id)
        .filter(SessionModel.id.in_(session_ids_q))
        .filter(SessionFacets.session_type.isnot(None))
        .all()
    )

    # Build type stats manually
    type_stats: dict[str, dict] = {}
    for facet_type, outcome in type_rows:
        if facet_type is None:
            continue
        if facet_type not in type_stats:
            type_stats[facet_type] = {"count": 0, "success": 0, "with_outcome": 0}
        type_stats[facet_type]["count"] += 1
        normalized_outcome = canonical_outcome(outcome)
        if normalized_outcome is not None:
            type_stats[facet_type]["with_outcome"] += 1
            if is_success_outcome(normalized_outcome):
                type_stats[facet_type]["success"] += 1

    # Get avg duration and cost per type
    type_breakdown = []
    for st, stats in sorted(type_stats.items(), key=lambda x: -x[1]["count"]):
        # Avg duration
        dur_q = (
            db.query(func.avg(SessionModel.duration_seconds))
            .join(SessionFacets, SessionFacets.session_id == SessionModel.id)
            .filter(SessionModel.id.in_(session_ids_q))
            .filter(SessionFacets.session_type == st)
        )
        avg_dur = dur_q.scalar()

        # Avg cost
        cost_q = (
            db.query(
                ModelUsage.model_name,
                func.sum(ModelUsage.input_tokens),
                func.sum(ModelUsage.output_tokens),
                func.sum(ModelUsage.cache_read_tokens),
                func.sum(ModelUsage.cache_creation_tokens),
            )
            .join(SessionModel, SessionModel.id == ModelUsage.session_id)
            .join(SessionFacets, SessionFacets.session_id == SessionModel.id)
            .filter(SessionModel.id.in_(session_ids_q))
            .filter(SessionFacets.session_type == st)
            .group_by(ModelUsage.model_name)
        )
        total_cost = 0.0
        for name, inp, out, cr, cc in cost_q.all():
            total_cost += estimate_cost(name, inp or 0, out or 0, cr or 0, cc or 0)
        avg_cost = total_cost / stats["count"] if stats["count"] > 0 else None

        sr = stats["success"] / stats["with_outcome"] if stats["with_outcome"] > 0 else None

        type_breakdown.append(
            GoalTypeBreakdown(
                session_type=st,
                count=stats["count"],
                avg_cost=round(avg_cost, 4) if avg_cost is not None else None,
                success_rate=round(sr, 3) if sr is not None else None,
                avg_duration=round(float(avg_dur), 1) if avg_dur else None,
            )
        )

    # Goal category breakdown
    cat_rows = (
        db.query(SessionFacets.goal_categories, SessionFacets.outcome)
        .join(SessionModel, SessionModel.id == SessionFacets.session_id)
        .filter(SessionModel.id.in_(session_ids_q))
        .filter(SessionFacets.goal_categories.isnot(None))
        .all()
    )

    cat_stats: dict[str, dict] = {}
    for cats, outcome in cat_rows:
        if not cats:
            continue
        normalized_outcome = canonical_outcome(outcome)
        for cat in cats:
            if cat not in cat_stats:
                cat_stats[cat] = {"count": 0, "success": 0, "with_outcome": 0}
            cat_stats[cat]["count"] += 1
            if normalized_outcome is not None:
                cat_stats[cat]["with_outcome"] += 1
                if is_success_outcome(normalized_outcome):
                    cat_stats[cat]["success"] += 1

    cat_breakdown = []
    for cat, stats in sorted(cat_stats.items(), key=lambda x: -x[1]["count"]):
        sr = stats["success"] / stats["with_outcome"] if stats["with_outcome"] > 0 else None
        cat_breakdown.append(
            GoalCategoryBreakdown(
                category=cat,
                count=stats["count"],
                avg_cost=None,
                success_rate=round(sr, 3) if sr is not None else None,
            )
        )

    return GoalAnalytics(
        session_type_breakdown=type_breakdown,
        goal_category_breakdown=cat_breakdown,
    )


def _compute_primary_success(
    db: Session,
    session_ids_q,
) -> PrimarySuccessAnalysis:
    """Count primary_success values, breakdown by session_type."""
    rows = (
        db.query(SessionFacets.primary_success, SessionFacets.session_type)
        .join(SessionModel, SessionModel.id == SessionFacets.session_id)
        .filter(SessionModel.id.in_(session_ids_q))
        .all()
    )

    full = partial = none_count = unknown = 0
    by_type: dict[str, dict[str, int]] = {}

    for ps, st in rows:
        bucket = _primary_success_bucket(ps)
        if bucket == "full":
            full += 1
        elif bucket == "partial":
            partial += 1
        elif bucket == "none":
            none_count += 1
        else:
            unknown += 1

        if st:
            if st not in by_type:
                by_type[st] = {"full": 0, "partial": 0, "none": 0, "unknown": 0}
            by_type[st][bucket] += 1

    total = full + partial + none_count + unknown
    full_rate = full / total if total > 0 else None

    return PrimarySuccessAnalysis(
        full_count=full,
        partial_count=partial,
        none_count=none_count,
        unknown_count=unknown,
        full_rate=round(full_rate, 3) if full_rate is not None else None,
        by_session_type=by_type,
    )


def get_session_insights(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date=None,
    end_date=None,
) -> SessionInsightsResponse:
    """Main entry point: compute all session insight facets."""
    q = base_session_query(db, team_id, engineer_id, start_date, end_date)
    session_ids_sq = q.with_entities(SessionModel.id).subquery()
    session_ids_q = session_ids_sq.select()
    sessions_analyzed = db.query(func.count()).select_from(session_ids_sq).scalar() or 0

    return SessionInsightsResponse(
        end_reasons=_compute_end_reason_breakdown(db, session_ids_q),
        satisfaction=_compute_satisfaction_summary(db, session_ids_q),
        friction_clusters=_compute_friction_clusters(db, session_ids_q),
        cache_efficiency=_compute_cache_efficiency(db, session_ids_q),
        permission_modes=_compute_permission_mode_analysis(db, session_ids_q),
        health_distribution=_compute_health_scores(db, session_ids_q),
        goals=_compute_goal_analytics(db, session_ids_q),
        primary_success=_compute_primary_success(db, session_ids_q),
        sessions_analyzed=sessions_analyzed,
    )
