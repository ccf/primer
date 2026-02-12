from collections import Counter

from sqlalchemy import func
from sqlalchemy.orm import Session

from primer.common.models import (
    Engineer,
    ModelUsage,
    Session as SessionModel,
    SessionFacets,
    ToolUsage,
)
from primer.common.schemas import (
    FrictionReport,
    ModelRanking,
    OverviewStats,
    ToolRanking,
)


def _base_session_query(db: Session, team_id: str | None = None):
    q = db.query(SessionModel)
    if team_id:
        q = q.join(Engineer).filter(Engineer.team_id == team_id)
    return q


def get_overview(db: Session, team_id: str | None = None) -> OverviewStats:
    q = _base_session_query(db, team_id)

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
    if team_id:
        eng_q = eng_q.join(Engineer).filter(Engineer.team_id == team_id)
    total_engineers = eng_q.scalar() or 0

    # Outcome counts from facets
    facets_q = db.query(SessionFacets.outcome)
    if team_id:
        facets_q = facets_q.join(SessionModel).join(Engineer).filter(Engineer.team_id == team_id)
    outcome_counts: dict[str, int] = {}
    for (outcome,) in facets_q.filter(SessionFacets.outcome.isnot(None)).all():
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

    # Session type counts
    type_q = db.query(SessionFacets.session_type)
    if team_id:
        type_q = type_q.join(SessionModel).join(Engineer).filter(Engineer.team_id == team_id)
    session_type_counts: dict[str, int] = {}
    for (st,) in type_q.filter(SessionFacets.session_type.isnot(None)).all():
        session_type_counts[st] = session_type_counts.get(st, 0) + 1

    return OverviewStats(
        total_sessions=total_sessions,
        total_engineers=total_engineers,
        total_messages=total_messages,
        total_tool_calls=total_tool_calls,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        avg_session_duration=avg_duration,
        avg_messages_per_session=avg_messages,
        outcome_counts=outcome_counts,
        session_type_counts=session_type_counts,
    )


def get_friction_report(db: Session, team_id: str | None = None) -> list[FrictionReport]:
    facets_q = db.query(SessionFacets)
    if team_id:
        facets_q = facets_q.join(SessionModel).join(Engineer).filter(Engineer.team_id == team_id)

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
    db: Session, team_id: str | None = None, limit: int = 20
) -> list[ToolRanking]:
    q = db.query(
        ToolUsage.tool_name,
        func.sum(ToolUsage.call_count).label("total_calls"),
        func.count(func.distinct(ToolUsage.session_id)).label("session_count"),
    )
    if team_id:
        q = q.join(SessionModel).join(Engineer).filter(Engineer.team_id == team_id)
    q = q.group_by(ToolUsage.tool_name).order_by(func.sum(ToolUsage.call_count).desc())
    return [
        ToolRanking(tool_name=name, total_calls=total, session_count=sc)
        for name, total, sc in q.limit(limit).all()
    ]


def get_model_rankings(db: Session, team_id: str | None = None) -> list[ModelRanking]:
    q = db.query(
        ModelUsage.model_name,
        func.sum(ModelUsage.input_tokens).label("total_input"),
        func.sum(ModelUsage.output_tokens).label("total_output"),
        func.count(func.distinct(ModelUsage.session_id)).label("session_count"),
    )
    if team_id:
        q = q.join(SessionModel).join(Engineer).filter(Engineer.team_id == team_id)
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
