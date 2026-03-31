"""MCP tool definitions for Primer sidecar."""

import json
import logging
import os

import httpx
from pydantic import ValidationError

from primer.common.auth_headers import build_engineer_auth_headers
from primer.mcp.nudges import build_in_session_nudges
from primer.mcp.sync import sync_sessions
from primer.server.services.live_session_signal_service import get_live_session_signals

logger = logging.getLogger(__name__)

SERVER_URL = os.environ.get("PRIMER_SERVER_URL", "http://localhost:8000")
DEVICE_TOKEN = os.environ.get("PRIMER_DEVICE_TOKEN", "")
API_KEY = os.environ.get("PRIMER_API_KEY", "")
ADMIN_API_KEY = os.environ.get("PRIMER_ADMIN_API_KEY", "")


def _has_engineer_auth() -> bool:
    return bool(DEVICE_TOKEN or API_KEY)


def _engineer_headers() -> dict:
    return build_engineer_auth_headers(
        api_key=API_KEY or None,
        device_token=DEVICE_TOKEN or None,
    )


def _admin_headers() -> dict:
    headers = _engineer_headers()
    admin_key = ADMIN_API_KEY or API_KEY
    if admin_key:
        headers["x-admin-key"] = admin_key
    return headers


def _render_coaching_brief(data: dict) -> str:
    brief_type = data.get("brief_type", "retrospective")
    heading = (
        "## Your Primer Session-Start Brief\n"
        if brief_type == "session_start"
        else "## Your Primer Coaching Brief\n"
    )
    lines = [heading]
    lines.append(f"**Status**: {data['status_summary']}\n")
    if data.get("context_summary"):
        lines.append(f"**Context**: {data['context_summary']}\n")
    for section in data.get("sections", []):
        lines.append(f"### {section['title']}")
        for item in section.get("items", []):
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)


def primer_sync() -> str:
    """Sync local session history to the Primer server (backfill missing sessions)."""
    if not _has_engineer_auth():
        return "Error: PRIMER_DEVICE_TOKEN or PRIMER_API_KEY not set"
    result = sync_sessions(
        SERVER_URL,
        api_key=API_KEY or None,
        device_token=DEVICE_TOKEN or None,
    )
    return json.dumps(result, indent=2)


def primer_my_stats(days: int = 30) -> str:
    """Get personal usage stats (sessions, tokens, tools, outcomes) for the last N days."""
    if not _has_engineer_auth():
        return "Error: PRIMER_DEVICE_TOKEN or PRIMER_API_KEY not set"
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
    if not _has_engineer_auth():
        return "Error: PRIMER_DEVICE_TOKEN or PRIMER_API_KEY not set"
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
    if not _has_engineer_auth():
        return "Error: PRIMER_DEVICE_TOKEN or PRIMER_API_KEY not set"
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
    if not _has_engineer_auth():
        return "Error: PRIMER_DEVICE_TOKEN or PRIMER_API_KEY not set"
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
    if not _has_engineer_auth():
        return "Error: PRIMER_DEVICE_TOKEN or PRIMER_API_KEY not set"
    try:
        resp = httpx.get(
            f"{SERVER_URL}/api/v1/analytics/coaching",
            params={"days": days},
            headers=_engineer_headers(),
            timeout=30,
        )
        if resp.status_code == 200:
            return _render_coaching_brief(resp.json())
        return f"Error: {resp.status_code} - {resp.text}"
    except httpx.RequestError as e:
        return f"Error connecting to server: {e}"


def primer_session_start_coaching(
    project_name: str | None = None,
    workflow_hint: str | None = None,
    task_hint: str | None = None,
    days: int = 90,
) -> str:
    """Get a contextual coaching brief right before starting a session.

    Uses project context, workflow hints, and prior team evidence
    to suggest a strong opening pattern, tool/model choices, and pitfalls.
    """
    if not _has_engineer_auth():
        return "Error: PRIMER_DEVICE_TOKEN or PRIMER_API_KEY not set"
    try:
        params = {
            key: value
            for key, value in {
                "project_name": project_name,
                "workflow_hint": workflow_hint,
                "task_hint": task_hint,
                "days": days,
            }.items()
            if value is not None
        }
        resp = httpx.get(
            f"{SERVER_URL}/api/v1/analytics/coaching/session-start",
            params=params,
            headers=_engineer_headers(),
            timeout=30,
        )
        if resp.status_code == 200:
            return _render_coaching_brief(resp.json())
        return f"Error: {resp.status_code} - {resp.text}"
    except httpx.RequestError as e:
        return f"Error connecting to server: {e}"


def primer_live_session_signals(
    session_id: str | None = None,
    transcript_path: str | None = None,
) -> str:
    """Analyze the current in-progress local session for live risk and friction signals.

    This is computed locally from the active transcript so it can be called repeatedly
    during a session without waiting for end-of-session ingest.
    """
    try:
        data = get_live_session_signals(session_id=session_id, transcript_path=transcript_path)
    except ValueError as exc:
        return f"Error: {exc}"
    lines = ["## Live Session Signals\n"]
    lines.append(f"**Risk**: {data.risk_level}\n")
    lines.append(f"**Satisfaction**: {data.satisfaction_signal}\n")
    if data.project_name:
        lines.append(f"**Project**: {data.project_name}\n")
    lines.append(f"**Session**: {data.session_id} ({data.agent_type})\n")
    for signal in data.signals:
        lines.append(f"### [{signal.severity}] {signal.title}")
        lines.append(f"- {signal.detail}")
        lines.append("")
    return "\n".join(lines)


