"""MCP tool definitions for Primer sidecar."""

import json
import logging
import os

import httpx

from primer.mcp.sync import sync_sessions

logger = logging.getLogger(__name__)

SERVER_URL = os.environ.get("PRIMER_SERVER_URL", "http://localhost:8000")
API_KEY = os.environ.get("PRIMER_API_KEY", "")
ADMIN_API_KEY = os.environ.get("PRIMER_ADMIN_API_KEY", "")


def _admin_headers() -> dict:
    admin_key = ADMIN_API_KEY or API_KEY
    return {"x-admin-key": admin_key, "x-api-key": API_KEY}


def primer_sync() -> str:
    """Sync local session history to the Primer server (backfill missing sessions)."""
    if not API_KEY:
        return "Error: PRIMER_API_KEY not set"
    result = sync_sessions(SERVER_URL, API_KEY)
    return json.dumps(result, indent=2)


def primer_my_stats(days: int = 30) -> str:
    """Get personal usage stats (sessions, tokens, tools, outcomes) for the last N days."""
    if not API_KEY:
        return "Error: PRIMER_API_KEY not set"
    try:
        resp = httpx.get(
            f"{SERVER_URL}/api/v1/analytics/overview",
            headers=_admin_headers(),
            timeout=10.0,
        )
        if resp.status_code == 200:
            return json.dumps(resp.json(), indent=2)
        return f"Error: {resp.status_code} - {resp.text}"
    except httpx.RequestError as e:
        return f"Error connecting to server: {e}"


def primer_team_overview(team_id: str | None = None) -> str:
    """Get team-level analytics overview."""
    if not API_KEY:
        return "Error: PRIMER_API_KEY not set"
    try:
        params = {"team_id": team_id} if team_id else {}
        resp = httpx.get(
            f"{SERVER_URL}/api/v1/analytics/overview",
            headers=_admin_headers(),
            params=params,
            timeout=10.0,
        )
        if resp.status_code == 200:
            return json.dumps(resp.json(), indent=2)
        return f"Error: {resp.status_code} - {resp.text}"
    except httpx.RequestError as e:
        return f"Error connecting to server: {e}"


def primer_friction_report(team_id: str | None = None) -> str:
    """Get team friction points and details."""
    if not API_KEY:
        return "Error: PRIMER_API_KEY not set"
    try:
        params = {"team_id": team_id} if team_id else {}
        resp = httpx.get(
            f"{SERVER_URL}/api/v1/analytics/friction",
            headers=_admin_headers(),
            params=params,
            timeout=10.0,
        )
        if resp.status_code == 200:
            return json.dumps(resp.json(), indent=2)
        return f"Error: {resp.status_code} - {resp.text}"
    except httpx.RequestError as e:
        return f"Error connecting to server: {e}"


def primer_recommendations(team_id: str | None = None) -> str:
    """Get org/team recommendations from the synthesis engine."""
    if not API_KEY:
        return "Error: PRIMER_API_KEY not set"
    try:
        params = {"team_id": team_id} if team_id else {}
        resp = httpx.get(
            f"{SERVER_URL}/api/v1/analytics/recommendations",
            headers=_admin_headers(),
            params=params,
            timeout=10.0,
        )
        if resp.status_code == 200:
            return json.dumps(resp.json(), indent=2)
        return f"Error: {resp.status_code} - {resp.text}"
    except httpx.RequestError as e:
        return f"Error connecting to server: {e}"


def primer_coaching(days: int = 30) -> str:
    """Get your personalized coaching brief.

    Synthesizes your usage patterns, friction hotspots, skill gaps,
    and config optimization into actionable guidance.
    """
    if not API_KEY:
        return "Error: PRIMER_API_KEY not set"
    try:
        resp = httpx.get(
            f"{SERVER_URL}/api/v1/analytics/coaching",
            params={"days": days},
            headers={"x-api-key": API_KEY},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            lines = ["## Your Primer Coaching Brief\n"]
            lines.append(f"**Status**: {data['status_summary']}\n")
            for section in data.get("sections", []):
                lines.append(f"### {section['title']}")
                for item in section.get("items", []):
                    lines.append(f"- {item}")
                lines.append("")
            return "\n".join(lines)
        return f"Error: {resp.status_code} - {resp.text}"
    except httpx.RequestError as e:
        return f"Error connecting to server: {e}"
