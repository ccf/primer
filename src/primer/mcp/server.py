"""MCP server entrypoint for Primer sidecar.

Register this in Claude Code's MCP settings to expose Primer tools during sessions.
"""

from mcp.server.fastmcp import FastMCP

from primer.mcp.tools import (
    primer_coaching,
    primer_friction_report,
    primer_my_stats,
    primer_recommendations,
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


if __name__ == "__main__":
    mcp.run()
