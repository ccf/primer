from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from primer.common.facet_taxonomy import canonical_outcome, normalize_goal_categories
from primer.common.models import (
    Engineer,
    SessionFacets,
    SessionMessage,
)
from primer.common.models import (
    Session as SessionModel,
)

LOW_CONFIDENCE_THRESHOLD = 0.7
LEGACY_OUTCOMES = {
    outcome
    for outcome in (
        "success",
        "partial",
        "failure",
        "fully_achieved",
        "mostly_achieved",
        "partially_achieved",
        "not_achieved",
    )
    if canonical_outcome(outcome) != outcome
}


def _has_legacy_goal_categories(value: object) -> bool:
    return isinstance(value, dict)


def _legacy_goal_categories_predicate(db: Session):
    dialect_name = db.get_bind().dialect.name if db.get_bind() is not None else ""
    if dialect_name == "sqlite":
        return func.json_type(SessionFacets.goal_categories) == "object"
    if dialect_name == "postgresql":
        return func.json_typeof(SessionFacets.goal_categories) == "object"
    return SessionFacets.id.is_(None)


def _legacy_rows_predicate(db: Session):
    return or_(
        SessionFacets.outcome.in_(sorted(LEGACY_OUTCOMES)),
        _legacy_goal_categories_predicate(db),
    )


def _legacy_candidate_query(db: Session, query=None):
    base_query = query if query is not None else db.query(SessionFacets)
    return base_query.filter(_legacy_rows_predicate(db))


def _count_legacy_goal_category_rows(db: Session, query=None) -> int:
    base_query = query if query is not None else db.query(SessionFacets)
    return base_query.filter(_legacy_goal_categories_predicate(db)).count()


def _count_legacy_rows(db: Session, query=None) -> int:
    return _legacy_candidate_query(db, query=query).count()


def _apply_session_scope(
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


def _scoped_session_ids_subquery(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    return _apply_session_scope(
        db.query(SessionModel.id),
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    ).subquery()


def _scoped_facets_query(db: Session, scoped_session_ids):
    return db.query(SessionFacets).join(
        scoped_session_ids, SessionFacets.session_id == scoped_session_ids.c.id
    )


def _normalized_row_updates(row: SessionFacets) -> dict[str, object]:
    updates: dict[str, object] = {}

    if row.outcome in LEGACY_OUTCOMES:
        updates["outcome"] = canonical_outcome(row.outcome)

    if _has_legacy_goal_categories(row.goal_categories):
        updates["goal_categories"] = normalize_goal_categories(row.goal_categories)

    return updates


def get_measurement_integrity_stats(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, int | float]:
    scoped_session_ids = _scoped_session_ids_subquery(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )
    total_sessions = db.query(func.count()).select_from(scoped_session_ids).scalar() or 0
    sessions_with_messages = (
        db.query(func.count(func.distinct(SessionMessage.session_id)))
        .join(scoped_session_ids, SessionMessage.session_id == scoped_session_ids.c.id)
        .scalar()
        or 0
    )
    sessions_with_facets = _scoped_facets_query(db, scoped_session_ids).count()
    low_confidence_sessions = (
        _scoped_facets_query(db, scoped_session_ids)
        .filter(
            SessionFacets.confidence_score.isnot(None),
            SessionFacets.confidence_score < LOW_CONFIDENCE_THRESHOLD,
        )
        .count()
    )
    missing_confidence_sessions = (
        _scoped_facets_query(db, scoped_session_ids)
        .filter(SessionFacets.confidence_score.is_(None))
        .count()
    )
    legacy_outcome_sessions = (
        _scoped_facets_query(db, scoped_session_ids)
        .filter(SessionFacets.outcome.in_(sorted(LEGACY_OUTCOMES)))
        .count()
    )
    legacy_goal_category_sessions = _count_legacy_goal_category_rows(
        db, query=_scoped_facets_query(db, scoped_session_ids)
    )
    remaining_legacy_rows = _count_legacy_rows(
        db, query=_scoped_facets_query(db, scoped_session_ids)
    )

    facet_coverage_pct = (
        round((sessions_with_facets / total_sessions) * 100, 1) if total_sessions else 0.0
    )
    transcript_coverage_pct = (
        round((sessions_with_messages / total_sessions) * 100, 1) if total_sessions else 0.0
    )

    return {
        "total_sessions": total_sessions,
        "sessions_with_messages": sessions_with_messages,
        "sessions_with_facets": sessions_with_facets,
        "facet_coverage_pct": facet_coverage_pct,
        "transcript_coverage_pct": transcript_coverage_pct,
        "low_confidence_sessions": low_confidence_sessions,
        "missing_confidence_sessions": missing_confidence_sessions,
        "legacy_outcome_sessions": legacy_outcome_sessions,
        "legacy_goal_category_sessions": legacy_goal_category_sessions,
        "remaining_legacy_rows": remaining_legacy_rows,
    }


def normalize_existing_facets(
    db: Session, limit: int | None = None, dry_run: bool = False
) -> dict[str, int]:
    candidate_query = _legacy_candidate_query(db).order_by(SessionFacets.id)
    if limit is not None:
        candidate_query = candidate_query.limit(limit)

    candidate_rows = candidate_query.all()
    pending_updates = [(row, _normalized_row_updates(row)) for row in candidate_rows]

    if not dry_run:
        for row, updates in pending_updates:
            for field_name, value in updates.items():
                setattr(row, field_name, value)
        db.commit()

    return {
        "rows_scanned": len(candidate_rows),
        "rows_updated": 0 if dry_run else len(pending_updates),
        "remaining_legacy_rows": _count_legacy_rows(db),
    }
