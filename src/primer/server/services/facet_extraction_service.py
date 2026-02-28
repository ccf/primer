"""Extract session facets via LLM analysis of transcript messages.

Replicates the facet extraction that Claude Code performs during `/insights`,
but runs at ingest time so facets are always available.
"""

import json
import logging
import re

import httpx
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import SessionLocal
from primer.common.models import Session as SessionModel
from primer.common.models import SessionFacets, SessionMessage
from primer.common.schemas import SessionFacetsPayload

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Matches Claude Code's facet extraction prompt
EXTRACTION_PROMPT = """\
Analyze this AI coding assistant session and extract structured facets.

CRITICAL GUIDELINES:
1. **goal_categories**: Count ONLY what the USER explicitly asked for.
   - DO NOT count the assistant's autonomous codebase exploration
   - DO NOT count work the assistant decided to do on its own
   - ONLY count when user says "can you...", "please...", "I need...", "let's..."
2. **user_satisfaction_counts**: Base ONLY on explicit user signals.
   - "Yay!", "great!", "perfect!" → happy
   - "thanks", "looks good", "that works" → satisfied
   - "ok, now let's..." (continuing without complaint) → likely_satisfied
   - "that's not right", "try again" → dissatisfied
   - "this is broken", "I give up" → frustrated
3. **friction_counts**: Be specific about what went wrong.
   - misunderstood_request: Assistant interpreted incorrectly
   - wrong_approach: Right goal, wrong solution method
   - buggy_code: Code didn't work correctly
   - user_rejected_action: User said no/stop to a tool call
   - excessive_changes: Over-engineered or changed too much
   - assistant_got_blocked: Assistant couldn't proceed
   - wrong_file_or_location: Edited wrong file or location
   - slow_or_verbose: Took too long or was too wordy
   - tool_failed: A tool call failed
   - external_tool_issue: External tool/service had issues
4. If very short or just warmup, use warmup_minimal for goal_category

Return a single JSON object with these fields:
{
  "underlying_goal": "What the user fundamentally wanted to achieve",
  "goal_categories": {"category_name": count, ...},
  "outcome": "fully_achieved|mostly_achieved|partially_achieved|not_achieved",
  "user_satisfaction_counts": {"satisfied|likely_satisfied|dissatisfied": N},
  "agent_helpfulness": "unhelpful|slightly_helpful|moderately_helpful|very_helpful",
  "session_type": "single_task|multi_task|iterative_refinement|exploration",
  "friction_counts": {"friction_type": count, ...},
  "friction_detail": "Description of friction events or empty string",
  "primary_success": "none|correct_code_edits|multi_file_changes|good_debugging",
  "brief_summary": "One sentence: what user wanted and whether they got it"
}

Respond with ONLY the JSON object, no other text."""

# Minimum session requirements (matches Claude Code's filters)
MIN_USER_MESSAGES = 2
MIN_DURATION_SECONDS = 60


def _build_transcript_text(messages: list[dict]) -> str:
    """Build a readable transcript from session messages for the LLM."""
    lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "unknown")
        text = msg.get("content_text") or ""

        if role == "human":
            lines.append(f"User: {text}")
        elif role == "assistant":
            parts = []
            if text:
                parts.append(text)
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                for tc in tool_calls:
                    name = tc.get("name", "unknown")
                    preview = tc.get("input_preview", "")
                    parts.append(f"[Tool: {name}({preview[:200]})]")
            if parts:
                lines.append(f"Assistant: {' '.join(parts)}")
        elif role == "tool_result":
            tool_results = msg.get("tool_results")
            if tool_results:
                for tr in tool_results:
                    name = tr.get("name", "unknown")
                    output = tr.get("output_preview", "")
                    lines.append(f"[Result from {name}: {output[:200]}]")

    # Truncate to ~60k chars to stay within context limits
    transcript = "\n".join(lines)
    if len(transcript) > 60000:
        transcript = transcript[:60000] + "\n...[truncated]"
    return transcript


def _parse_facets_response(text: str) -> dict | None:
    """Extract JSON object from LLM response text."""
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None

    # Validate required fields
    if not isinstance(data.get("underlying_goal"), str):
        return None
    if not isinstance(data.get("outcome"), str):
        return None
    if not isinstance(data.get("brief_summary"), str):
        return None

    return data


