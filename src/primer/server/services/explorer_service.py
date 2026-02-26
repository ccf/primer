"""Conversational data explorer service.

Implements a streaming tool-use chat loop using the Anthropic Messages API.
Tools are mapped to existing analytics service functions, enabling natural
language exploration of Claude Code usage data.
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from primer.common.config import settings

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

TOOL_DEFINITIONS = [
    {
        "name": "get_overview_stats",
        "description": (
            "Get high-level KPIs: total sessions, active engineers, estimated cost, "
            "success rate, avg session duration, outcome distribution, health score."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_friction_report",
        "description": (
            "Get friction types and counts. Shows what's slowing engineers down: "
            "tool errors, permission issues, context limits, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_cost_breakdown",
        "description": ("Get cost analytics: total cost, cost by model, and daily cost trend."),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_tool_rankings",
        "description": ("Get top tools by usage: tool name, total calls, and session count."),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max tools to return (default 20)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_engineer_leaderboard",
        "description": (
            "Get per-engineer stats: sessions, tokens, cost, success rate, top tools. "
            "Sortable by total_sessions, total_tokens, estimated_cost, success_rate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sort_by": {
                    "type": "string",
                    "description": (
                        "Sort: total_sessions, total_tokens, estimated_cost, success_rate"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Max engineers to return (default 20)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_daily_trends",
        "description": ("Get daily session, message, and tool call counts with success rates."),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 30)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_session_health",
        "description": (
            "Get session health insights: satisfaction summary, friction clusters, "
            "health score distribution, permission mode analysis, cache efficiency."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_productivity",
        "description": (
            "Get productivity/ROI metrics: sessions per engineer per day, avg cost per session, "
            "time saved, adoption rate, power users, ROI ratio."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "search_sessions",
        "description": (
            "Search sessions by project name, outcome, session type, or keyword in first prompt. "
            "Returns up to 20 matching sessions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Filter by project name (substring match)",
                },
                "outcome": {
                    "type": "string",
                    "description": "Filter by outcome: success, partial, failure",
                },
                "session_type": {
                    "type": "string",
                    "description": "Filter by session type: feature, debugging, refactoring, etc.",
                },
                "keyword": {
                    "type": "string",
                    "description": "Search keyword in first_prompt",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_session_detail",
        "description": (
            "Get full details for a single session by ID: duration, tokens, tools used, "
            "facets (outcome, friction, satisfaction), model usage."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session UUID to look up",
                },
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "get_pr_comparison",
        "description": (
            "Compare Claude-assisted PRs vs non-Claude PRs: merge rate, review comments, "
            "time to merge, size"
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_repo_readiness",
        "description": (
            "Get AI readiness scores for repositories: checks for CLAUDE.md, "
            ".claude/ directory, AGENTS.md"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max repositories to return (default 20)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "search_pull_requests",
        "description": (
            "Search pull requests by repo, state, author. Shows title, "
            "additions/deletions, review comments, merge status"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Filter by repository name (substring match on full_name)",
                },
                "state": {
                    "type": "string",
                    "description": "Filter by state: open, closed, merged",
                },
                "author": {
                    "type": "string",
                    "description": "Filter by engineer name (substring match)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max pull requests to return (default 20)",
                },
            },
            "required": [],
        },
    },
]


def _execute_tool(
    tool_name: str,
    tool_input: dict,
    db: Session,
    team_id: str | None,
    engineer_id: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> str:
    """Execute a tool and return JSON string result."""
    from primer.common.models import Engineer, SessionFacets, ToolUsage
    from primer.common.models import Session as SessionModel
    from primer.server.services.analytics_service import (
        get_cost_analytics,
        get_daily_stats,
        get_engineer_analytics,
        get_friction_report,
        get_overview,
        get_productivity_metrics,
        get_tool_rankings,
    )
    from primer.server.services.session_insights_service import get_session_insights

    kwargs = {
        "db": db,
        "team_id": team_id,
        "engineer_id": engineer_id,
        "start_date": start_date,
        "end_date": end_date,
    }

    if tool_name == "get_overview_stats":
        result = get_overview(**kwargs)
        return result.model_dump_json()

    if tool_name == "get_friction_report":
        result = get_friction_report(**kwargs)
        return json.dumps([r.model_dump() for r in result], default=str)

    if tool_name == "get_cost_breakdown":
        result = get_cost_analytics(**kwargs)
        return result.model_dump_json()

    if tool_name == "get_tool_rankings":
        limit = tool_input.get("limit", 20)
        result = get_tool_rankings(**kwargs, limit=limit)
        return json.dumps([r.model_dump() for r in result], default=str)

    if tool_name == "get_engineer_leaderboard":
        sort_by = tool_input.get("sort_by", "total_sessions")
        limit = tool_input.get("limit", 20)
        result = get_engineer_analytics(**kwargs, sort_by=sort_by, limit=limit)
        return result.model_dump_json()

    if tool_name == "get_daily_trends":
        days = tool_input.get("days", 30)
        result = get_daily_stats(**kwargs, days=days)
        return json.dumps([r.model_dump() for r in result], default=str)

    if tool_name == "get_session_health":
        result = get_session_insights(**kwargs)
        return result.model_dump_json()

    if tool_name == "get_productivity":
        result = get_productivity_metrics(**kwargs)
        return result.model_dump_json()

    if tool_name == "search_sessions":
        q = db.query(SessionModel)
        if engineer_id:
            q = q.filter(SessionModel.engineer_id == engineer_id)
        elif team_id:
            q = q.join(Engineer).filter(Engineer.team_id == team_id)
        if start_date:
            q = q.filter(SessionModel.started_at >= start_date)
        if end_date:
            q = q.filter(SessionModel.started_at <= end_date)

        project = tool_input.get("project")
        if project:
            q = q.filter(SessionModel.project_name.ilike(f"%{project}%"))
        keyword = tool_input.get("keyword")
        if keyword:
            q = q.filter(SessionModel.first_prompt.ilike(f"%{keyword}%"))

        # Join facets for outcome/session_type filtering
        outcome = tool_input.get("outcome")
        session_type = tool_input.get("session_type")
        if outcome or session_type:
            q = q.join(SessionFacets, SessionFacets.session_id == SessionModel.id)
            if outcome:
                q = q.filter(SessionFacets.outcome == outcome)
            if session_type:
                q = q.filter(SessionFacets.session_type == session_type)

        q = q.order_by(SessionModel.started_at.desc()).limit(20)
        sessions = q.all()
        return json.dumps(
            [
                {
                    "id": s.id,
                    "project_name": s.project_name,
                    "first_prompt": (s.first_prompt[:200] if s.first_prompt else None),
                    "duration_seconds": s.duration_seconds,
                    "message_count": s.message_count,
                    "tool_call_count": s.tool_call_count,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "primary_model": s.primary_model,
                }
                for s in sessions
            ],
            default=str,
        )

    if tool_name == "get_session_detail":
        session_id = tool_input.get("session_id", "")
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            return json.dumps({"error": "Session not found"})

        # Check scope
        if engineer_id and session.engineer_id != engineer_id:
            return json.dumps({"error": "Access denied"})
        if team_id:
            eng = db.query(Engineer).filter(Engineer.id == session.engineer_id).first()
            if not eng or eng.team_id != team_id:
                return json.dumps({"error": "Access denied"})

        facets = db.query(SessionFacets).filter(SessionFacets.session_id == session_id).first()
        tools = db.query(ToolUsage).filter(ToolUsage.session_id == session_id).all()

        return json.dumps(
            {
                "id": session.id,
                "project_name": session.project_name,
                "first_prompt": session.first_prompt,
                "summary": session.summary,
                "duration_seconds": session.duration_seconds,
                "message_count": session.message_count,
                "tool_call_count": session.tool_call_count,
                "input_tokens": session.input_tokens,
                "output_tokens": session.output_tokens,
                "primary_model": session.primary_model,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "end_reason": session.end_reason,
                "facets": {
                    "outcome": facets.outcome,
                    "session_type": facets.session_type,
                    "friction_counts": facets.friction_counts,
                    "underlying_goal": facets.underlying_goal,
                    "brief_summary": facets.brief_summary,
                }
                if facets
                else None,
                "tools": [{"tool_name": t.tool_name, "call_count": t.call_count} for t in tools],
            },
            default=str,
        )

    if tool_name == "get_pr_comparison":
        from primer.server.services.quality_service import get_claude_pr_comparison

        result = get_claude_pr_comparison(**kwargs)
        return result.model_dump_json()

    if tool_name == "get_repo_readiness":
        from primer.common.models import GitRepository

        limit = tool_input.get("limit", 20)
        q = db.query(GitRepository).order_by(GitRepository.ai_readiness_score.desc().nullslast())
        # Scope: only repos linked to sessions visible to this user
        if engineer_id:
            repo_ids = db.query(SessionModel.repository_id).filter(
                SessionModel.engineer_id == engineer_id,
                SessionModel.repository_id.isnot(None),
            )
            q = q.filter(GitRepository.id.in_(repo_ids))
        elif team_id:
            repo_ids = (
                db.query(SessionModel.repository_id)
                .join(Engineer, Engineer.id == SessionModel.engineer_id)
                .filter(
                    Engineer.team_id == team_id,
                    SessionModel.repository_id.isnot(None),
                )
            )
            q = q.filter(GitRepository.id.in_(repo_ids))
        repos = q.limit(limit).all()
        return json.dumps(
            [
                {
                    "full_name": r.full_name,
                    "ai_readiness_score": r.ai_readiness_score,
                    "has_claude_md": r.has_claude_md,
                    "has_agents_md": r.has_agents_md,
                    "has_claude_dir": r.has_claude_dir,
                }
                for r in repos
            ],
            default=str,
        )

    if tool_name == "search_pull_requests":
        from primer.server.services.quality_service import _build_pr_scope_query

        limit = tool_input.get("limit", 20)
        q = _build_pr_scope_query(db, team_id, engineer_id, start_date, end_date)

        # Optional filters
        from primer.common.models import GitRepository, PullRequest

        repo = tool_input.get("repo")
        if repo:
            q = q.filter(GitRepository.full_name.ilike(f"%{repo}%"))
        state = tool_input.get("state")
        if state:
            q = q.filter(PullRequest.state == state)
        author = tool_input.get("author")
        if author:
            q = q.filter(Engineer.name.ilike(f"%{author}%"))

        q = q.order_by(PullRequest.pr_created_at.desc()).limit(limit)
        rows = q.all()
        return json.dumps(
            [
                {
                    "repository": repo_name,
                    "pr_number": pr.github_pr_number,
                    "title": pr.title,
                    "state": pr.state,
                    "author": author_name,
                    "additions": pr.additions,
                    "deletions": pr.deletions,
                    "review_comments_count": pr.review_comments_count,
                    "pr_created_at": (pr.pr_created_at.isoformat() if pr.pr_created_at else None),
                    "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                }
                for pr, repo_name, author_name in rows
            ],
            default=str,
        )

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def _build_system_prompt(
    overview_snapshot: str,
    role: str,
    scope_desc: str,
) -> str:
    """Build the system prompt for the explorer."""
    return f"""You are an analytics advisor for Primer, a Claude Code usage insights platform.
