"""AI DevEx Maturity analytics service."""

from collections import Counter, defaultdict
from datetime import datetime
from hashlib import md5
from statistics import median

from sqlalchemy import func
from sqlalchemy.orm import Session

from primer.common.customizations import is_explicit_customization_provenance
from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.common.models import (
    Engineer,
    GitRepository,
    ModelUsage,
    PullRequest,
    SessionCommit,
    SessionCustomization,
    SessionFacets,
    SessionMessage,
    SessionRecoveryPath,
    SessionWorkflowProfile,
    Team,
    ToolUsage,
)
from primer.common.models import Session as SessionModel
from primer.common.pricing import estimate_cost, get_cost_tier
from primer.common.schemas import (
    AgentSkillUsage,
    AgentTeamModeSummary,
    CustomizationOutcomeAttribution,
    CustomizationStateFunnel,
    CustomizationUsage,
    DailyLeverageEntry,
    DelegationPatternSummary,
    EngineerLeverageProfile,
    HighPerformerStack,
    LeverageBreakdown,
    MaturityAnalyticsResponse,
    ProjectReadinessEntry,
    StackCustomization,
    TeamCustomizationLandscape,
    ToolCategoryBreakdown,
    ToolchainReliabilityEntry,
)
from primer.common.tool_classification import (
    CATEGORIES,
    classify_tool,
    classify_tools,
    compute_leverage_score,
)
from primer.server.services.agent_team_service import detect_session_agent_team
from primer.server.services.analytics_service import base_session_query
from primer.server.services.delegation_graph_service import extract_session_delegation_edges
from primer.server.services.effectiveness_service import build_effectiveness_score