def _facets_dict_to_payload(data: dict) -> SessionFacetsPayload:
    """Convert raw LLM facets dict to a SessionFacetsPayload."""
    # Convert goal_categories from dict[str, int] to list[str]
    goal_cats = data.get("goal_categories")
    if isinstance(goal_cats, dict):
        goal_cats = list(goal_cats.keys())
    elif not isinstance(goal_cats, list):
        goal_cats = None

    return SessionFacetsPayload(
        underlying_goal=data.get("underlying_goal"),
        goal_categories=goal_cats,
        outcome=data.get("outcome"),
        session_type=data.get("session_type"),
        primary_success=data.get("primary_success"),
        agent_helpfulness=data.get("agent_helpfulness"),
        brief_summary=data.get("brief_summary"),
        user_satisfaction_counts=data.get("user_satisfaction_counts"),
        friction_counts=data.get("friction_counts"),
        friction_detail=data.get("friction_detail"),
    )


def extract_facets_from_messages(
    messages: list[dict],
) -> SessionFacetsPayload | None:
    """Call Anthropic API to extract facets from session messages.

    Args:
        messages: List of message dicts with role, content_text, tool_calls, etc.

    Returns:
        SessionFacetsPayload if extraction succeeds, None otherwise.
    """
    if not settings.anthropic_api_key:
        logger.debug("No Anthropic API key configured, skipping facet extraction")
        return None

    transcript = _build_transcript_text(messages)
    if not transcript.strip():
        return None

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                ANTHROPIC_API_URL,
                json={
                    "model": settings.facet_extraction_model,
                    "max_tokens": 4096,
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                f"{EXTRACTION_PROMPT}\n\n--- SESSION TRANSCRIPT ---\n{transcript}"
                            ),
                        }
                    ],
                },
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )

        if resp.status_code != 200:
            logger.error(
                "Facet extraction API error %d: %s",
                resp.status_code,
                resp.text[:500],
            )
            return None

        result = resp.json()
        content_blocks = result.get("content", [])
        text = ""
        for block in content_blocks:
            if block.get("type") == "text":
                text += block.get("text", "")

        data = _parse_facets_response(text)
        if not data:
            logger.warning("Failed to parse facets from LLM response")
            return None

        return _facets_dict_to_payload(data)

    except httpx.HTTPError:
        logger.exception("Facet extraction request failed")
        return None
    except Exception:
        logger.exception("Unexpected error during facet extraction")
        return None


def extract_and_store_facets(session_id: str, messages: list[dict]) -> bool:
    """Extract facets and store them in the database.

    Designed to run as a background task after ingest.

    Args:
        session_id: The session to extract facets for.
        messages: List of message dicts from the ingest payload.

    Returns:
        True if facets were extracted and stored.
    """
    facets = extract_facets_from_messages(messages)
    if not facets:
        return False

    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            logger.warning("Session %s not found for facet storage", session_id)
            return False

        # Don't overwrite existing facets
        if session.has_facets:
            return False

        existing = db.query(SessionFacets).filter(SessionFacets.session_id == session_id).first()
        if existing:
            record = existing
        else:
            record = SessionFacets(session_id=session_id)
            db.add(record)

        for field_name in [
            "underlying_goal",
            "goal_categories",
            "outcome",
            "session_type",
            "primary_success",
            "agent_helpfulness",
            "brief_summary",
            "user_satisfaction_counts",
            "friction_counts",
            "friction_detail",
        ]:
            value = getattr(facets, field_name, None)
            if value is not None:
                setattr(record, field_name, value)

        session.has_facets = True
        db.commit()
        logger.info("Extracted and stored facets for session %s", session_id)
        return True
    except Exception:
        db.rollback()
        logger.exception("Failed to store facets for session %s", session_id)
        return False
    finally:
        db.close()


def backfill_facets(db: Session, limit: int = 50) -> dict:
    """Extract facets for sessions that have messages but no facets.

    Args:
        db: Database session (for querying, not for writes — each
            extraction creates its own session for writes).
        limit: Max sessions to process.

    Returns:
        Dict with counts: processed, success, skipped, failed.
    """
    # Find sessions with messages but no facets
    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.has_facets.is_(False),
            SessionModel.user_message_count >= MIN_USER_MESSAGES,
            SessionModel.duration_seconds >= MIN_DURATION_SECONDS,
        )
        .order_by(SessionModel.started_at.desc())
        .limit(limit)
        .all()
    )

    result = {"processed": 0, "success": 0, "skipped": 0, "failed": 0}

    for session in sessions:
        result["processed"] += 1

        # Load messages for this session
        msg_rows = (
            db.query(SessionMessage)
            .filter(SessionMessage.session_id == session.id)
            .order_by(SessionMessage.ordinal)
            .all()
        )

        if not msg_rows:
            result["skipped"] += 1
            continue

        messages = [
            {
                "role": m.role,
                "content_text": m.content_text,
                "tool_calls": m.tool_calls,
                "tool_results": m.tool_results,
            }
            for m in msg_rows
        ]

        success = extract_and_store_facets(session.id, messages)
        if success:
            result["success"] += 1
        else:
            result["failed"] += 1

    return result
