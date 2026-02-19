"""LLM-generated narrative insights service.

Gathers data from existing analytics services, builds prompts, calls the
Anthropic API via httpx, and caches results in NarrativeCache.
"""

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.models import Engineer, NarrativeCache, Team
from primer.common.schemas import NarrativeResponse, NarrativeSection

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
NARRATIVE_MODEL = "claude-sonnet-4-6"
MIN_SESSIONS = 5

ENGINEER_SECTIONS = [
    "At a Glance",
    "How You Work",
    "Strengths & Wins",
    "Friction & Pain Points",
    "Growth Opportunities",
    "Tips & Recommendations",
]

TEAM_SECTIONS = [
    "Team Overview",
    "Usage Patterns",
    "Standout Contributors",
    "Friction Hotspots",
    "Tool Adoption",
    "Recommendations",
]

ORG_SECTIONS = [
    "Organization Health",
    "Team Comparison",
    "Cost Analysis",
    "Adoption Trends",
    "Strategic Recommendations",
]


def _gather_data(
    db: Session,
    scope: str,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict:
    """Gather analytics data from existing services into a prompt-ready dict."""
    from primer.server.services.analytics_service import (
        get_bottleneck_analytics,
        get_cost_analytics,
        get_engineer_analytics,
        get_friction_report,
        get_overview,
        get_productivity_metrics,
        get_tool_rankings,
    )
    from primer.server.services.maturity_service import get_maturity_analytics
    from primer.server.services.session_insights_service import get_session_insights

    # Scope filtering
    tid = team_id if scope in ("team", "org") else None
    eid = engineer_id if scope == "engineer" else None

    # For org scope, pass no filters
    if scope == "org":
        tid = None
        eid = None

    overview = get_overview(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )

    data: dict = {
        "total_sessions": overview.total_sessions,
        "total_engineers": overview.total_engineers,
        "total_messages": overview.total_messages,
        "total_tool_calls": overview.total_tool_calls,
        "estimated_cost": overview.estimated_cost,
        "success_rate": overview.success_rate,
        "avg_session_duration_seconds": overview.avg_session_duration,
        "avg_messages_per_session": overview.avg_messages_per_session,
        "top_session_types": dict(
            sorted(overview.session_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ),
        "outcome_counts": overview.outcome_counts,
        "cache_hit_rate": overview.cache_hit_rate,
        "avg_health_score": overview.avg_health_score,
    }

    # Friction (top 5)
    friction = get_friction_report(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )
    data["top_friction"] = [{"type": f.friction_type, "count": f.count} for f in friction[:5]]

    # Top tools (top 10)
    tools = get_tool_rankings(
        db,
        team_id=tid,
        limit=10,
        engineer_id=eid,
        start_date=start_date,
        end_date=end_date,
    )
    data["top_tools"] = [{"name": t.tool_name, "calls": t.total_calls} for t in tools[:10]]

    # Cost analytics (top 3 models)
    costs = get_cost_analytics(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )
    data["total_cost"] = costs.total_estimated_cost
    data["top_models_by_cost"] = [
        {"model": m.model_name, "cost": round(m.estimated_cost, 4)}
        for m in costs.model_breakdown[:3]
    ]

    # Productivity
    productivity = get_productivity_metrics(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )
    data["sessions_per_engineer_per_day"] = productivity.sessions_per_engineer_per_day
    data["adoption_rate"] = productivity.adoption_rate
    data["roi_ratio"] = productivity.roi_ratio
    data["estimated_time_saved_hours"] = productivity.estimated_time_saved_hours

    # Session insights
    insights = get_session_insights(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )
    data["satisfaction_rate"] = insights.satisfaction.satisfaction_rate
    data["health_score"] = (
        insights.health_distribution.avg_score if insights.health_distribution else None
    )
    data["top_end_reasons"] = [
        {"reason": er.end_reason, "count": er.count} for er in insights.end_reasons[:5]
    ]

    # Bottleneck analytics
    bottlenecks = get_bottleneck_analytics(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )
    data["overall_friction_rate"] = bottlenecks.overall_friction_rate
    data["top_friction_impacts"] = [
        {
            "type": fi.friction_type,
            "occurrences": fi.occurrence_count,
            "impact_score": fi.impact_score,
        }
        for fi in bottlenecks.friction_impacts[:3]
    ]

    # Maturity
    maturity = get_maturity_analytics(
        db, team_id=tid, engineer_id=eid, start_date=start_date, end_date=end_date
    )
    data["avg_leverage_score"] = maturity.avg_leverage_score
    data["orchestration_adoption_rate"] = maturity.orchestration_adoption_rate

    # Scope-specific additions
    if scope == "engineer":
        from primer.server.services.insights_service import (
            get_config_optimization,
            get_personalized_tips,
        )

        config_opt = get_config_optimization(
            db, team_id=None, engineer_id=eid, start_date=start_date, end_date=end_date
        )
        data["config_suggestions"] = [
            {"title": s.title, "category": s.category} for s in config_opt.suggestions[:5]
        ]

        tips = get_personalized_tips(
            db, team_id=None, engineer_id=eid, start_date=start_date, end_date=end_date
        )
        data["personalized_tips"] = [
            {"title": t.title, "category": t.category} for t in tips.tips[:5]
        ]

    if scope in ("team", "org"):
        eng_analytics = get_engineer_analytics(
            db, team_id=tid, engineer_id=None, start_date=start_date, end_date=end_date, limit=10
        )
        data["top_engineers"] = [
            {
                "name": e.name,
                "sessions": e.total_sessions,
                "cost": round(e.estimated_cost, 4),
                "success_rate": e.success_rate,
            }
            for e in eng_analytics.engineers[:5]
        ]

    return data


def _build_prompt(scope: str, scope_label: str, data: dict) -> tuple[str, str]:
    """Build system + user prompts for the Anthropic API call."""
    sections = {
        "engineer": ENGINEER_SECTIONS,
        "team": TEAM_SECTIONS,
        "org": ORG_SECTIONS,
    }[scope]

    system_prompt = """You are an expert engineering analytics advisor for a software organization \
that uses Claude Code (Anthropic's AI coding assistant). You analyze usage data and produce \
concise, high-signal narrative reports.

Your output MUST be a valid JSON array of objects with "title" and "content" keys.

Writing style rules:
- Each section should be 1-2 short paragraphs. Separate paragraphs with a blank line.
- Lead with the single most important insight, backed by one or two key figures.
- Keep sentences short and direct. Avoid filler, caveats, and hedging language.
- Use **bold** sparingly for the most critical numbers or takeaways.
- Do NOT enumerate lists of individual people or models — synthesize patterns instead \
(e.g. "top performers average 68% success at half the cost" not a table of each person).
- Prefer ratios, percentages, and comparisons over raw counts.
- Be opinionated. State what's working and what isn't. End sections with a clear action.
- If a metric is missing or null, skip it without comment.

Do NOT wrap the JSON in code fences or add any text before/after the JSON array."""

    section_list = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(sections))

    user_prompt = f"""Generate a narrative insight report for: **{scope_label}** (scope: {scope}).

Produce exactly these sections in order:
{section_list}

Here is the analytics data:

```json
{json.dumps(data, indent=2, default=str)}
```

Return ONLY the JSON array."""

    return system_prompt, user_prompt


def _call_anthropic(system_prompt: str, user_prompt: str) -> tuple[list[dict], str, int, int]:
    """Call the Anthropic Messages API.

    Returns (sections, model, prompt_tokens, completion_tokens).
    """
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": NARRATIVE_MODEL,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )

    if response.status_code != 200:
        logger.error("Anthropic API error %d: %s", response.status_code, response.text[:500])
        raise RuntimeError(f"Anthropic API returned {response.status_code}")

    body = response.json()
    model_used = body.get("model", NARRATIVE_MODEL)
    usage = body.get("usage", {})
    prompt_tokens = usage.get("input_tokens", 0)
    completion_tokens = usage.get("output_tokens", 0)

    # Extract text content
    text = ""
    for block in body.get("content", []):
        if block.get("type") == "text":
            text += block["text"]

    # Parse JSON from response
    text = text.strip()
    # Strip code fences if present despite instructions
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    sections = json.loads(text)
    if not isinstance(sections, list):
        raise ValueError("Expected JSON array from LLM")

    return sections, model_used, prompt_tokens, completion_tokens


def _resolve_scope_label(
    db: Session, scope: str, engineer_id: str | None, team_id: str | None
) -> str:
    """Resolve a human-readable label for the scope."""
    if scope == "engineer" and engineer_id:
        eng = db.query(Engineer.name).filter(Engineer.id == engineer_id).first()
        return eng[0] if eng else "Engineer"
    if scope == "team" and team_id:
        team = db.query(Team.name).filter(Team.id == team_id).first()
        return team[0] if team else "Team"
    return "Organization"


def _date_range_key(start_date: datetime | None, end_date: datetime | None) -> str:
    """Generate a cache key component from the date range."""
    if start_date and end_date:
        return f"{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}"
    if start_date:
        return f"{start_date.strftime('%Y-%m-%d')}_now"
    return "all"


def _upsert_cache(
    db: Session,
    scope: str,
    scope_id: str | None,
    dr_key: str,
    sections: list[dict],
    data_summary: dict,
    model_used: str,
    prompt_tokens: int,
    completion_tokens: int,
    now: datetime,
) -> None:
    """Upsert a narrative cache entry, handling concurrent insert races."""
    from sqlalchemy.exc import IntegrityError

    def _update_existing(entry: NarrativeCache) -> None:
        entry.sections = sections
        entry.data_summary = data_summary
        entry.model_used = model_used
        entry.prompt_tokens = prompt_tokens
        entry.completion_tokens = completion_tokens
        entry.created_at = now
        entry.expires_at = now + timedelta(hours=settings.narrative_cache_ttl_hours)

    existing = (
        db.query(NarrativeCache)
        .filter(
            NarrativeCache.scope == scope,
            NarrativeCache.scope_id == scope_id if scope_id else NarrativeCache.scope_id.is_(None),
            NarrativeCache.date_range_key == dr_key,
        )
        .first()
    )

    if existing:
        _update_existing(existing)
        db.flush()
        return

    try:
        entry = NarrativeCache(
            id=str(uuid.uuid4()),
            scope=scope,
            scope_id=scope_id,
            date_range_key=dr_key,
            sections=sections,
            data_summary=data_summary,
            model_used=model_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            created_at=now,
            expires_at=now + timedelta(hours=settings.narrative_cache_ttl_hours),
        )
        db.add(entry)
        db.flush()
    except IntegrityError:
        db.rollback()
        # Concurrent insert won the race — update the existing row instead
        existing = (
            db.query(NarrativeCache)
            .filter(
                NarrativeCache.scope == scope,
                NarrativeCache.scope_id == scope_id
                if scope_id
                else NarrativeCache.scope_id.is_(None),
                NarrativeCache.date_range_key == dr_key,
            )
            .first()
        )
        if existing:
            _update_existing(existing)
            db.flush()


def generate_narrative(
    db: Session,
    scope: str,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    force_refresh: bool = False,
) -> NarrativeResponse:
    """Generate or retrieve a cached narrative insight report."""
    scope_id = engineer_id if scope == "engineer" else team_id
    dr_key = _date_range_key(start_date, end_date)

    # Check cache
    if not force_refresh:
        cached = (
            db.query(NarrativeCache)
            .filter(
                NarrativeCache.scope == scope,
                (
                    NarrativeCache.scope_id == scope_id
                    if scope_id
                    else NarrativeCache.scope_id.is_(None)
                ),
                NarrativeCache.date_range_key == dr_key,
                NarrativeCache.expires_at > datetime.now(UTC),
            )
            .first()
        )
        if cached:
            scope_label = _resolve_scope_label(db, scope, engineer_id, team_id)
            return NarrativeResponse(
                scope=scope,
                scope_label=scope_label,
                sections=[NarrativeSection(**s) for s in cached.sections],
                generated_at=cached.created_at,
                cached=True,
                model_used=cached.model_used,
                data_summary=cached.data_summary or {},
            )

    # Verify API key configured
    if not settings.anthropic_api_key:
        raise ValueError("PRIMER_ANTHROPIC_API_KEY not configured")

    # Gather data
    data = _gather_data(db, scope, team_id, engineer_id, start_date, end_date)

    if data["total_sessions"] < MIN_SESSIONS:
        raise ValueError(
            f"Insufficient data: only {data['total_sessions']} sessions "
            f"(minimum {MIN_SESSIONS} required)"
        )

    # Build prompt and call LLM
    scope_label = _resolve_scope_label(db, scope, engineer_id, team_id)
    system_prompt, user_prompt = _build_prompt(scope, scope_label, data)
    sections_raw, model_used, prompt_tokens, completion_tokens = _call_anthropic(
        system_prompt, user_prompt
    )

    # Validate sections
    sections = []
    for s in sections_raw:
        if isinstance(s, dict) and "title" in s and "content" in s:
            sections.append({"title": s["title"], "content": s["content"]})

    if not sections:
        raise ValueError("LLM returned no valid sections")

    # Build data summary for transparency
    data_summary = {
        "total_sessions": data["total_sessions"],
        "total_engineers": data["total_engineers"],
        "estimated_cost": data.get("total_cost"),
        "success_rate": data.get("success_rate"),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }

    # Upsert cache
    now = datetime.now(UTC)
    _upsert_cache(
        db,
        scope,
        scope_id,
        dr_key,
        sections,
        data_summary,
        model_used,
        prompt_tokens,
        completion_tokens,
        now,
    )

    return NarrativeResponse(
        scope=scope,
        scope_label=scope_label,
        sections=[NarrativeSection(**s) for s in sections],
        generated_at=now,
        cached=False,
        model_used=model_used,
        data_summary=data_summary,
    )


def refresh_all_narratives(db: Session) -> int:
    """Refresh narratives for all engineers, teams, and org scope.

    Skips scopes where cache is still valid.  Returns count of refreshed narratives.
    """
    from sqlalchemy import func

    refreshed = 0

    from primer.common.models import Session as SessionModel

    # Engineers with enough sessions
    engineer_ids = (
        db.query(SessionModel.engineer_id)
        .group_by(SessionModel.engineer_id)
        .having(func.count(SessionModel.id) >= MIN_SESSIONS)
        .all()
    )

    for (eid,) in engineer_ids:
        try:
            result = generate_narrative(db, scope="engineer", engineer_id=eid)
            db.commit()
            if not result.cached:
                refreshed += 1
        except Exception:
            db.rollback()
            logger.exception("Failed to refresh narrative for engineer %s", eid)

    # Teams with enough sessions
    team_ids = (
        db.query(SessionModel.engineer_id)
        .join(Engineer, Engineer.id == SessionModel.engineer_id)
        .filter(Engineer.team_id.isnot(None))
        .with_entities(Engineer.team_id)
        .group_by(Engineer.team_id)
        .having(func.count(SessionModel.id) >= MIN_SESSIONS)
        .all()
    )

    for (tid,) in team_ids:
        try:
            result = generate_narrative(db, scope="team", team_id=tid)
            db.commit()
            if not result.cached:
                refreshed += 1
        except Exception:
            db.rollback()
            logger.exception("Failed to refresh narrative for team %s", tid)

    # Org scope
    total = db.query(func.count(SessionModel.id)).scalar() or 0
    if total >= MIN_SESSIONS:
        try:
            result = generate_narrative(db, scope="org")
            db.commit()
            if not result.cached:
                refreshed += 1
        except Exception:
            db.rollback()
            logger.exception("Failed to refresh org narrative")

    return refreshed