_RELIABILITY_FAILURE_FRICTION_TYPES = frozenset({"tool_error", "exec_error", "timeout"})


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
        db.query(SessionModel.id, Engineer.id, Engineer.name, Engineer.team_id)
        .join(Engineer, SessionModel.engineer_id == Engineer.id)
        .filter(SessionModel.id.in_(db.query(session_id_subq.c.id)))
        .all()
    )
    session_engineer: dict[str, tuple[str, str]] = {}
    engineer_team_ids: dict[str, str | None] = {}
    for sid, eid, ename, engineer_team_id in eng_rows:
        session_engineer[sid] = (eid, ename)
        engineer_team_ids[eid] = engineer_team_id

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
    team_ids = {tid for tid in engineer_team_ids.values() if tid}
    team_names = {team.id: team.name for team in db.query(Team).filter(Team.id.in_(team_ids)).all()}

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
    session_costs: dict[str, float] = defaultdict(float)
    for sid, model_name, input_tok, output_tok in model_rows:
        session_costs[sid] += estimate_cost(model_name, input_tok or 0, output_tok or 0)
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

    session_state_rows = (
        db.query(
            SessionModel.id,
            SessionModel.engineer_id,
            SessionFacets.outcome,
            SessionFacets.friction_counts,
            SessionRecoveryPath.recovery_result,
            SessionRecoveryPath.recovery_step_count,
        )
        .outerjoin(SessionFacets, SessionModel.id == SessionFacets.session_id)
        .outerjoin(SessionRecoveryPath, SessionModel.id == SessionRecoveryPath.session_id)
        .filter(SessionModel.id.in_(db.query(session_id_subq.c.id)))
        .all()
    )
    session_metrics: dict[str, dict[str, object]] = {}
    for (
        session_id,
        engineer_id_for_session,
        outcome,
        friction_counts,
        recovery_result,
        recovery_step_count,
    ) in session_state_rows:
        positive_friction_counts = {
            friction_type: count
            for friction_type, count in (friction_counts or {}).items()
            if count and count > 0
        }
        session_metrics[session_id] = {
            "engineer_id": engineer_id_for_session,
            "outcome": canonical_outcome(outcome),
            "friction_counts": positive_friction_counts,
            "has_friction": bool(positive_friction_counts),
            "has_failure": any(
                friction_type in _RELIABILITY_FAILURE_FRICTION_TYPES
                for friction_type in positive_friction_counts
            ),
            "recovery_result": recovery_result,
            "recovery_step_count": recovery_step_count or 0,
        }

    session_workflow_archetypes = {
        row.session_id: row.archetype
        for row in (
            db.query(
                SessionWorkflowProfile.session_id,
                SessionWorkflowProfile.archetype,
            )
            .filter(
                SessionWorkflowProfile.session_id.in_(db.query(session_id_subq.c.id)),
                SessionWorkflowProfile.archetype.isnot(None),
            )
            .all()
        )
    }

    delegation_message_rows = (
        db.query(
            SessionMessage.session_id,
            SessionMessage.ordinal,
            SessionMessage.tool_calls,
        )
        .filter(
            SessionMessage.session_id.in_(db.query(session_id_subq.c.id)),
            SessionMessage.tool_calls.isnot(None),
        )
        .order_by(SessionMessage.session_id.asc(), SessionMessage.ordinal.asc())
        .all()
    )
    messages_by_session: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in delegation_message_rows:
        messages_by_session[row.session_id].append(
            {
                "ordinal": row.ordinal,
                "tool_calls": row.tool_calls,
            }
        )

    eng_session_counts = {
        eid: count
        for eid, count in sessions_q.with_entities(
            SessionModel.engineer_id, func.count(SessionModel.id)
        )
        .group_by(SessionModel.engineer_id)
        .all()
    }

    eng_sessions_with_commits = {
        eid: count
        for eid, count in db.query(
            SessionModel.engineer_id,
            func.count(func.distinct(SessionCommit.session_id)),
        )
        .join(SessionCommit, SessionCommit.session_id == SessionModel.id)
        .filter(SessionModel.id.in_(db.query(session_id_subq.c.id)))
        .group_by(SessionModel.engineer_id)
        .all()
    }

    eng_pr_state_rows = (
        db.query(SessionModel.engineer_id, SessionCommit.pull_request_id, PullRequest.state)
        .join(SessionCommit, SessionCommit.session_id == SessionModel.id)
        .join(PullRequest, PullRequest.id == SessionCommit.pull_request_id)
        .filter(
            SessionModel.id.in_(db.query(session_id_subq.c.id)),
            SessionCommit.pull_request_id.isnot(None),
        )
        .all()
    )
    eng_pr_states: dict[str, dict[str, str]] = defaultdict(dict)
    for eid, pr_id, state in eng_pr_state_rows:
        eng_pr_states[eid][pr_id] = state

    eng_merge_rates: dict[str, float | None] = {}
    for eid, pr_states in eng_pr_states.items():
        merged = sum(1 for state in pr_states.values() if state == "merged")
        closed = sum(1 for state in pr_states.values() if state == "closed")
        denominator = merged + closed
        eng_merge_rates[eid] = merged / denominator if denominator > 0 else None

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
        peer_costs = [
            cost
            for other_eid, cost in eng_cost_per_success.items()
            if other_eid != eid and cost is not None
        ]
        peer_median_cps = median(peer_costs) if peer_costs else None
        effectiveness = build_effectiveness_score(
            success_rate=eng_success_rates.get(eid),
            cost_per_successful_outcome=eng_cost_per_success.get(eid),
            benchmark_cost_per_successful_outcome=peer_median_cps,
            pr_merge_rate=eng_merge_rates.get(eid),
            findings_fix_rate=None,
            total_sessions=eng_session_counts.get(eid, 0),
            sessions_with_commits=eng_sessions_with_commits.get(eid, 0),
        )
        if effectiveness.score is not None:
            all_effectiveness_scores.append(effectiveness.score)

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
                effectiveness_score=effectiveness.score,
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

    delegation_pattern_data: dict[tuple[str, str], dict] = {}
    for sid in session_engineer:
        tool_usage_fallback = [
            {"tool_name": tool_name, "call_count": count}
            for tool_name, count in per_session.get(sid, {}).items()
        ]
        edges = extract_session_delegation_edges(
            messages_by_session.get(sid, []),
            tool_usage_fallback,
        )
        if not edges:
            continue
        session_metric = session_metrics.get(sid)
        engineer_id_for_session = session_engineer.get(sid, (None, ""))[0]
        workflow_archetype = session_workflow_archetypes.get(sid)
        for edge in edges:
            bucket = delegation_pattern_data.setdefault(
                (edge.edge_type, edge.target_node),
                {
                    "target_node": edge.target_node,
                    "edge_type": edge.edge_type,
                    "sessions": set(),
                    "engineers": set(),
                    "total_calls": 0,
                    "success_sessions": set(),
                    "workflow_archetypes": Counter(),
                },
            )
            bucket["sessions"].add(sid)
            if engineer_id_for_session:
                bucket["engineers"].add(engineer_id_for_session)
            bucket["total_calls"] += edge.call_count
            if session_metric:
                outcome = session_metric["outcome"]
                if outcome and is_success_outcome(outcome):
                    bucket["success_sessions"].add(sid)
            if workflow_archetype:
                bucket["workflow_archetypes"][workflow_archetype] += edge.call_count

    delegation_patterns = [
        DelegationPatternSummary(
            target_node=bucket["target_node"],
            edge_type=bucket["edge_type"],
            session_count=len(bucket["sessions"]),
            engineer_count=len(bucket["engineers"]),
            total_calls=bucket["total_calls"],
            success_rate=(
                round(len(bucket["success_sessions"]) / len(bucket["sessions"]), 3)
                if bucket["sessions"]
                else None
            ),
            top_workflow_archetypes=[
                archetype for archetype, _count in bucket["workflow_archetypes"].most_common(3)
            ],
        )
        for bucket in sorted(
            delegation_pattern_data.values(),
            key=lambda item: (
                -len(item["sessions"]),
                -item["total_calls"],
                item["target_node"],
            ),
        )
    ]

    agent_team_mode_data: dict[str, dict] = {}
    for sid in session_engineer:
        tool_usage_fallback = [
            {"tool_name": tool_name, "call_count": count}
            for tool_name, count in per_session.get(sid, {}).items()
        ]
        detection = detect_session_agent_team(messages_by_session.get(sid, []), tool_usage_fallback)
        bucket = agent_team_mode_data.setdefault(
            detection.coordination_mode,
            {
                "coordination_mode": detection.coordination_mode,
                "sessions": set(),
                "engineers": set(),
                "success_sessions": set(),
                "session_costs": [],
                "delegation_counts": [],
                "targets": Counter(),
                "workflow_archetypes": Counter(),
            },
        )
        bucket["sessions"].add(sid)
        engineer_id_for_session = session_engineer.get(sid, (None, ""))[0]
        if engineer_id_for_session:
            bucket["engineers"].add(engineer_id_for_session)
        session_metric = session_metrics.get(sid)
        if session_metric:
            outcome = session_metric["outcome"]
            if outcome and is_success_outcome(outcome):
                bucket["success_sessions"].add(sid)
        if sid in session_costs:
            bucket["session_costs"].append(session_costs[sid])
        bucket["delegation_counts"].append(detection.delegation_edge_count)
        bucket["targets"].update(detection.target_nodes)
        workflow_archetype = session_workflow_archetypes.get(sid)
        if workflow_archetype:
            bucket["workflow_archetypes"][workflow_archetype] += 1

    agent_team_modes = [
        AgentTeamModeSummary(
            coordination_mode=bucket["coordination_mode"],
            session_count=len(bucket["sessions"]),
            engineer_count=len(bucket["engineers"]),
            session_share=round(len(bucket["sessions"]) / sessions_analyzed, 3)
            if sessions_analyzed > 0
            else 0.0,
            success_rate=(
                round(len(bucket["success_sessions"]) / len(bucket["sessions"]), 3)
                if bucket["sessions"]
                else None
            ),
            avg_cost_per_session=(
                round(sum(bucket["session_costs"]) / len(bucket["session_costs"]), 4)
                if bucket["session_costs"]
                else None
            ),
            avg_delegation_edges=round(
                sum(bucket["delegation_counts"]) / len(bucket["delegation_counts"]),
                2,
            )
            if bucket["delegation_counts"]
            else 0.0,
            top_targets=[target for target, _count in bucket["targets"].most_common(3)],
            top_workflow_archetypes=[
                archetype for archetype, _count in bucket["workflow_archetypes"].most_common(3)
            ],
        )
        for bucket in sorted(
            agent_team_mode_data.values(),
            key=lambda item: (
                {"agent_team": 0, "delegated": 1, "solo": 2}.get(item["coordination_mode"], 3),
                -len(item["sessions"]),
            ),
        )
    ]

    # 4b. Toolchain reliability
    reliability_data: dict[tuple[str, str, str | None, str | None], dict] = {}

    def _ensure_reliability_bucket(
        surface_type: str,
        identifier: str,
        provenance: str | None,
        source_classification: str | None,
    ) -> dict:
        return reliability_data.setdefault(
            (surface_type, identifier, provenance, source_classification),
            {
                "identifier": identifier,
                "surface_type": surface_type,
                "provenance": provenance,
                "source_classification": source_classification,
                "sessions": set(),
                "engineers": set(),
                "friction_sessions": set(),
                "failure_sessions": set(),
                "recovered_sessions": set(),
                "abandoned_sessions": set(),
                "recovery_steps": [],
                "success_sessions": set(),
                "friction_type_counts": Counter(),
            },
        )

    def _apply_session_reliability_metrics(
        bucket: dict,
        session_id: str,
        session_metric: dict[str, object] | None,
    ) -> None:
        if session_metric is None:
            return
        if session_metric["has_friction"]:
            bucket["friction_sessions"].add(session_id)
            bucket["friction_type_counts"].update(session_metric["friction_counts"])
        if session_metric["has_failure"]:
            bucket["failure_sessions"].add(session_id)
        outcome = session_metric["outcome"]
        if outcome and is_success_outcome(outcome):
            bucket["success_sessions"].add(session_id)
        if session_metric["recovery_result"] == "recovered":
            bucket["recovered_sessions"].add(session_id)
        if session_metric["recovery_result"] == "abandoned":
            bucket["abandoned_sessions"].add(session_id)
        recovery_steps = session_metric["recovery_step_count"]
        if isinstance(recovery_steps, int) and recovery_steps > 0:
            bucket["recovery_steps"].append(recovery_steps)

    for sid, tools in per_session.items():
        for tool_name, call_count in tools.items():
            if call_count <= 0 or tool_name.startswith("Skill:") or tool_name.startswith("Task:"):
                continue
            if classify_tool(tool_name) == "mcp":
                continue
            bucket = _ensure_reliability_bucket("built_in_tool", tool_name, "built_in", "built_in")
            bucket["sessions"].add(sid)
            if sid in session_metrics:
                session_metric = session_metrics[sid]
                engineer_id_for_session = session_metric["engineer_id"]
                if engineer_id_for_session:
                    bucket["engineers"].add(engineer_id_for_session)
                _apply_session_reliability_metrics(bucket, sid, session_metric)

    # 5. Explicit customization breakdown
    customization_data: dict[tuple[str, str, str, str], dict] = {}
    customization_state_data: dict[tuple[str, str, str, str], dict] = {}
    engineer_explicit_customizations: dict[str, Counter[tuple[str, str, str, str]]] = defaultdict(
        Counter
    )
    engineer_customization_sessions: dict[str, dict[tuple[str, str, str, str], set[str]]] = (
        defaultdict(lambda: defaultdict(set))
    )
    engineer_customization_projects: dict[str, dict[tuple[str, str, str, str], Counter[str]]] = (
        defaultdict(lambda: defaultdict(Counter))
    )
    team_customizations: dict[str, Counter[tuple[str, str, str, str]]] = defaultdict(Counter)
    team_customization_engineers: dict[str, set[str]] = defaultdict(set)
    engineers_using_explicit_customizations: set[str] = set()
    customization_rows = (
        db.query(
            SessionCustomization.session_id,
            SessionCustomization.customization_type,
            SessionCustomization.identifier,
            SessionCustomization.provenance,
            SessionCustomization.source_classification,
            SessionCustomization.state,
            SessionCustomization.invocation_count,
            SessionModel.engineer_id,
            SessionModel.project_name,
        )
        .join(SessionModel, SessionCustomization.session_id == SessionModel.id)
        .filter(SessionCustomization.session_id.in_(db.query(session_id_subq.c.id)))
        .all()
    )
    for (
        session_id,
        customization_type,
        identifier,
        provenance,
        source_classification,
        state,
        invocation_count,
        engineer_id,
        project_name,
    ) in customization_rows:
        if provenance != "unknown" or source_classification != "unknown":
            state_bucket = customization_state_data.setdefault(
                (customization_type, identifier, provenance, source_classification),
                {
                    "identifier": identifier,
                    "customization_type": customization_type,
                    "provenance": provenance,
                    "source_classification": source_classification,
                    "available_sessions": set(),
                    "enabled_sessions": set(),
                    "invoked_sessions": set(),
                    "available_engineers": set(),
                    "enabled_engineers": set(),
                    "invoked_engineers": set(),
                },
            )
            state_bucket[f"{state}_sessions"].add(session_id)
            state_bucket[f"{state}_engineers"].add(engineer_id)

        if state != "invoked" or not is_explicit_customization_provenance(provenance):
            continue

        engineers_using_explicit_customizations.add(engineer_id)
        key = (customization_type, identifier, provenance, source_classification)
        team_key = engineer_team_ids.get(engineer_id) or "unassigned"
        engineer_explicit_customizations[engineer_id][key] += invocation_count or 0
        engineer_customization_sessions[engineer_id][key].add(session_id)
        if project_name:
            engineer_customization_projects[engineer_id][key][project_name] += 1
        team_customizations[team_key][key] += invocation_count or 0
        team_customization_engineers[team_key].add(engineer_id)
        bucket = customization_data.setdefault(
            key,
            {
                "identifier": identifier,
                "customization_type": customization_type,
                "provenance": provenance,
                "source_classification": source_classification,
                "total_invocations": 0,
                "sessions": set(),
                "engineers": set(),
                "projects": Counter(),
                "engineer_names": Counter(),
            },
        )
        bucket["total_invocations"] += invocation_count or 0
        bucket["sessions"].add(session_id)
        bucket["engineers"].add(engineer_id)
        if project_name:
            bucket["projects"][project_name] += 1
        bucket["engineer_names"][engineer_names.get(engineer_id, "Unknown")] += 1

        reliability_bucket = _ensure_reliability_bucket(
            customization_type,
            identifier,
            provenance,
            source_classification,
        )
        reliability_bucket["sessions"].add(session_id)
        reliability_bucket["engineers"].add(engineer_id)
        _apply_session_reliability_metrics(
            reliability_bucket,
            session_id,
            session_metrics.get(session_id),
        )

    customization_breakdown = [
        CustomizationUsage(
            identifier=bucket["identifier"],
            customization_type=bucket["customization_type"],
            provenance=bucket["provenance"],
            source_classification=bucket["source_classification"],
            total_invocations=bucket["total_invocations"],
            session_count=len(bucket["sessions"]),
            engineer_count=len(bucket["engineers"]),
            project_count=len(bucket["projects"]),
            top_projects=[project for project, _count in bucket["projects"].most_common(3)],
            top_engineers=[name for name, _count in bucket["engineer_names"].most_common(3)],
        )
        for bucket in sorted(
            customization_data.values(),
            key=lambda item: (
                -item["engineer_names"].total(),
                -item["total_invocations"],
                item["identifier"],
            ),
        )
    ]

    customization_state_funnel = [
        CustomizationStateFunnel(
            identifier=bucket["identifier"],
            customization_type=bucket["customization_type"],
            provenance=bucket["provenance"],
            source_classification=bucket["source_classification"],
            available_session_count=len(bucket["available_sessions"]),
            enabled_session_count=len(bucket["enabled_sessions"]),
            invoked_session_count=len(bucket["invoked_sessions"]),
            available_engineer_count=len(bucket["available_engineers"]),
            enabled_engineer_count=len(bucket["enabled_engineers"]),
            invoked_engineer_count=len(bucket["invoked_engineers"]),
            activation_rate=(
                round(
                    len(bucket["enabled_engineers"]) / len(bucket["available_engineers"]),
                    3,
                )
                if bucket["available_engineers"]
                else None
            ),
            usage_rate=(
                round(
                    len(bucket["invoked_engineers"]) / len(bucket["available_engineers"]),
                    3,
                )
                if bucket["available_engineers"]
                else None
            ),
            available_not_enabled_engineer_count=len(
                bucket["available_engineers"] - bucket["enabled_engineers"]
            ),
            enabled_not_invoked_engineer_count=len(
                bucket["enabled_engineers"] - bucket["invoked_engineers"]
            ),
        )
        for bucket in sorted(
            customization_state_data.values(),
            key=lambda item: (
                -len(item["invoked_engineers"]),
                -len(item["enabled_engineers"]),
                -len(item["available_engineers"]),
                item["identifier"],
            ),
        )
    ]

    toolchain_reliability = [
        ToolchainReliabilityEntry(
            identifier=bucket["identifier"],
            surface_type=bucket["surface_type"],
            provenance=bucket["provenance"],
            source_classification=bucket["source_classification"],
            session_count=len(bucket["sessions"]),
            engineer_count=len(bucket["engineers"]),
            friction_session_count=len(bucket["friction_sessions"]),
            friction_session_rate=(
                round(len(bucket["friction_sessions"]) / len(bucket["sessions"]), 3)
                if bucket["sessions"]
                else None
            ),
            failure_session_count=len(bucket["failure_sessions"]),
            failure_session_rate=(
                round(len(bucket["failure_sessions"]) / len(bucket["sessions"]), 3)
                if bucket["sessions"]
                else None
            ),
            recovery_rate=(
                round(
                    len(bucket["recovered_sessions"]) / len(bucket["friction_sessions"]),
                    3,
                )
                if bucket["friction_sessions"]
                else None
            ),
            success_rate=(
                round(len(bucket["success_sessions"]) / len(bucket["sessions"]), 3)
                if bucket["sessions"]
                else None
            ),
            abandonment_rate=(
                round(len(bucket["abandoned_sessions"]) / len(bucket["sessions"]), 3)
                if bucket["sessions"]
                else None
            ),
            avg_recovery_steps=(
                round(sum(bucket["recovery_steps"]) / len(bucket["recovery_steps"]), 1)
                if bucket["recovery_steps"]
                else None
            ),
            top_friction_types=[
                friction_type
                for friction_type, _count in bucket["friction_type_counts"].most_common(3)
            ],
        )
        for bucket in sorted(
            reliability_data.values(),
            key=lambda item: (
                -len(item["failure_sessions"]),
                -len(item["friction_sessions"]),
                -len(item["sessions"]),
                item["identifier"],
            ),
        )
    ]

    total_engineers = len(all_engineer_ids)
    profile_by_engineer_id = {profile.engineer_id: profile for profile in engineer_profiles}

    def _avg(values: list[float | None]) -> float | None:
        present = [value for value in values if value is not None]
        return sum(present) / len(present) if present else None

    def _team_customization_label(
        customization_key: tuple[str, str, str, str],
        identifier_counts: Counter[str],
    ) -> str:
        customization_type, identifier, provenance, source_classification = customization_key
        if identifier_counts[identifier] <= 1:
            return identifier
        return f"{identifier} ({customization_type}, {provenance}, {source_classification})"

    customization_presence_by_team: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for team_key, counts in team_customizations.items():
        for customization_key in counts:
            customization_presence_by_team[customization_key].add(team_key)

    team_engineers: dict[str, set[str]] = defaultdict(set)
    for engineer_id, team_id in engineer_team_ids.items():
        team_engineers[team_id or "unassigned"].add(engineer_id)

    team_customization_landscape: list[TeamCustomizationLandscape] = []
    for team_key, counts in sorted(
        team_customizations.items(),
        key=lambda item: (
            -len(item[1]),
            -len(team_customization_engineers[item[0]]),
            item[0],
        ),
    ):
        identifier_counts = Counter(
            identifier for _ctype, identifier, _prov, _source_classification in counts
        )
        avg_team_effectiveness = _avg(
            [
                profile_by_engineer_id[engineer_id].effectiveness_score
                for engineer_id in team_engineers.get(team_key, set())
                if engineer_id in profile_by_engineer_id
            ]
        )
        team_customization_landscape.append(
            TeamCustomizationLandscape(
                team_id=team_key,
                team_name=team_names.get(team_key, "Unassigned"),
                engineer_count=len(team_engineers.get(team_key, set())),
                engineers_using_explicit_customizations=len(team_customization_engineers[team_key]),
                explicit_customization_count=len(counts),
                adoption_rate=(
                    len(team_customization_engineers[team_key])
                    / len(team_engineers.get(team_key, set()))
                    if team_engineers.get(team_key)
                    else 0.0
                ),
                avg_effectiveness_score=(
                    round(avg_team_effectiveness, 1) if avg_team_effectiveness is not None else None
                ),
                top_customizations=[
                    _team_customization_label(customization_key, identifier_counts)
                    for customization_key, _count in counts.most_common(5)
                ],
                unique_customizations=[
                    _team_customization_label(
                        (
                            customization_type,
                            identifier,
                            provenance,
                            source_classification,
                        ),
                        identifier_counts,
                    )
                    for (
                        customization_type,
                        identifier,
                        provenance,
                        source_classification,
                    ), _count in counts.most_common()
                    if len(
                        customization_presence_by_team[
                            (
                                customization_type,
                                identifier,
                                provenance,
                                source_classification,
                            )
                        ]
                    )
                    == 1
                ][:5],
            )
        )

    customization_outcome_buckets: dict[tuple[str, ...], dict] = {}
    for bucket in customization_data.values():
        engineer_ids = bucket["engineers"]
        if not engineer_ids:
            continue
        cohort_share = len(engineer_ids) / total_engineers if total_engineers > 0 else None

        effectiveness_values = [
            profile_by_engineer_id[eid].effectiveness_score
            for eid in engineer_ids
            if eid in profile_by_engineer_id
        ]
        leverage_values = [
            profile_by_engineer_id[eid].leverage_score
            for eid in engineer_ids
            if eid in profile_by_engineer_id
        ]
        success_values = [eng_success_rates.get(eid) for eid in engineer_ids]
        cost_values = [eng_cost_per_success.get(eid) for eid in engineer_ids]
        merge_values = [eng_merge_rates.get(eid) for eid in engineer_ids]

        avg_eff = _avg(effectiveness_values)
        avg_lev = _avg(leverage_values)
        avg_suc = _avg(success_values)
        avg_cost = _avg(cost_values)
        avg_merge = _avg(merge_values)

        customization_outcome_buckets[
            (
                "customization",
                bucket["customization_type"],
                bucket["identifier"],
                bucket["provenance"],
                bucket["source_classification"],
            )
        ] = CustomizationOutcomeAttribution(
            dimension="customization",
            label=bucket["identifier"],
            customization_type=bucket["customization_type"],
            provenance=bucket["provenance"],
            source_classification=bucket["source_classification"],
            support_engineer_count=len(engineer_ids),
            support_session_count=len(bucket["sessions"]),
            avg_effectiveness_score=(round(avg_eff, 1) if avg_eff is not None else None),
            avg_leverage_score=round(avg_lev or 0.0, 1),
            avg_success_rate=(round(avg_suc, 3) if avg_suc is not None else None),
            avg_cost_per_successful_outcome=(round(avg_cost, 4) if avg_cost is not None else None),
            avg_pr_merge_rate=(round(avg_merge, 3) if avg_merge is not None else None),
            cohort_share=round(cohort_share, 3) if cohort_share is not None else None,
        )

    high_performer_stacks: list[HighPerformerStack] = []
    scored_profiles = [
        profile for profile in engineer_profiles if profile.effectiveness_score is not None
    ]
    ranked_profiles = (
        sorted(
            scored_profiles,
            key=lambda profile: (
                -(profile.effectiveness_score or 0.0),
                -profile.leverage_score,
            ),
        )
        if scored_profiles
        else engineer_profiles
    )
    top_cohort_size = max(1, (len(ranked_profiles) + 3) // 4) if ranked_profiles else 0
    high_performer_ids = {profile.engineer_id for profile in ranked_profiles[:top_cohort_size]}
    stack_buckets: dict[tuple[tuple[str, str, str, str], ...], dict] = {}
    for engineer_id in high_performer_ids:
        customization_counts = engineer_explicit_customizations.get(engineer_id, Counter())
        if not customization_counts:
            continue

        top_customizations = customization_counts.most_common(3)
        stack_key = tuple(key for key, _count in top_customizations)
        bucket = stack_buckets.setdefault(
            stack_key,
            {
                "customization_totals": Counter(),
                "engineers": set(),
                "sessions": set(),
                "projects": Counter(),
                "effectiveness_scores": [],
                "leverage_scores": [],
                "engineer_names": [],
            },
        )
        bucket["engineers"].add(engineer_id)
        profile = profile_by_engineer_id.get(engineer_id)
        if profile is not None:
            if profile.effectiveness_score is not None:
                bucket["effectiveness_scores"].append(profile.effectiveness_score)
            bucket["leverage_scores"].append(profile.leverage_score)
            bucket["engineer_names"].append(profile.name)
        eng_sessions = engineer_customization_sessions.get(engineer_id, {})
        eng_projects = engineer_customization_projects.get(engineer_id, {})
        for customization_key, invocation_count in top_customizations:
            bucket["customization_totals"][customization_key] += invocation_count
            bucket["sessions"].update(eng_sessions.get(customization_key, set()))
            bucket["projects"].update(eng_projects.get(customization_key, Counter()))

    for stack_key, bucket in sorted(
        stack_buckets.items(),
        key=lambda item: (
            -len(item[1]["engineers"]),
            -(
                sum(item[1]["effectiveness_scores"]) / len(item[1]["effectiveness_scores"])
                if item[1]["effectiveness_scores"]
                else 0.0
            ),
        ),
    ):
        label = " + ".join(
            identifier for _type, identifier, _provenance, _source_classification in stack_key
        )
        stack_id_source = "|".join(
            f"{ctype}:{ident}:{prov}:{source_classification}"
            for ctype, ident, prov, source_classification in stack_key
        )
        stack_id = md5(stack_id_source.encode(), usedforsecurity=False).hexdigest()[:12]
        high_performer_stacks.append(
            HighPerformerStack(
                stack_id=stack_id,
                label=label,
                customizations=[
                    StackCustomization(
                        identifier=identifier,
                        customization_type=customization_type,
                        provenance=provenance,
                        source_classification=source_classification,
                        invocation_count=bucket["customization_totals"][
                            (
                                customization_type,
                                identifier,
                                provenance,
                                source_classification,
                            )
                        ],
                    )
                    for (
                        customization_type,
                        identifier,
                        provenance,
                        source_classification,
                    ) in stack_key
                ],
                engineer_count=len(bucket["engineers"]),
                session_count=len(bucket["sessions"]),
                avg_effectiveness_score=(
                    round(
                        sum(bucket["effectiveness_scores"]) / len(bucket["effectiveness_scores"]),
                        1,
                    )
                    if bucket["effectiveness_scores"]
                    else None
                ),
                avg_leverage_score=round(
                    sum(bucket["leverage_scores"]) / len(bucket["leverage_scores"]),
                    1,
                ),
                top_projects=[project for project, _count in bucket["projects"].most_common(3)],
                top_engineers=sorted(bucket["engineer_names"])[:3],
            )
        )

        stack_success_values = [
            eng_success_rates.get(engineer_id) for engineer_id in bucket["engineers"]
        ]
        stack_cost_values = [
            eng_cost_per_success.get(engineer_id)
            for engineer_id in bucket["engineers"]
            if eng_cost_per_success.get(engineer_id) is not None
        ]
        stack_merge_values = [
            eng_merge_rates.get(engineer_id)
            for engineer_id in bucket["engineers"]
            if eng_merge_rates.get(engineer_id) is not None
        ]
        avg_stack_suc = _avg(stack_success_values)
        avg_stack_cost = _avg(stack_cost_values)
        avg_stack_merge = _avg(stack_merge_values)
        stack_outcome = CustomizationOutcomeAttribution(
            dimension="stack",
            label=label,
            customization_type=None,
            provenance=None,
            source_classification=None,
            support_engineer_count=len(bucket["engineers"]),
            support_session_count=len(bucket["sessions"]),
            avg_effectiveness_score=(
                round(
                    sum(bucket["effectiveness_scores"]) / len(bucket["effectiveness_scores"]),
                    1,
                )
                if bucket["effectiveness_scores"]
                else None
            ),
            avg_leverage_score=round(
                sum(bucket["leverage_scores"]) / len(bucket["leverage_scores"]),
                1,
            ),
            avg_success_rate=(round(avg_stack_suc, 3) if avg_stack_suc is not None else None),
            avg_cost_per_successful_outcome=(
                round(avg_stack_cost, 4) if avg_stack_cost is not None else None
            ),
            avg_pr_merge_rate=(round(avg_stack_merge, 3) if avg_stack_merge is not None else None),
            cohort_share=(
                round(len(bucket["engineers"]) / total_engineers, 3)
                if total_engineers > 0
                else None
            ),
        )
        customization_outcome_buckets[("stack", stack_id)] = stack_outcome

    customization_outcomes = sorted(
        customization_outcome_buckets.values(),
        key=lambda row: (
            0 if row.dimension == "customization" else 1,
            -(row.avg_effectiveness_score or 0.0),
            -row.support_engineer_count,
            row.label,
        ),
    )

    # 6. Project readiness
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
    explicit_customization_adoption_rate = (
        len(engineers_using_explicit_customizations) / total_engineers
        if total_engineers > 0
        else 0.0
    )
    model_div_avg = (
        sum(all_model_diversities) / len(all_model_diversities) if all_model_diversities else 0.0
    )

    return MaturityAnalyticsResponse(
        tool_categories=tool_categories,
        engineer_profiles=engineer_profiles,
        daily_leverage=daily_leverage,
        agent_skill_breakdown=agent_skill_breakdown,
        customization_breakdown=customization_breakdown,
        high_performer_stacks=high_performer_stacks,
        team_customization_landscape=team_customization_landscape,
        customization_state_funnel=customization_state_funnel,
        toolchain_reliability=toolchain_reliability,
        delegation_patterns=delegation_patterns,
        agent_team_modes=agent_team_modes,
        customization_outcomes=customization_outcomes,
        project_readiness=project_readiness,
        sessions_analyzed=sessions_analyzed,
        avg_leverage_score=round(avg_leverage, 1),
        avg_effectiveness_score=(
            round(avg_effectiveness, 1) if avg_effectiveness is not None else None
        ),
        orchestration_adoption_rate=round(adoption_rate, 3),
        team_orchestration_adoption_rate=round(team_adoption_rate, 3),
        explicit_customization_adoption_rate=round(explicit_customization_adoption_rate, 3),
        model_diversity_avg=round(model_div_avg, 3),
    )
