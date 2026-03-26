"""MCP server entrypoint for Primer sidecar.

Register this in Claude Code's MCP settings to expose Primer tools during sessions.
"""

from mcp.server.fastmcp import FastMCP

from primer.mcp.tools import (
    primer_coaching,
    primer_friction_report,
    primer_in_session_nudges,
    primer_live_session_signals,
    primer_my_stats,
    primer_personal_recaps,
    primer_recommendations,
    primer_session_start_coaching,
    primer_sync,
    primer_team_overview,
)

mcp = FastMCP("primer", instructions="Primer: Claude Code usage insights for your team")


@mcp.tool()
def sync() -> str:
    """Sync local session history to the Primer server.

    Uploads any sessions that haven't been synced yet.
    """
    return primer_sync()


@mcp.tool()
def my_stats(days: int = 30) -> str:
    """Get your personal Claude Code usage stats.

    Includes sessions, tokens, tools used, and outcomes.
    """
    return primer_my_stats(days=days)


@mcp.tool()
def team_overview(team_id: str | None = None) -> str:
    """Get team-level analytics overview.

    Includes session counts, token usage, and outcome distribution.
    """
    return primer_team_overview(team_id=team_id)


@mcp.tool()
def friction_report(team_id: str | None = None) -> str:
    """Get a report of friction points your team encounters.

    Includes types and frequency of friction with Claude Code.
    """
    return primer_friction_report(team_id=team_id)


@mcp.tool()
def recommendations(team_id: str | None = None) -> str:
    """Get actionable recommendations to improve Claude Code usage.

    Based on patterns and friction analysis.
    """
    return primer_recommendations(team_id=team_id)


@mcp.tool()
def coaching(days: int = 30) -> str:
    """Get your personalized coaching brief.

    What's working, what's slowing you down, and what to try next —
    based on your usage patterns, friction, and team benchmarks.
    """
    return primer_coaching(days=days)


@mcp.tool()
def session_start_coaching(
    project_name: str | None = None,
    workflow_hint: str | None = None,
    task_hint: str | None = None,
    days: int = 90,
) -> str:
    """Get a contextual session-start brief before you begin work.

    Uses project context, workflow hints, and peer-backed evidence to suggest
    a strong starting pattern, tool/model choices, and likely pitfalls.
    """
    return primer_session_start_coaching(
        project_name=project_name,
        workflow_hint=workflow_hint,
        task_hint=task_hint,
        days=days,
    )


@mcp.tool()
def live_session_signals(
    session_id: str | None = None,
    transcript_path: str | None = None,
) -> str:
    """Get live friction, satisfaction, and risk signals for the current local session.

    Primer inspects the in-progress local transcript and summarizes whether the
    session looks healthy, stuck, or at risk of abandonment.
    """
    return primer_live_session_signals(session_id=session_id, transcript_path=transcript_path)


@mcp.tool()
def in_session_nudges(
    project_name: str | None = None,
    workflow_hint: str | None = None,
    task_hint: str | None = None,
    session_id: str | None = None,
    transcript_path: str | None = None,
) -> str:
    """Get evidence-backed nudges for what to try next during an active session.

    Primer combines live local session signals with project playbooks and prior
    team evidence to suggest the smallest next corrective action.
    """
    return primer_in_session_nudges(
        project_name=project_name,
        workflow_hint=workflow_hint,
        task_hint=task_hint,
        session_id=session_id,
        transcript_path=transcript_path,
    )


@mcp.tool()
def personal_recaps(period: str = "both") -> str:
    """Get your daily and weekly personal recaps in the sidecar."""
    return primer_personal_recaps(period=period)


if __name__ == "__main__":
    mcp.run()