You help users explore their engineering team's Claude Code usage data through conversation.

## Your role
- Answer questions about Claude Code usage patterns, costs, productivity, and friction
- You can also answer questions about GitHub pull requests, code quality,
  and repository AI readiness
- Provide concise, data-driven answers with specific numbers
- Use markdown formatting for clarity (bold key metrics, use tables for comparisons)
- When relevant, suggest which dashboard page has more detail

## Writing rules
- Be concise — lead with the key insight, then supporting data
- Use bullet points and tables, not long paragraphs
- Round costs to 2 decimal places, percentages to 1 decimal place
- When comparing periods, state the direction and magnitude of change

## Current user context
- Role: {role}
- Data scope: {scope_desc}

## Pre-loaded overview snapshot
This is a snapshot of current KPIs so you can answer simple questions without tool calls:
{overview_snapshot}

## Available tools
You have tools to query analytics data. Use them when the overview
snapshot doesn't have enough detail. Only call tools when needed — the
overview snapshot covers many common questions."""


async def stream_explorer_chat(
    db: Session,
    messages: list[dict],
    auth_role: str,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> AsyncGenerator[str, None]:
    """Stream an explorer chat response as SSE events.

    Yields SSE-formatted strings (event: type\\ndata: json\\n\\n).
    """
    if not settings.anthropic_api_key:
        yield _sse_event("error", {"message": "PRIMER_ANTHROPIC_API_KEY not configured"})
        return

    # Pre-load overview for the system prompt
    from primer.server.services.analytics_service import get_overview

    try:
        overview = await asyncio.to_thread(
            get_overview,
            db,
            team_id=team_id,
            engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        )
        overview_snapshot = overview.model_dump_json()
    except Exception:
        overview_snapshot = "{}"

    # Build scope description
    if engineer_id:
        scope_desc = "Your personal data only"
    elif team_id:
        scope_desc = f"Team {team_id} data"
    else:
        scope_desc = "Organization-wide data"

    system_prompt = _build_system_prompt(overview_snapshot, auth_role, scope_desc)

    # Convert messages to Anthropic format
    api_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant"):
            api_messages.append({"role": role, "content": content})

    max_rounds = settings.explorer_max_tool_rounds
    round_count = 0

    while round_count <= max_rounds:
        # Call Anthropic API with streaming
        request_body = {
            "model": settings.explorer_model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": api_messages,
            "tools": TOOL_DEFINITIONS,
            "stream": True,
        }

        try:
            async with (
                httpx.AsyncClient(timeout=60.0) as client,
                client.stream(
                    "POST",
                    ANTHROPIC_API_URL,
                    json=request_body,
                    headers={
                        "x-api-key": settings.anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                ) as response,
            ):
                if response.status_code != 200:
                    body = await response.aread()
                    logger.error("Anthropic API error %d: %s", response.status_code, body)
                    yield _sse_event(
                        "error",
                        {"message": f"API error: {response.status_code}"},
                    )
                    return

                # Parse the SSE stream from Anthropic
                collected_text = ""
                tool_uses: list[dict] = []
                stop_reason = None
                current_tool_id = None
                current_tool_name = None
                current_tool_input_json = ""

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    event_type = event.get("type")

                    if event_type == "content_block_start":
                        block = event.get("content_block", {})
                        if block.get("type") == "tool_use":
                            current_tool_id = block.get("id")
                            current_tool_name = block.get("name")
                            current_tool_input_json = ""
                            yield _sse_event(
                                "tool_call",
                                {"name": current_tool_name, "input": {}},
                            )

                    elif event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                collected_text += text
                                yield _sse_event("text", {"content": text})
                        elif delta.get("type") == "input_json_delta":
                            current_tool_input_json += delta.get("partial_json", "")

                    elif event_type == "content_block_stop":
                        if current_tool_id and current_tool_name:
                            try:
                                tool_input = json.loads(current_tool_input_json or "{}")
                            except json.JSONDecodeError:
                                tool_input = {}
                            tool_uses.append(
                                {
                                    "id": current_tool_id,
                                    "name": current_tool_name,
                                    "input": tool_input,
                                }
                            )
                            current_tool_id = None
                            current_tool_name = None
                            current_tool_input_json = ""

                    elif event_type == "message_delta":
                        stop_reason = event.get("delta", {}).get("stop_reason")

        except httpx.HTTPError as e:
            logger.exception("Anthropic API request failed")
            yield _sse_event("error", {"message": f"Request failed: {e}"})
            return

        # If end_turn or no tool calls, we're done
        if stop_reason != "tool_use" or not tool_uses:
            break

        round_count += 1
        if round_count > max_rounds:
            yield _sse_event("text", {"content": "\n\n*Reached maximum analysis depth.*"})
            break

        # Build assistant message with text + tool_use blocks
        assistant_content: list[dict] = []
        if collected_text:
            assistant_content.append({"type": "text", "text": collected_text})
        for tu in tool_uses:
            assistant_content.append(
                {
                    "type": "tool_use",
                    "id": tu["id"],
                    "name": tu["name"],
                    "input": tu["input"],
                }
            )
        api_messages.append({"role": "assistant", "content": assistant_content})

        # Execute tools and build tool_result message
        tool_results_content: list[dict] = []
        for tu in tool_uses:
            try:
                result_str = await asyncio.to_thread(
                    _execute_tool,
                    tu["name"],
                    tu["input"],
                    db,
                    team_id,
                    engineer_id,
                    start_date,
                    end_date,
                )
                # Truncate very large results with valid JSON
                if len(result_str) > 20000:
                    result_str = json.dumps({"truncated": True, "data": result_str[:20000]})
            except Exception:
                logger.exception("Tool execution failed: %s", tu["name"])
                result_str = json.dumps({"error": f"Tool {tu['name']} failed"})

            yield _sse_event(
                "tool_result",
                {"name": tu["name"], "summary": _summarize_result(result_str)},
            )
            tool_results_content.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": result_str,
                }
            )

        api_messages.append({"role": "user", "content": tool_results_content})

        # Reset for next round
        collected_text = ""
        tool_uses = []
        stop_reason = None

    yield _sse_event("done", {})


def _sse_event(event_type: str, data: dict) -> str:
    """Format an SSE event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _summarize_result(result_str: str) -> str:
    """Create a short summary of a tool result for the UI."""
    try:
        data = json.loads(result_str)
    except (json.JSONDecodeError, TypeError):
        return "Data retrieved"

    if isinstance(data, dict):
        if "error" in data:
            return f"Error: {data['error']}"
        if "total_sessions" in data:
            parts = [f"{data['total_sessions']} sessions"]
            if data.get("success_rate") is not None:
                parts.append(f"{data['success_rate']:.0%} success")
            if data.get("estimated_cost") is not None:
                parts.append(f"${data['estimated_cost']:.2f}")
            return ", ".join(parts)
        if "total_estimated_cost" in data:
            return f"${data['total_estimated_cost']:.2f} total cost"
        if "sessions_analyzed" in data:
            return f"{data['sessions_analyzed']} sessions analyzed"
    elif isinstance(data, list):
        return f"{len(data)} items"

    return "Data retrieved"
