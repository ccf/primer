from datetime import datetime
from statistics import median

from sqlalchemy import func
from sqlalchemy.orm import Session

from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.common.models import ModelUsage, SessionFacets
from primer.common.models import Session as SessionModel
from primer.common.pricing import estimate_cost
from primer.common.schemas import EffectivenessBreakdown, EffectivenessScore
from primer.server.services.analytics_service import base_session_query

_WEIGHTS: dict[str, int] = {
    "success_rate": 35,
    "cost_efficiency": 20,
    "quality_outcomes": 25,
    "follow_through": 20,
}


def build_effectiveness_score(
    *,
    success_rate: float | None,
    cost_per_successful_outcome: float | None,
    benchmark_cost_per_successful_outcome: float | None,
    pr_merge_rate: float | None,
    findings_fix_rate: float | None,
    total_sessions: int,
    sessions_with_commits: int,
) -> EffectivenessScore:
    quality_outcomes = _quality_outcomes(pr_merge_rate, findings_fix_rate)
    breakdown = EffectivenessBreakdown(
        success_rate=_round_component(_clamp_unit_interval(success_rate)),
        cost_efficiency=_round_component(
            _cost_efficiency(cost_per_successful_outcome, benchmark_cost_per_successful_outcome)
        ),
        quality_outcomes=_round_component(quality_outcomes),
        follow_through=_round_component(_follow_through(total_sessions, sessions_with_commits)),
    )

    # A follow-through or cost signal on its own is too weak to imply effectiveness.
    if breakdown.success_rate is None and breakdown.quality_outcomes is None:
        return EffectivenessScore(
            score=None,
            breakdown=breakdown,
            cost_per_successful_outcome=_round_cost(cost_per_successful_outcome),
            benchmark_cost_per_successful_outcome=_round_cost(
                benchmark_cost_per_successful_outcome
            ),
        )

    available = {
        "success_rate": breakdown.success_rate,
        "cost_efficiency": breakdown.cost_efficiency,
        "quality_outcomes": breakdown.quality_outcomes,
        "follow_through": breakdown.follow_through,
    }
    weighted = [
        (name, value, _WEIGHTS[name]) for name, value in available.items() if value is not None
    ]
    if not weighted:
        score = None
    else:
        total_weight = sum(weight for _, _, weight in weighted)
        score = round(
            min(
                sum(value * weight for _, value, weight in weighted) / total_weight * 100,
                100.0,
            ),
            1,
        )

    return EffectivenessScore(
        score=score,
        breakdown=breakdown,
        cost_per_successful_outcome=_round_cost(cost_per_successful_outcome),
        benchmark_cost_per_successful_outcome=_round_cost(benchmark_cost_per_successful_outcome),
    )


def get_peer_cost_per_success_benchmark(
    db: Session,
    *,
    group_by: str,
    target_value: str,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> float | None:
    group_column = getattr(SessionModel, group_by)
    session_q = base_session_query(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )
    grouped_costs = _grouped_cost_per_success(db, session_q, group_column)
    peer_values = [
        cost
        for group_value, cost in grouped_costs.items()
        if group_value not in {None, target_value} and cost is not None
    ]
    if not peer_values:
        return None
    return round(median(peer_values), 4)


def _grouped_cost_per_success(db: Session, session_q, group_column) -> dict[str, float]:
    session_id_q = session_q.with_entities(SessionModel.id)

    cost_rows = (
        db.query(
            group_column,
            ModelUsage.model_name,
            func.coalesce(func.sum(ModelUsage.input_tokens), 0),
            func.coalesce(func.sum(ModelUsage.output_tokens), 0),
            func.coalesce(func.sum(ModelUsage.cache_read_tokens), 0),
            func.coalesce(func.sum(ModelUsage.cache_creation_tokens), 0),
        )
        .join(SessionModel, ModelUsage.session_id == SessionModel.id)
        .filter(SessionModel.id.in_(session_id_q))
        .group_by(group_column, ModelUsage.model_name)
        .all()
    )

    total_cost_by_group: dict[str, float] = {}
    for (
        group_value,
        model_name,
        input_tokens,
        output_tokens,
        cache_read,
        cache_creation,
    ) in cost_rows:
        if group_value is None:
            continue
        total_cost_by_group[group_value] = total_cost_by_group.get(
            group_value, 0.0
        ) + estimate_cost(
            model_name,
            input_tokens or 0,
            output_tokens or 0,
            cache_read or 0,
            cache_creation or 0,
        )

    outcome_rows = (
        db.query(group_column, SessionFacets.outcome)
        .join(SessionModel, SessionFacets.session_id == SessionModel.id)
        .filter(
            SessionModel.id.in_(session_id_q),
            SessionFacets.outcome.isnot(None),
            SessionModel.id.in_(db.query(ModelUsage.session_id).distinct()),
        )
        .all()
    )

    success_count_by_group: dict[str, int] = {}
    for group_value, outcome in outcome_rows:
        if group_value is None:
            continue
        normalized = canonical_outcome(outcome)
        if normalized is not None and is_success_outcome(normalized):
            success_count_by_group[group_value] = success_count_by_group.get(group_value, 0) + 1

    grouped_cost_per_success: dict[str, float] = {}
    for group_value, total_cost in total_cost_by_group.items():
        success_count = success_count_by_group.get(group_value, 0)
        if success_count > 0:
            grouped_cost_per_success[group_value] = total_cost / success_count

    return grouped_cost_per_success


def _quality_outcomes(pr_merge_rate: float | None, findings_fix_rate: float | None) -> float | None:
    signals = [
        _clamp_unit_interval(signal)
        for signal in (pr_merge_rate, findings_fix_rate)
        if signal is not None
    ]
    if not signals:
        return None
    return sum(signals) / len(signals)


def _follow_through(total_sessions: int, sessions_with_commits: int) -> float | None:
    if total_sessions <= 0:
        return None
    return _clamp_unit_interval(sessions_with_commits / total_sessions)


def _cost_efficiency(
    cost_per_successful_outcome: float | None,
    benchmark_cost_per_successful_outcome: float | None,
) -> float | None:
    if (
        cost_per_successful_outcome is None
        or benchmark_cost_per_successful_outcome is None
        or benchmark_cost_per_successful_outcome <= 0
    ):
        return None
    ratio = cost_per_successful_outcome / benchmark_cost_per_successful_outcome
    return max(0.0, min(1.0, 1.0 - (ratio - 0.5) / 1.5))


def _clamp_unit_interval(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, value))


def _round_component(value: float | None) -> float | None:
    return round(value, 3) if value is not None else None


def _round_cost(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None
