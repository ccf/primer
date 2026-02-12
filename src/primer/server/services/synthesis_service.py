from sqlalchemy.orm import Session

from primer.common.schemas import Recommendation
from primer.server.services.analytics_service import (
    get_friction_report,
    get_overview,
    get_tool_rankings,
)


def get_recommendations(
    db: Session, team_id: str | None = None, engineer_id: str | None = None
) -> list[Recommendation]:
    """Rule-based recommendation engine. Analyzes usage patterns and returns actionable recs."""
    recs: list[Recommendation] = []
    overview = get_overview(db, team_id=team_id, engineer_id=engineer_id)

    if overview.total_sessions == 0:
        return recs

    # High friction check
    friction = get_friction_report(db, team_id=team_id, engineer_id=engineer_id)
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
        facet_sessions = sum(overview.outcome_counts.values())
        coverage = facet_sessions / overview.total_sessions
        if coverage < 0.3:
            recs.append(
                Recommendation(
                    category="data_quality",
                    title="Low facet coverage",
                    description=(
                        f"Only {coverage:.0%} of sessions have facets. "
                        "Encourage engineers to run /insights periodically."
                    ),
                    severity="info",
                    evidence={"coverage": coverage, "total_sessions": overview.total_sessions},
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
    tools = get_tool_rankings(db, team_id=team_id, limit=5, engineer_id=engineer_id)
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
