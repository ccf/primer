from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func

from primer.common.config import settings
from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.common.models import (
    DailyAnalyticsRollup,
    Engineer,
    SessionFacets,
    SessionMessage,
    ToolUsage,
)
from primer.common.models import Session as SessionModel
from primer.common.schemas import DailyStatsResponse
from primer.common.source_capabilities import get_agent_types_with_capability

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

ROLLUP_SCOPE_ORG = "org"


def _scope_key(team_id: str | None) -> str:
    return ROLLUP_SCOPE_ORG if team_id is None else f"team:{team_id}"


def _rollup_key(rollup_date: date, team_id: str | None) -> tuple[date, str | None]:
    return rollup_date, team_id


def _is_day_start(value: datetime) -> bool:
    return value.hour == 0 and value.minute == 0 and value.second == 0 and value.microsecond == 0


def _is_day_end(value: datetime) -> bool:
    return value.hour == 23 and value.minute == 59 and value.second == 59


def _supports_rollup_bounds(
    start_date: datetime | None,
    end_date: datetime | None,
) -> bool:
    if start_date and not _is_day_start(start_date):
        return False
    return not (end_date and not _is_day_end(end_date))


def refresh_recent_daily_analytics_rollups(
    db: Session,
    *,
    lookback_days: int | None = None,
) -> dict[str, int]:
    effective_lookback = lookback_days or settings.analytics_rollup_lookback_days
    since_date = datetime.now(UTC).date() - timedelta(days=max(effective_lookback - 1, 0))

    stats: dict[tuple[date, str | None], dict[str, int]] = defaultdict(
        lambda: {
            "session_count": 0,
            "message_count": 0,
            "tool_call_count": 0,
            "success_session_count": 0,
            "outcome_session_count": 0,
        }
    )

    def add_metric(rollup_date: date, team_id: str | None, field: str, amount: int) -> None:
        stats[_rollup_key(rollup_date, None)][field] += amount
        if team_id is not None:
            stats[_rollup_key(rollup_date, team_id)][field] += amount

    session_rows = (
        db.query(
            func.date(SessionModel.started_at).label("rollup_date"),
            Engineer.team_id,
            func.count(SessionModel.id).label("session_count"),
        )
        .join(Engineer, Engineer.id == SessionModel.engineer_id)
        .filter(SessionModel.started_at.isnot(None))
        .filter(func.date(SessionModel.started_at) >= since_date.isoformat())
        .group_by(func.date(SessionModel.started_at), Engineer.team_id)
        .all()
    )
    for rollup_date, team_id, session_count in session_rows:
        add_metric(
            date.fromisoformat(str(rollup_date)),
            team_id,
            "session_count",
            int(session_count or 0),
        )

    transcript_agent_types = get_agent_types_with_capability("supports_transcript")
    if transcript_agent_types:
        message_rows = (
            db.query(
                func.date(SessionModel.started_at).label("rollup_date"),
                Engineer.team_id,
                func.count(SessionMessage.id).label("message_count"),
            )
            .join(Engineer, Engineer.id == SessionModel.engineer_id)
            .join(SessionMessage, SessionMessage.session_id == SessionModel.id)
            .filter(SessionModel.started_at.isnot(None))
            .filter(func.date(SessionModel.started_at) >= since_date.isoformat())
            .filter(SessionModel.agent_type.in_(transcript_agent_types))
            .group_by(func.date(SessionModel.started_at), Engineer.team_id)
            .all()
        )
        for rollup_date, team_id, message_count in message_rows:
            add_metric(
                date.fromisoformat(str(rollup_date)),
                team_id,
                "message_count",
                int(message_count or 0),
            )

    tool_agent_types = get_agent_types_with_capability("supports_tool_calls")
    if tool_agent_types:
        tool_rows = (
            db.query(
                func.date(SessionModel.started_at).label("rollup_date"),
                Engineer.team_id,
                func.coalesce(func.sum(ToolUsage.call_count), 0).label("tool_call_count"),
            )
            .join(Engineer, Engineer.id == SessionModel.engineer_id)
            .join(ToolUsage, ToolUsage.session_id == SessionModel.id)
            .filter(SessionModel.started_at.isnot(None))
            .filter(func.date(SessionModel.started_at) >= since_date.isoformat())
            .filter(SessionModel.agent_type.in_(tool_agent_types))
            .group_by(func.date(SessionModel.started_at), Engineer.team_id)
            .all()
        )
        for rollup_date, team_id, tool_call_count in tool_rows:
            add_metric(
                date.fromisoformat(str(rollup_date)),
                team_id,
                "tool_call_count",
                int(tool_call_count or 0),
            )

    facet_agent_types = get_agent_types_with_capability("supports_facets")
    if facet_agent_types:
        outcome_rows = (
            db.query(
                func.date(SessionModel.started_at).label("rollup_date"),
                Engineer.team_id,
                SessionFacets.outcome,
                func.count(SessionModel.id).label("session_count"),
            )
            .join(Engineer, Engineer.id == SessionModel.engineer_id)
            .join(SessionFacets, SessionFacets.session_id == SessionModel.id)
            .filter(SessionModel.started_at.isnot(None))
            .filter(func.date(SessionModel.started_at) >= since_date.isoformat())
            .filter(SessionModel.agent_type.in_(facet_agent_types))
            .filter(SessionFacets.outcome.isnot(None))
            .group_by(func.date(SessionModel.started_at), Engineer.team_id, SessionFacets.outcome)
            .all()
        )
        for rollup_date, team_id, outcome, session_count in outcome_rows:
            normalized_outcome = canonical_outcome(outcome)
            if normalized_outcome is None:
                continue
            count = int(session_count or 0)
            rollup_day = date.fromisoformat(str(rollup_date))
            add_metric(rollup_day, team_id, "outcome_session_count", count)
            if is_success_outcome(normalized_outcome):
                add_metric(rollup_day, team_id, "success_session_count", count)

    desired_keys = set(stats)
    existing_rows = (
        db.query(DailyAnalyticsRollup).filter(DailyAnalyticsRollup.date >= since_date).all()
    )

    refreshed = 0
    deleted = 0
    now = datetime.now(UTC).replace(tzinfo=None)

    for row in existing_rows:
        key = _rollup_key(row.date, row.team_id)
        if key not in desired_keys:
            db.delete(row)
            deleted += 1

    for (rollup_date, team_id), values in stats.items():
        row = (
            db.query(DailyAnalyticsRollup)
            .filter(
                DailyAnalyticsRollup.date == rollup_date,
                DailyAnalyticsRollup.scope_key == _scope_key(team_id),
            )
            .first()
        )
        if row is None:
            row = DailyAnalyticsRollup(
                date=rollup_date,
                scope_key=_scope_key(team_id),
                team_id=team_id,
            )
            db.add(row)

        row.session_count = values["session_count"]
        row.message_count = values["message_count"]
        row.tool_call_count = values["tool_call_count"]
        row.success_session_count = values["success_session_count"]
        row.outcome_session_count = values["outcome_session_count"]
        row.refreshed_at = now
        refreshed += 1

    db.commit()
    return {"refreshed": refreshed, "deleted": deleted}


