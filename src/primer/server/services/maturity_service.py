"""AI DevEx Maturity analytics service."""

from collections import Counter, defaultdict
from datetime import datetime
from statistics import median

from sqlalchemy import func
from sqlalchemy.orm import Session

from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.common.models import (
    Engineer,
    GitRepository,
    ModelUsage,
    SessionFacets,
    ToolUsage,
)
from primer.common.models import Session as SessionModel
from primer.common.pricing import estimate_cost, get_cost_tier
from primer.common.schemas import (
    AgentSkillUsage,
    DailyLeverageEntry,
    EngineerLeverageProfile,
    LeverageBreakdown,
    MaturityAnalyticsResponse,
    ProjectReadinessEntry,
    ToolCategoryBreakdown,
)
from primer.common.tool_classification import (
    CATEGORIES,
    classify_tools,
    compute_effectiveness_score,
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
    session_id_subq = sessions_q.with_entities(SessionModel.id).subquery()
    sessions_analyzed = db.query(func.count()).select_from(session_id_subq).scalar() or 0

    # Gather all tool usage rows for scoped sessions
    tool_rows = (
        db.query(ToolUsage.session_id, ToolUsage.tool_name, ToolUsage.call_count)
        .filter(ToolUsage.session_id.in_(db.query(session_id_subq.c.id)))
        .all()
    )

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

    # Map session_id -> engineer info
    eng_rows = (
        db.query(SessionModel.id, Engineer.id, Engineer.name)
        .join(Engineer, SessionModel.engineer_id == Engineer.id)
        .filter(SessionModel.id.in_(db.query(session_id_subq.c.id)))
        .all()
    )
    session_engineer: dict[str, tuple[str, str]] = {}
    for sid, eid, ename in eng_rows:
        session_engineer[sid] = (eid, ename)

    # Aggregate per-engineer tool counts
    eng_tools: dict[str, Counter[str]] = defaultdict(Counter)
    for sid, tools in per_session.items():
        if sid in session_engineer:
            eid = session_engineer[sid][0]
            for tool_name, count in tools.items():
                eng_tools[eid][tool_name] += count

    engineer_names: dict[str, str] = {}
    for _sid, (eid, ename) in session_engineer.items():
        engineer_names[eid] = ename

    # Cache hit rates per engineer
    eng_cache = (
        sessions_q.with_entities(
            SessionModel.engineer_id,
            func.sum(SessionModel.cache_read_tokens),
            func.sum(SessionModel.input_tokens),
        )
        .group_by(SessionModel.engineer_id)
        .all()
    )
    eng_cache_rates: dict[str, float] = {}
    for eid, cache_read, input_tok in eng_cache:
        total = (input_tok or 0) + (cache_read or 0)
        eng_cache_rates[eid] = (cache_read or 0) / total if total > 0 else 0.0

    # --- NEW: Model usage data per engineer ---
    model_rows = (
        db.query(
            ModelUsage.session_id,
            ModelUsage.model_name,
            ModelUsage.input_tokens,
            ModelUsage.output_tokens,
        )
        .filter(ModelUsage.session_id.in_(db.query(session_id_subq.c.id)))
        .all()
    )
    eng_model_tokens: dict[str, Counter[str]] = defaultdict(Counter)
    eng_model_tier_tokens: dict[str, Counter[str]] = defaultdict(Counter)
    for sid, model_name, input_tok, output_tok in model_rows:
        if sid in session_engineer:
            eid = session_engineer[sid][0]
            total_tok = (input_tok or 0) + (output_tok or 0)
            eng_model_tokens[eid][model_name] += total_tok
            tier = get_cost_tier(model_name)
            eng_model_tier_tokens[eid][tier] += total_tok

    # --- NEW: Effectiveness data per engineer ---
    # Success rates
    facet_rows = (
        db.query(SessionModel.engineer_id, SessionFacets.outcome)
        .join(SessionFacets, SessionModel.id == SessionFacets.session_id)
        .filter(SessionModel.id.in_(db.query(session_id_subq.c.id)))
        .filter(SessionFacets.outcome.isnot(None))
        .all()
    )
    eng_outcomes: dict[str, list[str]] = defaultdict(list)
    for eid, outcome in facet_rows:
        normalized_outcome = canonical_outcome(outcome)
        if normalized_outcome is not None:
            eng_outcomes[eid].append(normalized_outcome)

    eng_success_rates: dict[str, float] = {}
    eng_success_counts: dict[str, int] = {}
    for eid, outcomes in eng_outcomes.items():
        successes = sum(1 for outcome in outcomes if is_success_outcome(outcome))
        eng_success_counts[eid] = successes
        eng_success_rates[eid] = successes / len(outcomes) if outcomes else 0.0

    # Cost per engineer — use actual per-model pricing from ModelUsage rows
    eng_total_cost: dict[str, float] = {}
    for sid, model_name, input_tok, output_tok in model_rows:
        if sid in session_engineer:
            eid = session_engineer[sid][0]
            eng_total_cost[eid] = eng_total_cost.get(eid, 0.0) + estimate_cost(
                model_name, input_tok or 0, output_tok or 0
            )
    # Fallback: if no ModelUsage rows, estimate from session-level tokens
    if not eng_total_cost:
        fallback_rows = (
            sessions_q.with_entities(
                SessionModel.engineer_id,
                func.sum(SessionModel.input_tokens),
                func.sum(SessionModel.output_tokens),
                func.sum(SessionModel.cache_read_tokens),
                func.sum(SessionModel.cache_creation_tokens),
            )
            .group_by(SessionModel.engineer_id)
            .all()
        )
        for eid, inp, out, cr, cc in fallback_rows:
            eng_total_cost[eid] = estimate_cost(
                "claude-sonnet-4", inp or 0, out or 0, cr or 0, cc or 0
            )

    eng_cost_per_success: dict[str, float | None] = {}
    for eid in set(eng_total_cost) | set(eng_success_counts):
        cost = eng_total_cost.get(eid)
        successes = eng_success_counts.get(eid, 0)
        if cost is not None and cost > 0 and successes > 0:
            eng_cost_per_success[eid] = cost / successes
        else:
            eng_cost_per_success[eid] = None

    # Team median cost per success for effectiveness normalization
    valid_costs = [c for c in eng_cost_per_success.values() if c is not None]
    team_median_cps = median(valid_costs) if valid_costs else None

    # 2. Per-engineer leverage + effectiveness profiles
    engineer_profiles: list[EngineerLeverageProfile] = []
    engineers_using_orchestration = 0
    engineers_using_teams = 0
    all_leverage_scores: list[float] = []
    all_effectiveness_scores: list[float] = []
    all_model_diversities: list[float] = []

    all_engineer_ids = set(eid for eid, _ in session_engineer.values())
    for eid in all_engineer_ids:
        tools = eng_tools.get(eid, Counter())
        classified_eng = classify_tools(dict(tools))
        orch_calls = sum(classified_eng["orchestration"].values())
        skill_calls = sum(classified_eng["skill"].values())
        mcp_calls = sum(classified_eng["mcp"].values())
        total_calls = sum(tools.values())

        cache_rate = eng_cache_rates.get(eid, 0.0)
        model_tokens = dict(eng_model_tokens.get(eid, {}))
        model_tier_tokens = dict(eng_model_tier_tokens.get(eid, {}))

        score, breakdown = compute_leverage_score(
            dict(tools), cache_rate, model_tokens or None, model_tier_tokens or None
        )
        all_leverage_scores.append(score)
        all_model_diversities.append(breakdown.get("model_diversity", 0.0))

        if orch_calls > 0 or skill_calls > 0:
            engineers_using_orchestration += 1

        has_teams = breakdown.get("agent_team_score", 0) > 0
        if has_teams:
            engineers_using_teams += 1

        # Effectiveness
        eff_score, _eff_breakdown = compute_effectiveness_score(
            success_rate=eng_success_rates.get(eid),
            cost_per_success=eng_cost_per_success.get(eid),
            team_median_cost_per_success=team_median_cps,
            avg_health_score=None,  # health computed dynamically, not stored
        )
        if eng_success_rates.get(eid) is not None:
            all_effectiveness_scores.append(eff_score)

        # Top agents/skills/models
        orch = classified_eng["orchestration"]
        top_agents = sorted(orch, key=orch.get, reverse=True)[:5]  # type: ignore[arg-type]
        skill = classified_eng["skill"]
        top_skills = sorted(skill, key=skill.get, reverse=True)[:5]  # type: ignore[arg-type]
        if model_tokens:
            top_models = sorted(  # type: ignore[arg-type]
                model_tokens, key=model_tokens.get, reverse=True
            )[:5]
        else:
            top_models = []

        cat_dist = {cat: sum(classified_eng[cat].values()) for cat in CATEGORIES}

        engineer_profiles.append(
            EngineerLeverageProfile(
                engineer_id=eid,
                name=engineer_names.get(eid, "Unknown"),
                leverage_score=score,
                effectiveness_score=eff_score if eng_success_rates.get(eid) is not None else None,
                leverage_breakdown=LeverageBreakdown(**breakdown) if breakdown else None,
                total_tool_calls=total_calls,
                orchestration_calls=orch_calls,
                skill_calls=skill_calls,
                mcp_calls=mcp_calls,
                model_count=len(model_tokens),
                cost_tier_count=sum(1 for v in model_tier_tokens.values() if v > 0),
                uses_agent_teams=has_teams,
                top_agents=top_agents,
                top_skills=top_skills,
                top_models=top_models,
                category_distribution=cat_dist,
            )
        )

    engineer_profiles.sort(key=lambda p: p.leverage_score, reverse=True)

    # 3. Daily leverage trend
    daily_leverage: list[DailyLeverageEntry] = []
    if sessions_analyzed > 0:
        session_dates = sessions_q.with_entities(
            SessionModel.id,
            SessionModel.started_at,
            SessionModel.cache_read_tokens,
            SessionModel.input_tokens,
        ).all()
        date_tools: dict[str, Counter[str]] = defaultdict(Counter)
        date_cache: dict[str, list[tuple[int, int]]] = defaultdict(list)
        all_days: set[str] = set()
        for sid, started_at, cache_read, input_tok in session_dates:
            if started_at:
                day = started_at.strftime("%Y-%m-%d")
                all_days.add(day)
                date_cache[day].append((cache_read or 0, input_tok or 0))
                if sid in per_session:
                    for tool_name, count in per_session[sid].items():
                        date_tools[day][tool_name] += count

        for day in sorted(all_days):
            tools = dict(date_tools[day])
            total_cache = sum(c for c, _ in date_cache[day])
            total_input = sum(i for _, i in date_cache[day])
            total_tokens = total_cache + total_input
            daily_cache_rate = total_cache / total_tokens if total_tokens > 0 else 0.0
            score, _ = compute_leverage_score(tools, daily_cache_rate)
            daily_leverage.append(
                DailyLeverageEntry(date=day, leverage_score=score, total_calls=sum(tools.values()))
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

    # 5. Project readiness
    project_readiness: list[ProjectReadinessEntry] = []
    if sessions_analyzed > 0:
        repo_session_counts = (
            db.query(SessionModel.repository_id, func.count(SessionModel.id))
            .filter(
                SessionModel.id.in_(db.query(session_id_subq.c.id)),
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
    total_engineers = len(all_engineer_ids)
    avg_leverage = (
        sum(all_leverage_scores) / len(all_leverage_scores) if all_leverage_scores else 0.0
    )
    avg_effectiveness = (
        sum(all_effectiveness_scores) / len(all_effectiveness_scores)
        if all_effectiveness_scores
        else None
    )
    adoption_rate = engineers_using_orchestration / total_engineers if total_engineers > 0 else 0.0
    team_adoption_rate = engineers_using_teams / total_engineers if total_engineers > 0 else 0.0
    model_div_avg = (
        sum(all_model_diversities) / len(all_model_diversities) if all_model_diversities else 0.0
    )

    return MaturityAnalyticsResponse(
        tool_categories=tool_categories,
        engineer_profiles=engineer_profiles,
        daily_leverage=daily_leverage,
        agent_skill_breakdown=agent_skill_breakdown,
        project_readiness=project_readiness,
        sessions_analyzed=sessions_analyzed,
        avg_leverage_score=round(avg_leverage, 1),
        avg_effectiveness_score=(
            round(avg_effectiveness, 1) if avg_effectiveness is not None else None
        ),
        orchestration_adoption_rate=round(adoption_rate, 3),
        team_orchestration_adoption_rate=round(team_adoption_rate, 3),
        model_diversity_avg=round(model_div_avg, 3),
    )
