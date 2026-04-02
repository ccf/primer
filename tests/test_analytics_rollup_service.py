from datetime import UTC, datetime
from uuid import uuid4

from primer.common.models import DailyAnalyticsRollup, SessionFacets, SessionMessage, ToolUsage
from primer.common.models import Session as SessionModel
from primer.server.services.analytics_rollup_service import (
    refresh_recent_daily_analytics_rollups,
)


def test_refresh_recent_daily_analytics_rollups_creates_org_and_team_rows(
    db_session, engineer_with_key
):
    engineer, _api_key = engineer_with_key
    session = SessionModel(
        id=str(uuid4()),
        engineer_id=engineer.id,
        started_at=datetime(2026, 4, 2, 12, 0, tzinfo=UTC),
        message_count=2,
        user_message_count=1,
        assistant_message_count=1,
        tool_call_count=3,
        has_facets=True,
    )
    db_session.add(session)
    db_session.flush()
    db_session.add_all(
        [
            SessionMessage(
                session_id=session.id,
                ordinal=0,
                role="human",
                content_text="Investigate flaky test",
            ),
            SessionMessage(
                session_id=session.id,
                ordinal=1,
                role="assistant",
                content_text="Checking logs",
            ),
            ToolUsage(session_id=session.id, tool_name="Read", call_count=3),
            SessionFacets(session_id=session.id, outcome="success"),
        ]
    )
    db_session.commit()

    summary = refresh_recent_daily_analytics_rollups(db_session, lookback_days=7)

    assert summary["refreshed"] == 2
    org_row = (
        db_session.query(DailyAnalyticsRollup)
        .filter(
            DailyAnalyticsRollup.date == datetime(2026, 4, 2, tzinfo=UTC).date(),
            DailyAnalyticsRollup.scope_key == "org",
        )
        .one()
    )
    team_row = (
        db_session.query(DailyAnalyticsRollup)
        .filter(
            DailyAnalyticsRollup.date == datetime(2026, 4, 2, tzinfo=UTC).date(),
            DailyAnalyticsRollup.scope_key == f"team:{engineer.team_id}",
        )
        .one()
    )

    for row in (org_row, team_row):
        assert row.session_count == 1
        assert row.message_count == 2
        assert row.tool_call_count == 3
        assert row.success_session_count == 1
        assert row.outcome_session_count == 1