def get_daily_stats_from_rollups(
    db: Session,
    *,
    team_id: str | None = None,
    days: int = 30,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[DailyStatsResponse] | None:
    if not _supports_rollup_bounds(start_date, end_date):
        return None

    base_q = db.query(func.date(SessionModel.started_at).label("date")).filter(
        SessionModel.started_at.isnot(None)
    )
    if team_id:
        base_q = base_q.join(Engineer).filter(Engineer.team_id == team_id)
    if start_date:
        base_q = base_q.filter(SessionModel.started_at >= start_date)
    if end_date:
        base_q = base_q.filter(SessionModel.started_at <= end_date)

    base_dates = [
        date.fromisoformat(str(row.date))
        for row in base_q.group_by(func.date(SessionModel.started_at))
        .order_by(func.date(SessionModel.started_at).desc())
        .limit(days)
        .all()
    ]
    if not base_dates:
        return []

    scope_key = _scope_key(team_id)
    rollup_rows = (
        db.query(DailyAnalyticsRollup)
        .filter(
            DailyAnalyticsRollup.scope_key == scope_key,
            DailyAnalyticsRollup.date.in_(base_dates),
        )
        .order_by(DailyAnalyticsRollup.date.desc())
        .all()
    )
    if len(rollup_rows) != len(base_dates):
        return None

    rollup_map = {row.date: row for row in rollup_rows}
    return [
        DailyStatsResponse(
            date=rollup_date,
            session_count=rollup_map[rollup_date].session_count,
            message_count=rollup_map[rollup_date].message_count,
            tool_call_count=rollup_map[rollup_date].tool_call_count,
            success_rate=(
                rollup_map[rollup_date].success_session_count
                / rollup_map[rollup_date].outcome_session_count
                if rollup_map[rollup_date].outcome_session_count
                else None
            ),
        )
        for rollup_date in base_dates
    ]
