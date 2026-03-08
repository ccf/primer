from datetime import datetime

from sqlalchemy.orm import Session

from primer.common.schemas import Recommendation
from primer.server.services.analytics_service import (
    get_friction_report,
    get_overview,
    get_tool_rankings,
)
from primer.server.services.measurement_integrity_service import (
    LOW_CONFIDENCE_THRESHOLD,
    get_measurement_integrity_stats,
)

LOW_COVERAGE_THRESHOLD_PCT = 30.0


def get_recommendations(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[Recommendation]:
    """Rule-based recommendation engine. Analyzes usage patterns and returns actionable recs."""
    recs: list[Recommendation] = []
    overview = get_overview(
        db, team_id=team_id, engineer_id=engineer_id, start_date=start_date, end_date=end_date
    )

    if overview.total_sessions == 0:
        return recs

    # High friction check
    friction = get_friction_report(
        db, team_id=team_id, engineer_id=engineer_id, start_date=start_date, end_date=end_date
    )
    for fr in friction:
        if fr.count >= 5:
            recs.append(
                Recommendation(
                    category="friction",
                    title=f"Recurring friction: {fr.friction_type}",
                    description=(
                        f"'{fr.friction_type}' has been reported {fr.count} times. "
                        f"Review the details and consider addressing root causes."
                    ),
                    severity="warning",
                    evidence={"friction_type": fr.friction_type, "count": fr.count},
                )
            )

    # Low facet coverage
    if overview.total_sessions > 10:
        integrity = get_measurement_integrity_stats(
            db,
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        )
        facet_coverage_pct = float(integrity["facet_coverage_pct"])
        transcript_coverage_pct = float(integrity["transcript_coverage_pct"])
        sessions_with_facets = int(integrity["sessions_with_facets"])
        low_confidence_sessions = int(integrity["low_confidence_sessions"])
        missing_confidence_sessions = int(integrity["missing_confidence_sessions"])
        legacy_outcome_sessions = int(integrity["legacy_outcome_sessions"])
        legacy_goal_category_sessions = int(integrity["legacy_goal_category_sessions"])
        remaining_legacy_rows = int(integrity["remaining_legacy_rows"])
        low_confidence_pct = (
            round((low_confidence_sessions / sessions_with_facets) * 100, 1)
            if sessions_with_facets
            else 0.0
        )
        missing_confidence_pct = (
            round((missing_confidence_sessions / sessions_with_facets) * 100, 1)
            if sessions_with_facets
            else 0.0
        )

        integrity_signals: list[str] = []
        if facet_coverage_pct < LOW_COVERAGE_THRESHOLD_PCT:
            integrity_signals.append(f"facet coverage is {facet_coverage_pct:.1f}%")
        if transcript_coverage_pct < LOW_COVERAGE_THRESHOLD_PCT:
            integrity_signals.append(f"transcript coverage is {transcript_coverage_pct:.1f}%")
        if low_confidence_sessions > 0:
            integrity_signals.append(
                f"{low_confidence_sessions} sessions are below the "
                f"{LOW_CONFIDENCE_THRESHOLD:.2f} confidence threshold"
            )
        if missing_confidence_sessions > 0:
            integrity_signals.append(
                f"{missing_confidence_sessions} sessions are missing confidence scores"
            )
        if remaining_legacy_rows > 0:
            integrity_signals.append(
                f"{remaining_legacy_rows} legacy facet rows still need normalization"
            )

        if integrity_signals:
            recs.append(
                Recommendation(
                    category="data_quality",
                    title="Measurement integrity needs attention",
                    description=(
                        "Recommendation confidence is limited because "
                        + "; ".join(integrity_signals)
                        + ". Improve transcript/facet collection and normalize "
                        + "legacy rows before acting on downstream insights."
                    ),
                    severity="info",
                    evidence={
                        "total_sessions": int(integrity["total_sessions"]),
                        "sessions_with_facets": sessions_with_facets,
                        "facet_coverage_pct": facet_coverage_pct,
                        "sessions_with_messages": int(integrity["sessions_with_messages"]),
                        "transcript_coverage_pct": transcript_coverage_pct,
                        "low_confidence_sessions": low_confidence_sessions,
                        "low_confidence_pct": low_confidence_pct,
                        "missing_confidence_sessions": missing_confidence_sessions,
                        "missing_confidence_pct": missing_confidence_pct,
                        "confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
                        "legacy_outcome_sessions": legacy_outcome_sessions,
                        "legacy_goal_category_sessions": legacy_goal_category_sessions,
                        "remaining_legacy_rows": remaining_legacy_rows,
                    },
                )
            )

    # Heavy token usage check
    if overview.avg_session_duration and overview.total_sessions > 5:
        total = overview.total_input_tokens + overview.total_output_tokens
        avg_tokens = total / overview.total_sessions
        if avg_tokens > 500_000:
            recs.append(
                Recommendation(
                    category="cost",
                    title="High average token usage",
                    description=(
                        f"Average of {avg_tokens:,.0f} tokens per session. "
                        "Consider reviewing prompt patterns or using caching more effectively."
                    ),
                    severity="warning",
                    evidence={"avg_tokens_per_session": avg_tokens},
                )
            )

    # Tool diversity check
    tools = get_tool_rankings(
        db,
        team_id=team_id,
        limit=5,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )
    if tools and tools[0].total_calls > 0:
        top_tool_share = tools[0].total_calls / sum(t.total_calls for t in tools)
        if top_tool_share > 0.6:
            recs.append(
                Recommendation(
                    category="workflow",
                    title=f"Over-reliance on {tools[0].tool_name}",
                    description=(
                        f"{tools[0].tool_name} accounts for "
                        f"{top_tool_share:.0%} of all tool calls. "
                        "This may indicate underuse of other available tools."
                    ),
                    severity="info",
                    evidence={"tool": tools[0].tool_name, "share": top_tool_share},
                )
            )

    return recs