def primer_in_session_nudges(
    project_name: str | None = None,
    workflow_hint: str | None = None,
    task_hint: str | None = None,
    session_id: str | None = None,
    transcript_path: str | None = None,
) -> str:
    """Get evidence-backed nudges during an active local session.

    Combines local live-session signals with the session-start coaching brief so the
    sidecar can suggest the smallest next corrective action when the session drifts.
    """
    try:
        live_signals = get_live_session_signals(
            session_id=session_id,
            transcript_path=transcript_path,
        )
    except ValueError as exc:
        return f"Error: {exc}"

    coaching_brief = None
    if _has_engineer_auth():
        try:
            params = {
                key: value
                for key, value in {
                    "project_name": project_name or live_signals.project_name,
                    "workflow_hint": workflow_hint,
                    "task_hint": task_hint,
                    "days": 90,
                }.items()
                if value is not None
            }
            resp = httpx.get(
                f"{SERVER_URL}/api/v1/analytics/coaching/session-start",
                params=params,
                headers=_engineer_headers(),
                timeout=30,
            )
            if resp.status_code == 200:
                from primer.common.schemas import CoachingBrief

                coaching_brief = CoachingBrief.model_validate(resp.json())
        except (ValidationError, ValueError, httpx.RequestError, json.JSONDecodeError):
            coaching_brief = None

    data = build_in_session_nudges(live_signals, coaching_brief)
    lines = ["## In-Session Workflow Nudges\n"]
    lines.append(f"**Risk**: {data.risk_level}\n")
    if data.project_name:
        lines.append(f"**Project**: {data.project_name}\n")
    if not data.nudges:
        lines.append("No nudges right now.\n")
        return "\n".join(lines)
    for nudge in data.nudges:
        lines.append(f"### [{nudge.severity}] {nudge.title}")
        lines.append(f"- {nudge.message}")
        if nudge.rationale:
            lines.append(f"- Why now: {nudge.rationale}")
        for action in nudge.suggested_actions:
            lines.append(f"- Try: {action}")
        lines.append("")
    return "\n".join(lines)


def primer_personal_recaps(period: str = "both") -> str:
    """Get your daily and weekly personal recap inside the sidecar."""
    if not _has_engineer_auth():
        return "Error: PRIMER_DEVICE_TOKEN or PRIMER_API_KEY not set"
    if period not in {"daily", "weekly", "both"}:
        return "Error: period must be one of daily, weekly, both"
    try:
        resp = httpx.get(
            f"{SERVER_URL}/api/v1/analytics/personal-recaps",
            headers=_engineer_headers(),
            timeout=30,
        )
        if resp.status_code != 200:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        lines = ["## Personal Recaps\n"]
        periods = ["daily", "weekly"] if period == "both" else [period]
        for selected in periods:
            recap = data[selected]
            lines.append(f"### {selected.title()}")
            lines.append(f"**{recap['headline']}**")
            lines.append(recap["summary"])
            if recap.get("wins"):
                lines.append("Wins:")
                for item in recap["wins"]:
                    lines.append(f"- {item}")
            if recap.get("watchouts"):
                lines.append("Watchouts:")
                for item in recap["watchouts"]:
                    lines.append(f"- {item}")
            if recap.get("next_steps"):
                lines.append("Next steps:")
                for item in recap["next_steps"]:
                    lines.append(f"- {item}")
            lines.append("")
        return "\n".join(lines)
    except httpx.RequestError as e:
        return f"Error connecting to server: {e}"


def primer_manager_review_pack(team_id: str | None = None, days: int = 7) -> str:
    """Get a weekly manager review pack combining quality, friction, growth, and cost."""
    if not _has_engineer_auth() and not ADMIN_API_KEY:
        return "Error: PRIMER_DEVICE_TOKEN, PRIMER_API_KEY, or PRIMER_ADMIN_API_KEY not set"
    try:
        params = {"days": days}
        if team_id:
            params["team_id"] = team_id
        resp = httpx.get(
            f"{SERVER_URL}/api/v1/analytics/manager-review-pack",
            headers=_admin_headers(),
            params=params,
            timeout=30,
        )
        if resp.status_code != 200:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        lines = ["## Weekly Manager Review Pack\n"]
        lines.append(f"**Scope**: {data['scope_label']}\n")
        lines.append(f"**Window**: {data['period_start']} to {data['period_end']}\n")
        lines.append(f"**Headline**: {data['headline']}\n")
        for section in data.get("sections", []):
            lines.append(f"### {section['title']}")
            lines.append(section["summary"])
            for bullet in section.get("bullets", []):
                lines.append(f"- {bullet}")
            lines.append("")
        if data.get("recommended_actions"):
            lines.append("### Recommended Actions")
            for action in data["recommended_actions"]:
                lines.append(f"- {action}")
            lines.append("")
        return "\n".join(lines)
    except httpx.RequestError as e:
        return f"Error connecting to server: {e}"
