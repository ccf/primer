"""AI DevEx Maturity analytics service."""

from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from primer.common.models import (
    Engineer,
    GitRepository,
    ToolUsage,
)
from primer.common.models import Session as SessionModel
from primer.common.schemas import (
    AgentSkillUsage,
    DailyLeverageEntry,
    EngineerLeverageProfile,
    MaturityAnalyticsResponse,
    ProjectReadinessEntry,
    ToolCategoryBreakdown,
)
from primer.common.tool_classification import (
    CATEGORIES,
    classify_tools,
    compute_leverage_score,
)
from primer.server.services.analytics_service import base_session_query


def get_maturity_analytics(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> MaturityAnalyticsResponse:
    """Compute full maturity analytics response."""
    sessions_q = base_session_query(db, team_id, engineer_id, start_date, end_date)
    session_ids = [s.id for s in sessions_q.with_entities(SessionModel.id).all()]
    sessions_analyzed = len(session_ids)

    # Gather all tool usage rows for scoped sessions
    if session_ids:
        tool_rows = (
            db.query(
                ToolUsage.session_id,
                ToolUsage.tool_name,
                ToolUsage.call_count,
            )
            .filter(ToolUsage.session_id.in_(session_ids))
            .all()
        )
    else:
        tool_rows = []

    # Build per-session and aggregate tool counts
    aggregate_tools: Counter[str] = Counter()
    per_session: dict[str, dict[str, int]] = defaultdict(dict)
    for sid, tool_name, call_count in tool_rows:
        aggregate_tools[tool_name] += call_count
        per_session[sid][tool_name] = per_session[sid].get(tool_name, 0) + call_count

    # 1. Tool category breakdown
    classified = classify_tools(dict(aggregate_tools))
    tool_categories = ToolCategoryBreakdown(
        core=classified["core"],
        search=classified["search"],
        orchestration=classified["orchestration"],
        skill=classified["skill"],
        mcp=classified["mcp"],
    )

    # 2. Per-engineer leverage profiles
    # Map session_id -> engineer info (query directly to avoid duplicate Engineer join)
    if session_ids:
        eng_rows = (
            db.query(SessionModel.id, Engineer.id, Engineer.name)
            .join(Engineer, SessionModel.engineer_id == Engineer.id)
            .filter(SessionModel.id.in_(session_ids))
            .all()
        )
    else:
        eng_rows = []
    session_engineer: dict[str, tuple[str, str]] = {}
    for sid, eid, ename in eng_rows:
        session_engineer[sid] = (eid, ename)

    # Aggregate per-engineer
    eng_tools: dict[str, Counter[str]] = defaultdict(Counter)
    for sid, tools in per_session.items():
        if sid in session_engineer:
            eid = session_engineer[sid][0]
            for tool_name, count in tools.items():
                eng_tools[eid][tool_name] += count

    engineer_names: dict[str, str] = {}
    for _sid, (eid, ename) in session_engineer.items():
        engineer_names[eid] = ename

    # Get cache hit rates per engineer for leverage scoring
    if session_ids:
        eng_cache = (
            sessions_q.with_entities(
                SessionModel.engineer_id,
                func.sum(SessionModel.cache_read_tokens),
                func.sum(SessionModel.input_tokens),
            )
            .group_by(SessionModel.engineer_id)
            .all()
        )
    else:
        eng_cache = []
    eng_cache_rates: dict[str, float] = {}
    for eid, cache_read, input_tok in eng_cache:
        total = (input_tok or 0) + (cache_read or 0)
        eng_cache_rates[eid] = (cache_read or 0) / total if total > 0 else 0.0

    engineer_profiles: list[EngineerLeverageProfile] = []
    engineers_using_orchestration = 0
    all_scores: list[float] = []

    for eid, tools in eng_tools.items():
        classified_eng = classify_tools(dict(tools))
        orch_calls = sum(classified_eng["orchestration"].values())
        skill_calls = sum(classified_eng["skill"].values())
        mcp_calls = sum(classified_eng["mcp"].values())
        total_calls = sum(tools.values())

        cache_rate = eng_cache_rates.get(eid, 0.0)
        score = compute_leverage_score(dict(tools), cache_rate)
        all_scores.append(score)

        if orch_calls > 0 or skill_calls > 0:
            engineers_using_orchestration += 1

        # Top agents = orchestration tools sorted by count
        orch = classified_eng["orchestration"]
        top_agents = sorted(orch, key=orch.get, reverse=True)[:5]  # type: ignore[arg-type]
        skill = classified_eng["skill"]
        top_skills = sorted(skill, key=skill.get, reverse=True)[:5]  # type: ignore[arg-type]

        cat_dist = {cat: sum(classified_eng[cat].values()) for cat in CATEGORIES}

        engineer_profiles.append(
            EngineerLeverageProfile(
                engineer_id=eid,
                name=engineer_names.get(eid, "Unknown"),
                leverage_score=score,
                total_tool_calls=total_calls,
                orchestration_calls=orch_calls,
                skill_calls=skill_calls,
                mcp_calls=mcp_calls,
                top_agents=top_agents,
                top_skills=top_skills,
                category_distribution=cat_dist,
            )
        )

    engineer_profiles.sort(key=lambda p: p.leverage_score, reverse=True)

    # 3. Daily leverage trend
    daily_leverage: list[DailyLeverageEntry] = []
    if session_ids:
        # Get session dates
        session_dates = sessions_q.with_entities(SessionModel.id, SessionModel.started_at).all()
        date_tools: dict[str, Counter[str]] = defaultdict(Counter)
        for sid, started_at in session_dates:
            if started_at and sid in per_session:
                day = started_at.strftime("%Y-%m-%d")
                for tool_name, count in per_session[sid].items():
                    date_tools[day][tool_name] += count

        for day in sorted(date_tools):
            tools = dict(date_tools[day])
            score = compute_leverage_score(tools)
            daily_leverage.append(
                DailyLeverageEntry(
                    date=day,
                    leverage_score=score,
                    total_calls=sum(tools.values()),
                )
            )

    # 4. Agent/skill breakdown
    agent_skill_data: dict[str, dict] = {}
    for sid, tools in per_session.items():
        eid = session_engineer.get(sid, (None,))[0]
        for tool_name, count in tools.items():
            classified_cat = classify_tools({tool_name: count})
            cat = next(c for c in CATEGORIES if classified_cat[c])
            if cat not in ("orchestration", "skill"):
                continue
            if tool_name not in agent_skill_data:
                agent_skill_data[tool_name] = {
                    "name": tool_name,
                    "category": cat,
                    "total_calls": 0,
                    "sessions": set(),
                    "engineers": set(),
                }
            agent_skill_data[tool_name]["total_calls"] += count
            agent_skill_data[tool_name]["sessions"].add(sid)
            if eid:
                agent_skill_data[tool_name]["engineers"].add(eid)

    agent_skill_breakdown = [
        AgentSkillUsage(
            name=d["name"],
            category=d["category"],
            total_calls=d["total_calls"],
            session_count=len(d["sessions"]),
            engineer_count=len(d["engineers"]),
        )
        for d in sorted(agent_skill_data.values(), key=lambda x: x["total_calls"], reverse=True)
    ]

    # 5. Project readiness (scoped to repos with sessions in current filter)
    project_readiness: list[ProjectReadinessEntry] = []
    if session_ids:
        repo_session_counts = (
            db.query(SessionModel.repository_id, func.count(SessionModel.id))
            .filter(
                SessionModel.id.in_(session_ids),
                SessionModel.repository_id.isnot(None),
            )
            .group_by(SessionModel.repository_id)
            .all()
        )
        repo_counts = dict(repo_session_counts)
        if repo_counts:
            repos = (
                db.query(GitRepository)
                .filter(
                    GitRepository.id.in_(list(repo_counts.keys())),
                    GitRepository.ai_readiness_score.isnot(None),
                )
                .all()
            )
            for repo in repos:
                project_readiness.append(
                    ProjectReadinessEntry(
                        repository=repo.full_name,
                        has_claude_md=repo.has_claude_md or False,
                        has_agents_md=repo.has_agents_md or False,
                        has_claude_dir=repo.has_claude_dir or False,
                        ai_readiness_score=repo.ai_readiness_score or 0.0,
                        session_count=repo_counts.get(repo.id, 0),
                    )
                )
    project_readiness.sort(key=lambda p: p.ai_readiness_score, reverse=True)

    # Aggregate metrics
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
    # Use distinct engineers from scoped sessions (not just those with tool usage rows)
    total_engineers = len(set(eid for eid, _ in session_engineer.values()))
    adoption_rate = engineers_using_orchestration / total_engineers if total_engineers > 0 else 0.0

    return MaturityAnalyticsResponse(
        tool_categories=tool_categories,
        engineer_profiles=engineer_profiles,
        daily_leverage=daily_leverage,
        agent_skill_breakdown=agent_skill_breakdown,
        project_readiness=project_readiness,
        sessions_analyzed=sessions_analyzed,
        avg_leverage_score=round(avg_score, 1),
        orchestration_adoption_rate=round(adoption_rate, 3),
    )
