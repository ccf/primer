import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.common.models import (
    Engineer,
    ModelUsage,
    SessionFacets,
    SessionWorkflowProfile,
    ToolUsage,
)
from primer.common.models import Session as SessionModel
from primer.common.pricing import estimate_cost
from primer.common.schemas import (
    BrightSpot,
    CohortMetrics,
    ConfigOptimizationResponse,
    ConfigSuggestion,
    EngineerApproach,
    EngineerLearningPath,
    EngineerRampup,
    EngineerSkillProfile,
    ExemplarPatternReference,
    ExemplarSession,
    LearningPathsResponse,
    LearningRecommendation,
    LearningRecommendationExemplar,
    NewHireProgress,
    OnboardingAccelerationResponse,
    OnboardingRecommendation,
    PatternSharingResponse,
    PersonalizedTip,
    PersonalizedTipsResponse,
    SharedPattern,
    SimilarSession,
    SimilarSessionsResponse,
    SkillInventoryResponse,
    TeamSkillGap,
    TimeToTeamAverageResponse,
    WeeklySuccessPoint,
)
from primer.server.services.analytics_service import base_session_query


def _shannon_entropy(counts: dict[str, int]) -> float:
    """Compute Shannon entropy from a dict of counts."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return round(entropy, 3)


def _proficiency_level(call_count: int) -> str:
    if call_count >= 50:
        return "expert"
    if call_count >= 20:
        return "proficient"
    if call_count >= 5:
        return "moderate"
    return "novice"


def _sortable_started_at(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


# ---------------------------------------------------------------------------
# Config Optimization
# ---------------------------------------------------------------------------


def get_config_optimization(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> ConfigOptimizationResponse:
    base_q = base_session_query(db, team_id, engineer_id, start_date, end_date)
    sessions = base_q.all()
    suggestions: list[ConfigSuggestion] = []

    if not sessions:
        return ConfigOptimizationResponse(suggestions=[], sessions_analyzed=0)

    # Use a subquery for IN clauses to avoid SQLite's 999 variable limit
    session_ids_subq = base_q.with_entities(SessionModel.id).subquery()
    session_ids_q = db.query(session_ids_subq.c.id)

    # 1. Repeated session types → hook suggestion
    facets = (
        db.query(SessionFacets.session_type)
        .filter(
            SessionFacets.session_id.in_(session_ids_q),
            SessionFacets.session_type.isnot(None),
        )
        .all()
    )
    type_counts: Counter[str] = Counter(f.session_type for f in facets)
    for stype, count in type_counts.items():
        if count >= 5:
            suggestions.append(
                ConfigSuggestion(
                    category="hook",
                    title=f"Automate '{stype}' sessions with a hook",
                    description=(
                        f"The session type '{stype}' appeared {count} times. "
                        "Consider creating a Claude Code hook to streamline this workflow."
                    ),
                    severity="info",
                    evidence={"session_type": stype, "count": count},
                    suggested_config=(
                        f'{{"hooks": {{"on_session_start": '
                        f'[{{"match": "{stype}", "command": "your-script"}}]}}}}'
                    ),
                )
            )

    # 2. Conservative permission mode with high tool calls
    default_mode_sessions = [
        s for s in sessions if s.permission_mode and s.permission_mode.lower() == "default"
    ]
    if default_mode_sessions:
        avg_tools = sum(s.tool_call_count for s in default_mode_sessions) / len(
            default_mode_sessions
        )
        ratio = len(default_mode_sessions) / len(sessions)
        if ratio > 0.5 and avg_tools > 20:
            suggestions.append(
                ConfigSuggestion(
                    category="permission",
                    title="Consider upgrading permission mode",
                    description=(
                        f"{ratio:.0%} of sessions use default permission mode with an average "
                        f"of {avg_tools:.0f} tool calls. Upgrading to auto-accept-reads could "
                        "reduce interruptions."
                    ),
                    severity="warning",
                    evidence={
                        "default_mode_ratio": round(ratio, 2),
                        "avg_tool_calls": round(avg_tools, 1),
                    },
                    suggested_config='{"permission_mode": "auto-accept-reads"}',
                )
            )

    # 3. Expensive models for simple tasks
    simple_sessions_with_opus = [
        s
        for s in sessions
        if s.tool_call_count < 5 and s.primary_model and "opus" in s.primary_model.lower()
    ]
    if len(simple_sessions_with_opus) >= 3:
        suggestions.append(
            ConfigSuggestion(
                category="model",
                title="Use lighter models for simple tasks",
                description=(
                    f"{len(simple_sessions_with_opus)} sessions used Opus for tasks with "
                    "<5 tool calls. Consider using Sonnet or Haiku for simpler tasks."
                ),
                severity="warning",
                evidence={"simple_opus_sessions": len(simple_sessions_with_opus)},
                suggested_config='{"model": "sonnet"}',
            )
        )

    # 4. Heavy Bash usage → MCP suggestion
    bash_usages = (
        db.query(ToolUsage.session_id, ToolUsage.call_count)
        .filter(
            ToolUsage.session_id.in_(session_ids_q),
            ToolUsage.tool_name == "Bash",
        )
        .all()
    )
    high_bash_sessions = [u for u in bash_usages if u.call_count >= 10]
    if len(high_bash_sessions) >= 3:
        avg_bash = sum(u.call_count for u in high_bash_sessions) / len(high_bash_sessions)
        suggestions.append(
            ConfigSuggestion(
                category="mcp",
                title="Wrap frequent Bash commands as MCP tools",
                description=(
                    f"{len(high_bash_sessions)} sessions have 10+ Bash calls "
                    f"(avg {avg_bash:.0f}). Consider creating MCP tools for common commands."
                ),
                severity="info",
                evidence={
                    "high_bash_sessions": len(high_bash_sessions),
                    "avg_bash_calls": round(avg_bash, 1),
                },
            )
        )

    # 5. Underutilized Task tool
    if len(sessions) >= 20:
        task_usage_count = (
            db.query(func.count(ToolUsage.id))
            .filter(
                ToolUsage.session_id.in_(session_ids_q),
                ToolUsage.tool_name == "Task",
            )
            .scalar()
        )
        if task_usage_count == 0:
            suggestions.append(
                ConfigSuggestion(
                    category="workflow",
                    title="Try using the Task tool for complex work",
                    description=(
                        f"Across {len(sessions)} sessions, no Task tool usage was detected. "
                        "Subagent delegation can help with complex, multi-step workflows."
                    ),
                    severity="info",
                    evidence={"sessions_analyzed": len(sessions)},
                )
            )

    return ConfigOptimizationResponse(
        suggestions=suggestions,
        sessions_analyzed=len(sessions),
    )


# ---------------------------------------------------------------------------
# Personalized Tips
# ---------------------------------------------------------------------------


def get_personalized_tips(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> PersonalizedTipsResponse:
    tips: list[PersonalizedTip] = []

    # Get engineer's sessions
    eng_base_q = base_session_query(db, team_id, engineer_id, start_date, end_date)
    eng_sessions = eng_base_q.all()
    if not eng_sessions:
        return PersonalizedTipsResponse(tips=[], sessions_analyzed=0, engineer_id=engineer_id)

    # Subquery for IN clauses to avoid SQLite's 999 variable limit
    eng_ids_subq = eng_base_q.with_entities(SessionModel.id).subquery()
    eng_session_ids_q = db.query(eng_ids_subq.c.id)

    # Get engineer's tools
    eng_tools_q = (
        db.query(ToolUsage.tool_name, func.sum(ToolUsage.call_count))
        .filter(ToolUsage.session_id.in_(eng_session_ids_q))
        .group_by(ToolUsage.tool_name)
        .all()
    )
    eng_tool_map = {name: count for name, count in eng_tools_q}
    eng_tool_names = set(eng_tool_map.keys())

    # Get team context for comparison (only meaningful with a specific engineer)
    resolved_team_id = None
    if engineer_id:
        if team_id:
            resolved_team_id = team_id
        else:
            eng = db.query(Engineer.team_id).filter(Engineer.id == engineer_id).first()
            if eng:
                resolved_team_id = eng.team_id

    if resolved_team_id:
        # Team-wide tool usage
        team_session_ids_q = (
            db.query(SessionModel.id).join(Engineer).filter(Engineer.team_id == resolved_team_id)
        )
        if start_date:
            team_session_ids_q = team_session_ids_q.filter(SessionModel.started_at >= start_date)
        if end_date:
            team_session_ids_q = team_session_ids_q.filter(SessionModel.started_at <= end_date)
        team_ids_subq = team_session_ids_q.subquery()
        team_session_ids_sq = db.query(team_ids_subq.c.id)

        team_engineer_count = (
            db.query(func.count(func.distinct(SessionModel.engineer_id)))
            .filter(SessionModel.id.in_(team_session_ids_sq))
            .scalar()
            or 0
        )

        if team_engineer_count > 1:
            # 1. Tool gap detection
            team_tool_engineers = (
                db.query(
                    ToolUsage.tool_name,
                    func.count(func.distinct(SessionModel.engineer_id)),
                )
                .join(SessionModel, ToolUsage.session_id == SessionModel.id)
                .filter(ToolUsage.session_id.in_(team_session_ids_sq))
                .group_by(ToolUsage.tool_name)
                .all()
            )
            for tool_name, eng_count in team_tool_engineers:
                adoption = eng_count / team_engineer_count
                if adoption >= 0.5 and tool_name not in eng_tool_names:
                    tips.append(
                        PersonalizedTip(
                            category="tool_gap",
                            title=f"Try the {tool_name} tool",
                            description=(
                                f"{eng_count}/{team_engineer_count} teammates use {tool_name}, "
                                "but you haven't used it yet."
                            ),
                            severity="info",
                            evidence={
                                "tool": tool_name,
                                "team_adoption": round(adoption, 2),
                            },
                        )
                    )

            # 3. High friction rate vs peers
            eng_friction_count = 0
            eng_facets = (
                db.query(SessionFacets.friction_counts)
                .filter(
                    SessionFacets.session_id.in_(eng_session_ids_q),
                    SessionFacets.friction_counts.isnot(None),
                )
                .all()
            )
            for (fc,) in eng_facets:
                if isinstance(fc, dict):
                    eng_friction_count += sum(fc.values())

            team_friction_total = 0
            team_facets = (
                db.query(SessionFacets.friction_counts)
                .filter(
                    SessionFacets.session_id.in_(team_session_ids_sq),
                    SessionFacets.friction_counts.isnot(None),
                )
                .all()
            )
            for (fc,) in team_facets:
                if isinstance(fc, dict):
                    team_friction_total += sum(fc.values())

            team_avg_friction = (
                team_friction_total / team_engineer_count if team_engineer_count else 0
            )
            if team_avg_friction > 0 and eng_friction_count > 2 * team_avg_friction:
                tips.append(
                    PersonalizedTip(
                        category="friction",
                        title="Higher friction rate than teammates",
                        description=(
                            f"Your friction count ({eng_friction_count}) is more than "
                            f"2x the team average ({team_avg_friction:.0f}). "
                            "Consider reviewing your workflow for common blockers."
                        ),
                        severity="warning",
                        evidence={
                            "your_friction": eng_friction_count,
                            "team_avg": round(team_avg_friction, 1),
                        },
                    )
                )

            # 5. Never uses Task tool while peers do
            if "Task" not in eng_tool_names:
                team_task_users = (
                    db.query(func.count(func.distinct(SessionModel.engineer_id)))
                    .join(ToolUsage, ToolUsage.session_id == SessionModel.id)
                    .filter(
                        ToolUsage.session_id.in_(team_session_ids_sq),
                        ToolUsage.tool_name == "Task",
                    )
                    .scalar()
                    or 0
                )
                if team_task_users > 0:
                    tips.append(
                        PersonalizedTip(
                            category="workflow",
                            title="Try delegating with the Task tool",
                            description=(
                                f"{team_task_users} teammate(s) use the Task tool for "
                                "subagent delegation. It can help with complex workflows."
                            ),
                            severity="info",
                            evidence={"team_task_users": team_task_users},
                        )
                    )

    # 2. Low tool diversity (doesn't need team context)
    if len(eng_tool_names) < 3 and len(eng_sessions) >= 3:
        tips.append(
            PersonalizedTip(
                category="diversity",
                title="Expand your tool usage",
                description=(
                    f"You've used only {len(eng_tool_names)} distinct tool(s) across "
                    f"{len(eng_sessions)} sessions. Exploring more tools like Grep, Glob, "
                    "or Edit could improve productivity."
                ),
                severity="info",
                evidence={
                    "tools_used": sorted(eng_tool_names),
                    "session_count": len(eng_sessions),
                },
            )
        )

    # 4. Low success rate for a session type
    eng_facets_with_outcome = (
        db.query(SessionFacets.session_type, SessionFacets.outcome)
        .filter(
            SessionFacets.session_id.in_(eng_session_ids_q),
            SessionFacets.session_type.isnot(None),
            SessionFacets.outcome.isnot(None),
        )
        .all()
    )
    type_outcomes: dict[str, list[str]] = defaultdict(list)
    for stype, outcome in eng_facets_with_outcome:
        normalized_outcome = canonical_outcome(outcome)
        if normalized_outcome is not None:
            type_outcomes[stype].append(normalized_outcome)

    for stype, outcomes in type_outcomes.items():
        if len(outcomes) >= 3:
            successes = sum(1 for outcome in outcomes if is_success_outcome(outcome))
            rate = successes / len(outcomes)
            if rate < 0.5:
                tips.append(
                    PersonalizedTip(
                        category="success",
                        title=f"Low success rate for '{stype}' sessions",
                        description=(
                            f"Only {rate:.0%} of your '{stype}' sessions succeeded "
                            f"({successes}/{len(outcomes)}). Consider alternative approaches."
                        ),
                        severity="warning",
                        evidence={
                            "session_type": stype,
                            "success_rate": round(rate, 2),
                            "total": len(outcomes),
                        },
                    )
                )

    return PersonalizedTipsResponse(
        tips=tips,
        sessions_analyzed=len(eng_sessions),
        engineer_id=engineer_id,
    )


# ---------------------------------------------------------------------------
# Skill Inventory
# ---------------------------------------------------------------------------


def get_skill_inventory(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> SkillInventoryResponse:
    # Build base query for sessions in scope
    base_q = base_session_query(db, team_id, engineer_id, start_date, end_date)
    sessions = base_q.all()

    if not sessions:
        return SkillInventoryResponse(
            engineer_profiles=[],
            team_skill_gaps=[],
            total_engineers=0,
            total_session_types=0,
            total_tools_used=0,
        )

    # Use a subquery for IN clauses to avoid SQLite's 999 variable limit
    session_ids_subq = base_q.with_entities(SessionModel.id).subquery()
    session_ids_q = db.query(session_ids_subq.c.id)

    # Group sessions by engineer
    eng_sessions: dict[str, list] = defaultdict(list)
    for s in sessions:
        eng_sessions[s.engineer_id].append(s)

    # Get engineer names
    engineer_ids = list(eng_sessions.keys())
    engineers = db.query(Engineer.id, Engineer.name).filter(Engineer.id.in_(engineer_ids)).all()
    eng_names = {eid: name for eid, name in engineers}

    # Get all facets for session types
    all_facets = (
        db.query(SessionFacets.session_id, SessionFacets.session_type)
        .filter(
            SessionFacets.session_id.in_(session_ids_q),
            SessionFacets.session_type.isnot(None),
        )
        .all()
    )
    session_to_type: dict[str, str] = {f.session_id: f.session_type for f in all_facets}

    # Get all tool usages
    all_tools = (
        db.query(ToolUsage.session_id, ToolUsage.tool_name, ToolUsage.call_count)
        .filter(ToolUsage.session_id.in_(session_ids_q))
        .all()
    )

    # Build session_id → engineer_id lookup for O(1) mapping
    session_to_engineer: dict[str, str] = {}
    for eid, sess_list in eng_sessions.items():
        for s in sess_list:
            session_to_engineer[s.id] = eid

    # Group tool usage by engineer
    eng_tool_calls: dict[str, Counter] = defaultdict(Counter)
    for tu in all_tools:
        eid = session_to_engineer.get(tu.session_id)
        if eid:
            eng_tool_calls[eid][tu.tool_name] += tu.call_count

    # Build profiles
    all_session_types: set[str] = set()
    all_tool_names: set[str] = set()
    profiles: list[EngineerSkillProfile] = []

    for eid, sess_list in eng_sessions.items():
        # Session types
        type_counts: Counter[str] = Counter()
        for s in sess_list:
            st = session_to_type.get(s.id)
            if st:
                type_counts[st] += 1
        all_session_types.update(type_counts.keys())

        # Tool proficiency
        tool_prof: dict[str, str] = {}
        for tool_name, count in eng_tool_calls[eid].items():
            tool_prof[tool_name] = _proficiency_level(count)
            all_tool_names.add(tool_name)

        # Project count
        projects = {s.project_name for s in sess_list if s.project_name}

        profiles.append(
            EngineerSkillProfile(
                engineer_id=eid,
                name=eng_names.get(eid, "Unknown"),
                session_types=dict(type_counts),
                tool_proficiency=tool_prof,
                project_count=len(projects),
                total_sessions=len(sess_list),
                diversity_score=_shannon_entropy(type_counts),
            )
        )

    # Team skill gaps — check coverage for session types and tools
    total_engineers = len(engineer_ids)
    gaps: list[TeamSkillGap] = []

    # Session type coverage
    for stype in sorted(all_session_types):
        engineers_with = sum(1 for p in profiles if stype in p.session_types)
        coverage = engineers_with / total_engineers if total_engineers else 0
        if coverage < 0.3:
            gaps.append(
                TeamSkillGap(
                    skill=stype,
                    coverage_pct=round(coverage * 100, 1),
                    total_engineers=total_engineers,
                    engineers_with_skill=engineers_with,
                )
            )

    # Tool coverage
    for tool in sorted(all_tool_names):
        engineers_with = sum(1 for p in profiles if tool in p.tool_proficiency)
        coverage = engineers_with / total_engineers if total_engineers else 0
        if coverage < 0.3:
            gaps.append(
                TeamSkillGap(
                    skill=tool,
                    coverage_pct=round(coverage * 100, 1),
                    total_engineers=total_engineers,
                    engineers_with_skill=engineers_with,
                )
            )

    return SkillInventoryResponse(
        engineer_profiles=profiles,
        team_skill_gaps=gaps,
        total_engineers=total_engineers,
        total_session_types=len(all_session_types),
        total_tools_used=len(all_tool_names),
    )


# ---------------------------------------------------------------------------
# Learning Paths
# ---------------------------------------------------------------------------


def get_learning_paths(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> LearningPathsResponse:
    base_q = base_session_query(db, team_id, engineer_id, start_date, end_date)
    sessions = base_q.all()

    if not sessions:
        return LearningPathsResponse(engineer_paths=[], team_skill_universe={}, sessions_analyzed=0)

    session_ids_subq = base_q.with_entities(SessionModel.id).subquery()
    session_ids_q = db.query(session_ids_subq.c.id)

    # Group sessions by engineer
    eng_sessions: dict[str, list] = defaultdict(list)
    for s in sessions:
        eng_sessions[s.engineer_id].append(s)

    # Engineer names
    engineer_ids = list(eng_sessions.keys())
    engineers = db.query(Engineer.id, Engineer.name).filter(Engineer.id.in_(engineer_ids)).all()
    eng_names = {eid: name for eid, name in engineers}

    # Session types per session
    all_facets = (
        db.query(
            SessionFacets.session_id,
            SessionFacets.session_type,
            SessionFacets.goal_categories,
        )
        .filter(SessionFacets.session_id.in_(session_ids_q))
        .all()
    )
    session_to_type: dict[str, str] = {}
    session_to_goals: dict[str, list[str]] = {}
    for f in all_facets:
        if f.session_type:
            session_to_type[f.session_id] = f.session_type
        if f.goal_categories:
            cats = f.goal_categories
            if isinstance(cats, str):
                try:
                    cats = json.loads(cats)
                except (json.JSONDecodeError, TypeError):
                    cats = []
            if isinstance(cats, list):
                session_to_goals[f.session_id] = cats

    # Build session_id → engineer_id
    session_to_engineer: dict[str, str] = {}
    for eid, sess_list in eng_sessions.items():
        for s in sess_list:
            session_to_engineer[s.id] = eid

    # Tool usages
    all_tools = (
        db.query(ToolUsage.session_id, ToolUsage.tool_name, ToolUsage.call_count)
        .filter(ToolUsage.session_id.in_(session_ids_q))
        .all()
    )
    eng_tool_names: dict[str, set[str]] = defaultdict(set)
    for tu in all_tools:
        eid = session_to_engineer.get(tu.session_id)
        if eid:
            eng_tool_names[eid].add(tu.tool_name)

    total_engineers = len(engineer_ids)

    # Build team skill universe
    # Session types: skill → count of engineers using it
    eng_session_types: dict[str, set[str]] = defaultdict(set)
    for sid, stype in session_to_type.items():
        eid = session_to_engineer.get(sid)
        if eid:
            eng_session_types[eid].add(stype)

    team_type_universe: Counter[str] = Counter()
    for eid in engineer_ids:
        for stype in eng_session_types.get(eid, set()):
            team_type_universe[stype] += 1

    team_tool_universe: Counter[str] = Counter()
    for eid in engineer_ids:
        for tool in eng_tool_names.get(eid, set()):
            team_tool_universe[tool] += 1

    # Goal categories per engineer
    eng_goal_cats: dict[str, set[str]] = defaultdict(set)
    for sid, cats in session_to_goals.items():
        eid = session_to_engineer.get(sid)
        if eid:
            for c in cats:
                eng_goal_cats[eid].add(c)

    team_goal_universe: Counter[str] = Counter()
    for eid in engineer_ids:
        for cat in eng_goal_cats.get(eid, set()):
            team_goal_universe[cat] += 1

    # Skill universe for response: prefix keys to avoid name collisions
    team_skill_universe: dict[str, int] = {}
    for stype, cnt in team_type_universe.items():
        team_skill_universe[f"type:{stype}"] = cnt
    for tool, cnt in team_tool_universe.items():
        team_skill_universe[f"tool:{tool}"] = cnt

    team_skill_count = len(team_skill_universe) if team_skill_universe else 1
    pattern_sharing = get_pattern_sharing(
        db,
        team_id=team_id,
        engineer_id=engineer_id if team_id is None else None,
        start_date=start_date,
        end_date=end_date,
    )
    exemplar_sessions = pattern_sharing.exemplar_sessions

    paths: list[EngineerLearningPath] = []
    for eid in engineer_ids:
        recs: list[LearningRecommendation] = []
        sess_list = eng_sessions[eid]
        my_types = eng_session_types.get(eid, set())
        my_tools = eng_tool_names.get(eid, set())
        my_goals = eng_goal_cats.get(eid, set())

        # 1. Session type gaps
        for stype, cnt in team_type_universe.items():
            adoption = cnt / total_engineers
            if adoption >= 0.5 and stype not in my_types:
                recs.append(
                    LearningRecommendation(
                        category="session_type_gap",
                        skill_area=stype,
                        title=f"Try '{stype}' sessions",
                        description=(
                            f"{cnt}/{total_engineers} teammates work on '{stype}' "
                            "sessions, but you haven't yet."
                        ),
                        priority="high",
                        evidence={"team_adoption": round(adoption, 2), "team_count": cnt},
                        exemplars=_select_learning_recommendation_exemplars(
                            "session_type_gap",
                            stype,
                            exemplar_sessions,
                        ),
                    )
                )

        # 2. Tool gaps
        for tool, cnt in team_tool_universe.items():
            adoption = cnt / total_engineers
            if adoption >= 0.4 and tool not in my_tools:
                priority = "high" if adoption >= 0.7 else "medium"
                recs.append(
                    LearningRecommendation(
                        category="tool_gap",
                        skill_area=tool,
                        title=f"Learn the {tool} tool",
                        description=(
                            f"{cnt}/{total_engineers} teammates use {tool}, "
                            "but you haven't used it yet."
                        ),
                        priority=priority,
                        evidence={"team_adoption": round(adoption, 2), "team_count": cnt},
                        exemplars=_select_learning_recommendation_exemplars(
                            "tool_gap",
                            tool,
                            exemplar_sessions,
                        ),
                    )
                )

        # 3. Goal category gaps
        for cat, cnt in team_goal_universe.items():
            adoption = cnt / total_engineers
            if adoption >= 0.3 and cat not in my_goals:
                recs.append(
                    LearningRecommendation(
                        category="goal_gap",
                        skill_area=cat,
                        title=f"Explore '{cat}' goals",
                        description=(
                            f"{cnt}/{total_engineers} teammates work on '{cat}' "
                            "goals, but you haven't yet."
                        ),
                        priority="medium",
                        evidence={"team_adoption": round(adoption, 2), "team_count": cnt},
                        exemplars=_select_learning_recommendation_exemplars(
                            "goal_gap",
                            cat,
                            exemplar_sessions,
                        ),
                    )
                )

        # 4. Complexity progression
        sorted_sessions = sorted(sess_list, key=lambda s: _sortable_started_at(s.started_at))
        complexity_trend = "flat"
        if len(sorted_sessions) >= 5:
            first_chunk = sorted_sessions[: min(10, len(sorted_sessions) // 2)]
            recent_chunk = sorted_sessions[-min(10, len(sorted_sessions) // 2) :]
            first_avg = sum(s.tool_call_count + s.message_count for s in first_chunk) / len(
                first_chunk
            )
            recent_avg = sum(s.tool_call_count + s.message_count for s in recent_chunk) / len(
                recent_chunk
            )
            if first_avg > 0:
                change = (recent_avg - first_avg) / first_avg
                if change > 0.1:
                    complexity_trend = "increasing"
                elif change < -0.1:
                    complexity_trend = "decreasing"

            if complexity_trend == "decreasing" and len(sorted_sessions) >= 20:
                recs.append(
                    LearningRecommendation(
                        category="complexity",
                        skill_area="task complexity",
                        title="Complexity trend is declining",
                        description=(
                            "Your recent sessions show lower complexity than earlier ones. "
                            "Consider tackling more challenging tasks."
                        ),
                        priority="low",
                        evidence={
                            "first_avg": round(first_avg, 1),
                            "recent_avg": round(recent_avg, 1),
                        },
                        exemplars=_select_learning_recommendation_exemplars(
                            "complexity",
                            "task complexity",
                            exemplar_sessions,
                        ),
                    )
                )

        # 5. Coverage score (prefixed keys match team denominator)
        my_skill_count = len(my_types) + len(my_tools)
        coverage_score = round(my_skill_count / team_skill_count, 3) if team_skill_count else 0.0
        coverage_score = min(coverage_score, 1.0)

        paths.append(
            EngineerLearningPath(
                engineer_id=eid,
                name=eng_names.get(eid, "Unknown"),
                total_sessions=len(sess_list),
                recommendations=recs,
                coverage_score=coverage_score,
                complexity_trend=complexity_trend,
            )
        )

    return LearningPathsResponse(
        engineer_paths=paths,
        team_skill_universe=team_skill_universe,
        sessions_analyzed=len(sessions),
    )


# ---------------------------------------------------------------------------
# Pattern Sharing
# ---------------------------------------------------------------------------


def get_pattern_sharing(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> PatternSharingResponse:
    base_q = base_session_query(db, team_id, engineer_id, start_date, end_date)
    sessions = base_q.all()

    if not sessions:
        return PatternSharingResponse(patterns=[], total_clusters_found=0, sessions_analyzed=0)

    session_ids_subq = base_q.with_entities(SessionModel.id).subquery()
    session_ids_q = db.query(session_ids_subq.c.id)

    # Build lookups
    session_map: dict[str, object] = {s.id: s for s in sessions}
    session_to_engineer: dict[str, str] = {s.id: s.engineer_id for s in sessions}

    engineer_ids = list({s.engineer_id for s in sessions})
    engineers = db.query(Engineer.id, Engineer.name).filter(Engineer.id.in_(engineer_ids)).all()
    eng_names = {eid: name for eid, name in engineers}

    # Facets
    all_facets = (
        db.query(
            SessionFacets.session_id,
            SessionFacets.session_type,
            SessionFacets.outcome,
            SessionFacets.agent_helpfulness,
            SessionFacets.brief_summary,
            SessionFacets.goal_categories,
        )
        .filter(SessionFacets.session_id.in_(session_ids_q))
        .all()
    )
    session_facets: dict[str, object] = {}
    for f in all_facets:
        session_facets[f.session_id] = f

    # Tool usages per session
    all_tools = (
        db.query(ToolUsage.session_id, ToolUsage.tool_name, ToolUsage.call_count)
        .filter(ToolUsage.session_id.in_(session_ids_q))
        .all()
    )
    session_tools: dict[str, list[str]] = defaultdict(list)
    session_tool_count: dict[str, int] = defaultdict(int)
    for tu in all_tools:
        session_tools[tu.session_id].append(tu.tool_name)
        session_tool_count[tu.session_id] += tu.call_count

    session_workflows = {
        row.session_id: {
            "archetype": row.archetype,
            "label": row.label,
            "steps": list(row.steps or []),
        }
        for row in (
            db.query(
                SessionWorkflowProfile.session_id,
                SessionWorkflowProfile.archetype,
                SessionWorkflowProfile.label,
                SessionWorkflowProfile.steps,
            )
            .filter(SessionWorkflowProfile.session_id.in_(session_ids_q))
            .all()
        )
    }

    session_costs: dict[str, float] = defaultdict(float)
    model_rows = (
        db.query(
            ModelUsage.session_id,
            ModelUsage.model_name,
            func.sum(ModelUsage.input_tokens).label("input_tokens"),
            func.sum(ModelUsage.output_tokens).label("output_tokens"),
            func.sum(ModelUsage.cache_read_tokens).label("cache_read_tokens"),
            func.sum(ModelUsage.cache_creation_tokens).label("cache_creation_tokens"),
        )
        .filter(ModelUsage.session_id.in_(session_ids_q))
        .group_by(ModelUsage.session_id, ModelUsage.model_name)
        .all()
    )
    for row in model_rows:
        session_costs[row.session_id] += estimate_cost(
            row.model_name,
            row.input_tokens or 0,
            row.output_tokens or 0,
            row.cache_read_tokens or 0,
            row.cache_creation_tokens or 0,
        )

    def _make_approach(sid: str) -> EngineerApproach:
        s = session_map[sid]
        eid = session_to_engineer[sid]
        facet = session_facets.get(sid)
        return EngineerApproach(
            engineer_id=eid,
            name=eng_names.get(eid, "Unknown"),
            session_id=sid,
            duration_seconds=s.duration_seconds,
            tool_count=session_tool_count.get(sid, 0),
            outcome=canonical_outcome(facet.outcome) if facet else None,
            helpfulness=facet.agent_helpfulness if facet else None,
            tools_used=sorted(set(session_tools.get(sid, []))),
        )

    def _build_pattern(
        cluster_key: str,
        cluster_type: str,
        cluster_label: str,
        sids: list[str],
    ) -> SharedPattern:
        approaches = [_make_approach(sid) for sid in sids]
        eng_set = {a.engineer_id for a in approaches}

        # Best approach: successful + shortest duration
        successful = [
            approach
            for approach in approaches
            if is_success_outcome(approach.outcome) and approach.duration_seconds
        ]
        best = min(successful, key=lambda a: a.duration_seconds) if successful else None

        durations = [a.duration_seconds for a in approaches if a.duration_seconds is not None]
        avg_dur = sum(durations) / len(durations) if durations else None

        outcomes = [a.outcome for a in approaches if a.outcome]
        successes = sum(1 for outcome in outcomes if is_success_outcome(outcome))
        sr = round(successes / len(outcomes), 3) if outcomes else None

        # Insight
        insight_parts = [f"{len(eng_set)} engineers worked on {cluster_label}"]
        if best and avg_dur and avg_dur > 0:
            pct = round((1 - best.duration_seconds / avg_dur) * 100)
            if pct > 0:
                insight_parts.append(f"{best.name}'s approach was {pct}% faster")
        insight = "; ".join(insight_parts)

        cid = hashlib.md5(
            f"{cluster_type}:{cluster_key}".encode(), usedforsecurity=False
        ).hexdigest()[:12]

        return SharedPattern(
            cluster_id=cid,
            cluster_type=cluster_type,
            cluster_label=cluster_label,
            session_count=len(sids),
            engineer_count=len(eng_set),
            approaches=approaches,
            best_approach=best,
            avg_duration=round(avg_dur, 1) if avg_dur else None,
            success_rate=sr,
            insight=insight,
        )

    patterns: list[SharedPattern] = []

    # 1. Session type + project clusters
    type_project_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for s in sessions:
        facet = session_facets.get(s.id)
        if facet and facet.session_type and s.project_name:
            type_project_groups[(facet.session_type, s.project_name)].append(s.id)

    for (stype, proj), sids in type_project_groups.items():
        eng_set = {session_to_engineer[sid] for sid in sids}
        if len(eng_set) >= 2:
            label = f"{stype} on {proj}"
            patterns.append(_build_pattern(f"{stype}:{proj}", "session_type", label, sids))

    # 2. Goal category clusters
    goal_groups: dict[str, list[str]] = defaultdict(list)
    for f in all_facets:
        cats = f.goal_categories
        if cats:
            if isinstance(cats, str):
                try:
                    cats = json.loads(cats)
                except (json.JSONDecodeError, TypeError):
                    cats = []
            if isinstance(cats, list):
                for cat in cats:
                    goal_groups[cat].append(f.session_id)

    for cat, sids in goal_groups.items():
        # Filter to valid session ids
        valid_sids = [sid for sid in sids if sid in session_map]
        eng_set = {session_to_engineer[sid] for sid in valid_sids}
        if len(eng_set) >= 2 and len(valid_sids) >= 3:
            patterns.append(_build_pattern(f"goal:{cat}", "goal_category", cat, valid_sids))

    # 3. Project-only clusters
    project_groups: dict[str, list[str]] = defaultdict(list)
    for s in sessions:
        if s.project_name:
            project_groups[s.project_name].append(s.id)

    # Track projects already covered by type+project clusters
    covered_projects: set[str] = set()
    for (_, proj), sids_tp in type_project_groups.items():
        if len({session_to_engineer[sid] for sid in sids_tp}) >= 2:
            covered_projects.add(proj)

    for proj, sids in project_groups.items():
        eng_set = {session_to_engineer[sid] for sid in sids}
        if len(eng_set) >= 2 and proj not in covered_projects:
            patterns.append(_build_pattern(f"project:{proj}", "project", proj, sids))

    # Sort by engineer_count desc
    patterns.sort(key=lambda p: p.engineer_count, reverse=True)

    return PatternSharingResponse(
        patterns=patterns,
        bright_spots=_derive_bright_spots(patterns),
        exemplar_sessions=_derive_exemplar_sessions(
            patterns,
            session_map=session_map,
            session_facets=session_facets,
            session_tools=session_tools,
            session_workflows=session_workflows,
            session_costs=session_costs,
        ),
        total_clusters_found=len(patterns),
        sessions_analyzed=len(sessions),
    )


def _derive_bright_spots(patterns: list[SharedPattern], limit: int = 3) -> list[BrightSpot]:
    candidates = [
        pattern
        for pattern in patterns
        if pattern.best_approach is not None
        and pattern.success_rate is not None
        and pattern.success_rate >= 0.75
        and pattern.engineer_count >= 2
        and pattern.session_count >= 3
    ]
    candidates.sort(
        key=lambda pattern: (
            -(pattern.success_rate or 0.0),
            -pattern.engineer_count,
            -pattern.session_count,
            pattern.avg_duration or float("inf"),
        )
    )

    bright_spots: list[BrightSpot] = []
    for pattern in candidates[:limit]:
        exemplar = pattern.best_approach
        if exemplar is None:
            continue
        bright_spots.append(
            BrightSpot(
                bright_spot_id=pattern.cluster_id,
                title=f"Bright spot: {pattern.cluster_label}",
                summary=(
                    f"{pattern.engineer_count} engineers converged on this pattern across "
                    f"{pattern.session_count} sessions. {exemplar.name}'s exemplar session is the "
                    "best place to copy the approach."
                ),
                cluster_type=pattern.cluster_type,
                cluster_label=pattern.cluster_label,
                session_count=pattern.session_count,
                engineer_count=pattern.engineer_count,
                success_rate=pattern.success_rate,
                avg_duration=pattern.avg_duration,
                exemplar_session_id=exemplar.session_id,
                exemplar_engineer_id=exemplar.engineer_id,
                exemplar_engineer_name=exemplar.name,
                exemplar_duration_seconds=exemplar.duration_seconds,
                exemplar_tools=exemplar.tools_used,
            )
        )
    return bright_spots


def _select_learning_recommendation_exemplars(
    category: str,
    skill_area: str,
    exemplars: list[ExemplarSession],
    limit: int = 2,
) -> list[LearningRecommendationExemplar]:
    matches: list[tuple[ExemplarSession, str]] = []

    for exemplar in exemplars:
        reason = _learning_exemplar_reason(category, skill_area, exemplar)
        if reason is not None:
            matches.append((exemplar, reason))

    matches.sort(
        key=lambda item: (
            -(item[0].success_rate or 0.0),
            -item[0].supporting_engineer_count,
            -item[0].supporting_session_count,
            item[0].estimated_cost if item[0].estimated_cost is not None else float("inf"),
            item[0].title,
        )
    )

    return [
        LearningRecommendationExemplar(
            session_id=exemplar.session_id,
            title=exemplar.title,
            engineer_name=exemplar.engineer_name,
            project_name=exemplar.project_name,
            summary=exemplar.session_summary,
            relevance_reason=reason,
            workflow_archetype=exemplar.workflow_archetype,
            workflow_fingerprint=exemplar.workflow_fingerprint,
            duration_seconds=exemplar.duration_seconds,
            estimated_cost=exemplar.estimated_cost,
            tools_used=exemplar.tools_used,
        )
        for exemplar, reason in matches[:limit]
    ]


def _learning_exemplar_reason(
    category: str, skill_area: str, exemplar: ExemplarSession
) -> str | None:
    if category == "session_type_gap":
        if any(
            pattern.cluster_type == "session_type"
            and pattern.cluster_label.startswith(f"{skill_area} on ")
            for pattern in exemplar.linked_patterns
        ):
            return f"Strong peer example of a '{skill_area}' workflow."
        return None

    if category == "goal_gap":
        if any(
            pattern.cluster_type == "goal_category" and pattern.cluster_label == skill_area
            for pattern in exemplar.linked_patterns
        ):
            return f"Relevant exemplar for '{skill_area}' work."
        return None

    if category == "tool_gap":
        if skill_area in exemplar.tools_used:
            return f"Shows {skill_area} in a successful peer workflow."
        return None

    if category == "complexity":
        if len(exemplar.workflow_steps) >= 3 or len(exemplar.tools_used) >= 3:
            return "A stronger multi-step workflow to study when ramping complexity back up."
        return None

    return None


def _derive_exemplar_sessions(
    patterns: list[SharedPattern],
    *,
    session_map: dict[str, SessionModel],
    session_facets: dict[str, object],
    session_tools: dict[str, list[str]],
    session_workflows: dict[str, dict[str, object]],
    session_costs: dict[str, float],
    limit: int = 6,
) -> list[ExemplarSession]:
    cluster_type_order = {
        "session_type": 0,
        "goal_category": 1,
        "project": 2,
    }
    buckets: dict[str, dict[str, object]] = {}

    for pattern in patterns:
        exemplar = pattern.best_approach
        if exemplar is None:
            continue

        bucket = buckets.setdefault(
            exemplar.session_id,
            {
                "approach": exemplar,
                "linked_patterns": [],
                "supporting_session_count": 0,
                "supporting_engineer_count": 0,
                "success_rate": None,
            },
        )
        linked_patterns = bucket["linked_patterns"]
        assert isinstance(linked_patterns, list)
        linked_patterns.append(
            ExemplarPatternReference(
                cluster_id=pattern.cluster_id,
                cluster_type=pattern.cluster_type,
                cluster_label=pattern.cluster_label,
                session_count=pattern.session_count,
                engineer_count=pattern.engineer_count,
                success_rate=pattern.success_rate,
            )
        )
        bucket["supporting_session_count"] = max(
            int(bucket["supporting_session_count"]),
            pattern.session_count,
        )
        bucket["supporting_engineer_count"] = max(
            int(bucket["supporting_engineer_count"]),
            pattern.engineer_count,
        )
        current_success_rate = bucket["success_rate"]
        if current_success_rate is None or (
            pattern.success_rate is not None and pattern.success_rate > current_success_rate
        ):
            bucket["success_rate"] = pattern.success_rate

    exemplars: list[ExemplarSession] = []
    for session_id, bucket in buckets.items():
        approach = bucket["approach"]
        assert isinstance(approach, EngineerApproach)
        session = session_map[session_id]
        facet = session_facets.get(session_id)
        workflow = session_workflows.get(session_id, {})
        linked_patterns = bucket["linked_patterns"]
        assert isinstance(linked_patterns, list)
        linked_patterns.sort(
            key=lambda item: (
                cluster_type_order.get(item.cluster_type, 99),
                -item.engineer_count,
                -item.session_count,
                -(item.success_rate or 0.0),
                item.cluster_label,
            )
        )
        primary_pattern = linked_patterns[0]
        related_pattern_count = max(len(linked_patterns) - 1, 0)
        linked_pattern_phrase = (
            " It also anchors "
            f"{related_pattern_count} related pattern"
            f"{'' if related_pattern_count == 1 else 's'}."
            if related_pattern_count > 0
            else ""
        )
        why_selected = (
            f"Chosen as the fastest successful example for {primary_pattern.cluster_label}."
            f"{linked_pattern_phrase}"
        )

        title = str(workflow.get("label") or primary_pattern.cluster_label)
        summary = (
            f"Backed by {bucket['supporting_engineer_count']} engineers across "
            f"{bucket['supporting_session_count']} sessions."
        )
        session_summary = getattr(facet, "brief_summary", None) or session.summary
        exemplars.append(
            ExemplarSession(
                exemplar_id=f"exemplar:{session_id}",
                title=title,
                summary=summary,
                why_selected=why_selected,
                session_id=session_id,
                engineer_id=approach.engineer_id,
                engineer_name=approach.name,
                project_name=session.project_name,
                outcome=approach.outcome,
                helpfulness=getattr(facet, "agent_helpfulness", None),
                session_summary=session_summary,
                duration_seconds=session.duration_seconds,
                estimated_cost=(
                    round(session_costs[session_id], 4) if session_id in session_costs else None
                ),
                tools_used=sorted(set(session_tools.get(session_id, []))),
                workflow_archetype=workflow.get("archetype"),
                workflow_fingerprint=workflow.get("label"),
                workflow_steps=list(workflow.get("steps") or []),
                supporting_session_count=int(bucket["supporting_session_count"]),
                supporting_engineer_count=int(bucket["supporting_engineer_count"]),
                supporting_pattern_count=len(linked_patterns),
                success_rate=bucket["success_rate"],
                linked_patterns=linked_patterns[:3],
            )
        )

    exemplars.sort(
        key=lambda exemplar: (
            -(exemplar.success_rate or 0.0),
            -exemplar.supporting_engineer_count,
            -exemplar.supporting_session_count,
            exemplar.estimated_cost if exemplar.estimated_cost is not None else float("inf"),
            exemplar.title,
        )
    )
    return exemplars[:limit]


# ---------------------------------------------------------------------------
# Onboarding Acceleration
# ---------------------------------------------------------------------------


def get_onboarding_acceleration(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> OnboardingAccelerationResponse:
    base_q = base_session_query(db, team_id, engineer_id, start_date, end_date)
    sessions = base_q.all()

    if not sessions:
        return OnboardingAccelerationResponse(
            cohorts=[],
            new_hire_progress=[],
            recommendations=[],
            sessions_analyzed=0,
            experienced_benchmark=None,
        )

    session_ids_subq = base_q.with_entities(SessionModel.id).subquery()
    session_ids_q = db.query(session_ids_subq.c.id)

    now = datetime.now(UTC)

    # Group sessions by engineer
    eng_sessions: dict[str, list] = defaultdict(list)
    for s in sessions:
        eng_sessions[s.engineer_id].append(s)

    engineer_ids = list(eng_sessions.keys())
    engineers = db.query(Engineer.id, Engineer.name).filter(Engineer.id.in_(engineer_ids)).all()
    eng_names = {eid: name for eid, name in engineers}

    # Tool usages per session
    all_tools = (
        db.query(ToolUsage.session_id, ToolUsage.tool_name)
        .filter(ToolUsage.session_id.in_(session_ids_q))
        .all()
    )
    session_tools: dict[str, set[str]] = defaultdict(set)
    for tu in all_tools:
        session_tools[tu.session_id].add(tu.tool_name)

    # Facets
    all_facets = (
        db.query(
            SessionFacets.session_id,
            SessionFacets.session_type,
            SessionFacets.outcome,
            SessionFacets.friction_counts,
        )
        .filter(SessionFacets.session_id.in_(session_ids_q))
        .all()
    )
    session_outcome: dict[str, str] = {}
    session_friction: dict[str, int] = {}
    session_type_map: dict[str, str] = {}
    for f in all_facets:
        if f.outcome:
            normalized_outcome = canonical_outcome(f.outcome)
            if normalized_outcome is not None:
                session_outcome[f.session_id] = normalized_outcome
        if f.session_type:
            session_type_map[f.session_id] = f.session_type
        if f.friction_counts and isinstance(f.friction_counts, dict):
            session_friction[f.session_id] = sum(f.friction_counts.values())

    # Cohort segmentation by true first session date (ignoring date range filter)
    def _ensure_utc(dt: datetime) -> datetime:
        return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt

    first_session_rows = (
        db.query(SessionModel.engineer_id, func.min(SessionModel.started_at))
        .filter(SessionModel.engineer_id.in_(engineer_ids))
        .group_by(SessionModel.engineer_id)
        .all()
    )
    eng_first_session: dict[str, datetime] = {}
    for eid, first_dt in first_session_rows:
        if first_dt:
            eng_first_session[eid] = _ensure_utc(first_dt)

    def _cohort_label(eid: str) -> str:
        first = eng_first_session.get(eid)
        if not first:
            return "experienced"
        # Make first timezone-aware if needed
        if first.tzinfo is None:
            first = first.replace(tzinfo=UTC)
        days = (now - first).days
        if days <= 30:
            return "new_hire"
        if days <= 90:
            return "ramping"
        return "experienced"

    cohort_engineers: dict[str, list[str]] = defaultdict(list)
    for eid in engineer_ids:
        cohort_engineers[_cohort_label(eid)].append(eid)

    # Per-engineer metrics
    def _eng_metrics(eid: str) -> dict:
        sess_list = eng_sessions[eid]
        tools_used: set[str] = set()
        for s in sess_list:
            tools_used.update(session_tools.get(s.id, set()))

        outcomes = [session_outcome.get(s.id) for s in sess_list]
        outcomes = [o for o in outcomes if o]
        successes = sum(1 for outcome in outcomes if is_success_outcome(outcome))
        sr = round(successes / len(outcomes), 3) if outcomes else None

        durations = [s.duration_seconds for s in sess_list if s.duration_seconds is not None]
        avg_dur = sum(durations) / len(durations) if durations else None

        frictions = [session_friction.get(s.id, 0) for s in sess_list]
        total_friction = sum(frictions)
        friction_rate = round(total_friction / len(sess_list), 3) if sess_list else 0.0

        types_used: Counter[str] = Counter()
        for s in sess_list:
            st = session_type_map.get(s.id)
            if st:
                types_used[st] += 1

        return {
            "total_sessions": len(sess_list),
            "tool_diversity": len(tools_used),
            "tools": tools_used,
            "success_rate": sr,
            "avg_duration": round(avg_dur, 1) if avg_dur else None,
            "friction_rate": friction_rate,
            "session_types": types_used,
        }

    eng_metrics = {eid: _eng_metrics(eid) for eid in engineer_ids}

    # Build cohort metrics
    def _build_cohort(label: str, eids: list[str]) -> CohortMetrics:
        if not eids:
            return CohortMetrics(
                cohort_label=label,
                engineer_count=0,
                avg_sessions_per_engineer=0,
                avg_tool_diversity=0,
                avg_duration_seconds=None,
                success_rate=None,
                avg_friction_rate=0,
                top_tools=[],
                top_session_types=[],
            )

        metrics = [eng_metrics[eid] for eid in eids]
        total_sess = sum(m["total_sessions"] for m in metrics)
        avg_sess = total_sess / len(eids)
        avg_div = sum(m["tool_diversity"] for m in metrics) / len(eids)

        durations = [m["avg_duration"] for m in metrics if m["avg_duration"] is not None]
        avg_dur = sum(durations) / len(durations) if durations else None

        srs = [m["success_rate"] for m in metrics if m["success_rate"] is not None]
        sr = round(sum(srs) / len(srs), 3) if srs else None

        avg_fr = sum(m["friction_rate"] for m in metrics) / len(eids)

        all_tools_counter: Counter[str] = Counter()
        all_types_counter: Counter[str] = Counter()
        for m in metrics:
            all_tools_counter.update(m["tools"])
            all_types_counter.update(m["session_types"].keys())

        return CohortMetrics(
            cohort_label=label,
            engineer_count=len(eids),
            avg_sessions_per_engineer=round(avg_sess, 1),
            avg_tool_diversity=round(avg_div, 1),
            avg_duration_seconds=round(avg_dur, 1) if avg_dur else None,
            success_rate=sr,
            avg_friction_rate=round(avg_fr, 3),
            top_tools=[t for t, _ in all_tools_counter.most_common(5)],
            top_session_types=[t for t, _ in all_types_counter.most_common(5)],
        )

    cohorts: list[CohortMetrics] = []
    for label in ["new_hire", "ramping", "experienced"]:
        eids = cohort_engineers.get(label, [])
        if eids:
            cohorts.append(_build_cohort(label, eids))

    experienced_benchmark = next((c for c in cohorts if c.cohort_label == "experienced"), None)

    # New hire progress
    new_hire_eids = cohort_engineers.get("new_hire", [])
    new_hire_progress: list[NewHireProgress] = []

    for eid in new_hire_eids:
        m = eng_metrics[eid]
        first = eng_first_session.get(eid)
        if first:
            if first.tzinfo is None:
                first = first.replace(tzinfo=UTC)
            days = (now - first).days
        else:
            days = 0

        # Velocity score (0-100)
        # 30% tool diversity, 30% success rate, 20% sessions/day, 20% inv friction
        velocity = 0.0

        if experienced_benchmark and experienced_benchmark.avg_tool_diversity > 0:
            tool_ratio = min(m["tool_diversity"] / experienced_benchmark.avg_tool_diversity, 1.0)
            velocity += 30 * tool_ratio

        sr = m["success_rate"]
        if sr is not None:
            velocity += 30 * sr

        if days > 0:
            sess_per_day = m["total_sessions"] / days
            # Cap at 2 sessions/day as "good"
            velocity += 20 * min(sess_per_day / 2, 1.0)

        # Inverse friction (lower = better)
        fr = m["friction_rate"]
        velocity += 20 * max(0, 1 - fr)

        velocity = round(min(velocity, 100), 1)

        # Lagging areas
        lagging: list[str] = []
        if experienced_benchmark:
            if (
                experienced_benchmark.avg_tool_diversity > 0
                and m["tool_diversity"] < 0.6 * experienced_benchmark.avg_tool_diversity
            ):
                lagging.append("tool diversity")
            if (
                experienced_benchmark.success_rate is not None
                and sr is not None
                and experienced_benchmark.success_rate > 0
                and sr < 0.6 * experienced_benchmark.success_rate
            ):
                lagging.append("success rate")
            if (
                experienced_benchmark.avg_friction_rate > 0
                and fr > 1.5 * experienced_benchmark.avg_friction_rate
            ):
                lagging.append("friction rate")
            if (
                experienced_benchmark.avg_sessions_per_engineer > 0
                and m["total_sessions"] < 0.6 * experienced_benchmark.avg_sessions_per_engineer
            ):
                lagging.append("session volume")

        new_hire_progress.append(
            NewHireProgress(
                engineer_id=eid,
                name=eng_names.get(eid, "Unknown"),
                days_since_first_session=days,
                total_sessions=m["total_sessions"],
                tool_diversity=m["tool_diversity"],
                success_rate=sr,
                avg_duration=m["avg_duration"],
                friction_rate=fr,
                velocity_score=velocity,
                lagging_areas=lagging,
            )
        )

    # Recommendations
    recommendations: list[OnboardingRecommendation] = []

    if experienced_benchmark and new_hire_eids:
        new_hire_cohort = next((c for c in cohorts if c.cohort_label == "new_hire"), None)
        if new_hire_cohort:
            # Team-wide recs
            if (
                experienced_benchmark.avg_friction_rate > 0
                and new_hire_cohort.avg_friction_rate > 2 * experienced_benchmark.avg_friction_rate
            ):
                recommendations.append(
                    OnboardingRecommendation(
                        category="friction",
                        title="New hires experiencing high friction",
                        description=(
                            f"New hire friction rate ({new_hire_cohort.avg_friction_rate:.2f}) "
                            f"is over 2x the experienced rate "
                            f"({experienced_benchmark.avg_friction_rate:.2f})."
                        ),
                        target_engineer_id=None,
                        evidence={
                            "new_hire_friction": new_hire_cohort.avg_friction_rate,
                            "experienced_friction": experienced_benchmark.avg_friction_rate,
                        },
                    )
                )

            if (
                experienced_benchmark.avg_tool_diversity > 0
                and new_hire_cohort.avg_tool_diversity
                < 0.5 * experienced_benchmark.avg_tool_diversity
            ):
                recommendations.append(
                    OnboardingRecommendation(
                        category="tool_adoption",
                        title="New hires underusing available tools",
                        description=(
                            f"New hire tool diversity ({new_hire_cohort.avg_tool_diversity:.1f}) "
                            f"is less than 50% of experienced engineers "
                            f"({experienced_benchmark.avg_tool_diversity:.1f})."
                        ),
                        target_engineer_id=None,
                        evidence={
                            "new_hire_diversity": new_hire_cohort.avg_tool_diversity,
                            "experienced_diversity": experienced_benchmark.avg_tool_diversity,
                        },
                    )
                )

            if new_hire_cohort.success_rate is not None and new_hire_cohort.success_rate < 0.7:
                recommendations.append(
                    OnboardingRecommendation(
                        category="mentoring",
                        title="New hire success rate below 70%",
                        description=(
                            f"New hires have a {new_hire_cohort.success_rate:.0%} success rate. "
                            "Consider pairing them with experienced engineers."
                        ),
                        target_engineer_id=None,
                        evidence={"success_rate": new_hire_cohort.success_rate},
                    )
                )

        # Individual recs for low velocity
        for nhp in new_hire_progress:
            if nhp.velocity_score < 50:
                recommendations.append(
                    OnboardingRecommendation(
                        category="mentoring",
                        title=f"Pair {nhp.name} with an experienced engineer",
                        description=(
                            f"{nhp.name}'s velocity score ({nhp.velocity_score}) is below 50. "
                            f"Lagging areas: {', '.join(nhp.lagging_areas) or 'general'}."
                        ),
                        target_engineer_id=nhp.engineer_id,
                        evidence={
                            "velocity_score": nhp.velocity_score,
                            "lagging_areas": nhp.lagging_areas,
                        },
                    )
                )

    return OnboardingAccelerationResponse(
        cohorts=cohorts,
        new_hire_progress=new_hire_progress,
        recommendations=recommendations,
        sessions_analyzed=len(sessions),
        experienced_benchmark=experienced_benchmark,
    )


# ---------------------------------------------------------------------------
# Similar Sessions (Contextual Pattern Sharing)
# ---------------------------------------------------------------------------


def get_similar_sessions(
    db: Session,
    session_id: str,
    limit: int = 10,
    requesting_engineer_id: str | None = None,
) -> SimilarSessionsResponse:
    """Find sessions similar to the target, within the same team."""
    # Load target session and its facets
    target = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not target:
        return SimilarSessionsResponse(
            similar_sessions=[],
            target_session_type=None,
            target_project=None,
            total_found=0,
        )

    target_facets = db.query(SessionFacets).filter(SessionFacets.session_id == session_id).first()
    target_type = target_facets.session_type if target_facets else None
    target_project = target.project_name
    target_goals: list[str] = []
    if target_facets and target_facets.goal_categories:
        cats = target_facets.goal_categories
        if isinstance(cats, str):
            try:
                cats = json.loads(cats)
            except (json.JSONDecodeError, TypeError):
                cats = []
        if isinstance(cats, list):
            target_goals = cats

    # Find the target's team
    target_engineer = db.query(Engineer).filter(Engineer.id == target.engineer_id).first()
    target_team_id = target_engineer.team_id if target_engineer else None

    # Build candidate query: same team, exclude self
    # If requesting_engineer_id is set, restrict to that engineer's sessions only
    # (enforces data isolation for the engineer role)
    q = db.query(SessionModel).filter(SessionModel.id != session_id)
    if requesting_engineer_id:
        q = q.filter(SessionModel.engineer_id == requesting_engineer_id)
    elif target_team_id:
        q = q.join(Engineer).filter(Engineer.team_id == target_team_id)
    else:
        # No team — scope to same engineer only
        q = q.filter(SessionModel.engineer_id == target.engineer_id)

    candidates = q.all()
    if not candidates:
        return SimilarSessionsResponse(
            similar_sessions=[],
            target_session_type=target_type,
            target_project=target_project,
            total_found=0,
        )

    # Gather candidate facets and tools
    # Use subquery to avoid SQLite 999-variable limit
    cand_subq = q.with_entities(SessionModel.id).subquery()
    cand_ids_q = db.query(cand_subq.c.id)

    cand_facets = db.query(SessionFacets).filter(SessionFacets.session_id.in_(cand_ids_q)).all()
    facets_map: dict[str, SessionFacets] = {f.session_id: f for f in cand_facets}

    cand_tools = (
        db.query(ToolUsage.session_id, ToolUsage.tool_name)
        .filter(ToolUsage.session_id.in_(cand_ids_q))
        .all()
    )
    tools_map: dict[str, list[str]] = defaultdict(list)
    for tu in cand_tools:
        tools_map[tu.session_id].append(tu.tool_name)

    # Engineer names/avatars
    eng_ids = list({c.engineer_id for c in candidates})
    eng_rows = (
        db.query(Engineer.id, Engineer.name, Engineer.avatar_url)
        .filter(Engineer.id.in_(eng_ids))
        .all()
    )
    eng_info = {e.id: (e.name, e.avatar_url) for e in eng_rows}

    # Score candidates
    scored: list[tuple[int, bool, float | None, SessionModel]] = []
    for c in candidates:
        f = facets_map.get(c.id)
        c_type = f.session_type if f else None
        c_project = c.project_name
        c_goals: list[str] = []
        if f and f.goal_categories:
            cats = f.goal_categories
            if isinstance(cats, str):
                try:
                    cats = json.loads(cats)
                except (json.JSONDecodeError, TypeError):
                    cats = []
            if isinstance(cats, list):
                c_goals = cats

        # Relevance: 3 = type+project, 2 = type only, 1 = goal overlap, 0 = no match
        relevance = 0
        reason = "same_goal"
        if target_type and c_type == target_type and target_project and c_project == target_project:
            relevance = 3
            reason = "same_type_and_project"
        elif target_type and c_type == target_type:
            relevance = 2
            reason = "same_type"
        elif target_goals and c_goals and set(target_goals) & set(c_goals):
            relevance = 1
            reason = "same_goal"
        else:
            continue  # skip non-matching

        c_outcome = canonical_outcome(f.outcome) if f else None
        is_success = is_success_outcome(c_outcome)
        dur = c.duration_seconds if c.duration_seconds is not None else float("inf")

        scored.append((relevance, is_success, dur, c, reason))

    # Sort: highest relevance, success first, shortest duration
    scored.sort(key=lambda x: (-x[0], not x[1], x[2] if x[2] is not None else float("inf")))

    results: list[SimilarSession] = []
    for _relevance, _is_success, _dur, c, reason in scored[:limit]:
        f = facets_map.get(c.id)
        ename, eavatar = eng_info.get(c.engineer_id, ("Unknown", None))
        results.append(
            SimilarSession(
                session_id=c.id,
                engineer_id=c.engineer_id,
                engineer_name=ename,
                engineer_avatar_url=eavatar,
                project_name=c.project_name,
                session_type=f.session_type if f else None,
                outcome=canonical_outcome(f.outcome) if f else None,
                duration_seconds=c.duration_seconds,
                tools_used=sorted(set(tools_map.get(c.id, []))),
                similarity_reason=reason,
                started_at=c.started_at.isoformat() if c.started_at else None,
            )
        )

    return SimilarSessionsResponse(
        similar_sessions=results,
        target_session_type=target_type,
        target_project=target_project,
        total_found=len(scored),
    )


# ---------------------------------------------------------------------------
# Time to Team Average
# ---------------------------------------------------------------------------


def get_time_to_team_average(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> TimeToTeamAverageResponse:
    """For each engineer, compute how many weeks until their rolling success
    rate reached the team average."""
    base_q = base_session_query(db, team_id, engineer_id, start_date, end_date)
    sessions = base_q.all()

    if not sessions:
        return TimeToTeamAverageResponse(
            engineers=[],
            team_avg_success_rate=0.0,
            avg_weeks_to_match=None,
            engineers_who_matched=0,
            total_engineers=0,
        )

    session_ids_subq = base_q.with_entities(SessionModel.id).subquery()
    session_ids_q = db.query(session_ids_subq.c.id)

    # Get facets for outcomes
    all_facets = (
        db.query(SessionFacets.session_id, SessionFacets.outcome)
        .filter(
            SessionFacets.session_id.in_(session_ids_q),
            SessionFacets.outcome.isnot(None),
        )
        .all()
    )
    outcome_map: dict[str, str] = {}
    for facet in all_facets:
        normalized_outcome = canonical_outcome(facet.outcome)
        if normalized_outcome is not None:
            outcome_map[facet.session_id] = normalized_outcome

    # Compute team average success rate
    outcomes_all = list(outcome_map.values())
    if not outcomes_all:
        return TimeToTeamAverageResponse(
            engineers=[],
            team_avg_success_rate=0.0,
            avg_weeks_to_match=None,
            engineers_who_matched=0,
            total_engineers=0,
        )
    team_avg_sr = sum(1 for outcome in outcomes_all if is_success_outcome(outcome)) / len(
        outcomes_all
    )

    # Group sessions by engineer
    eng_sessions: dict[str, list] = defaultdict(list)
    for s in sessions:
        eng_sessions[s.engineer_id].append(s)

    # Engineer names + first session dates
    engineer_ids = list(eng_sessions.keys())
    eng_rows = db.query(Engineer.id, Engineer.name).filter(Engineer.id.in_(engineer_ids)).all()
    eng_names = {eid: name for eid, name in eng_rows}

    # Use all-time first session date for accurate ramp-up timing
    first_session_rows = (
        db.query(SessionModel.engineer_id, func.min(SessionModel.started_at))
        .filter(SessionModel.engineer_id.in_(engineer_ids))
        .group_by(SessionModel.engineer_id)
        .all()
    )
    eng_first: dict[str, datetime] = {}
    for eid, first_dt in first_session_rows:
        if first_dt:
            eng_first[eid] = first_dt

    engineers: list[EngineerRampup] = []
    matched_count = 0
    weeks_list: list[int] = []

    for eid in engineer_ids:
        sess_list = eng_sessions[eid]
        first_dt = eng_first.get(eid)
        if not first_dt:
            continue

        # Sort by started_at
        sess_list.sort(key=lambda s: _sortable_started_at(s.started_at))

        # Group into weekly buckets by offset from first session
        weekly_buckets: dict[int, list[str]] = defaultdict(list)
        for s in sess_list:
            if not s.started_at:
                continue
            delta = _sortable_started_at(s.started_at) - _sortable_started_at(first_dt)
            if hasattr(delta, "total_seconds"):
                week_num = int(delta.total_seconds() / (7 * 86400))
            else:
                week_num = 0
            outcome = outcome_map.get(s.id)
            if outcome:
                weekly_buckets[week_num].append(outcome)

        if not weekly_buckets:
            engineers.append(
                EngineerRampup(
                    engineer_id=eid,
                    name=eng_names.get(eid, "Unknown"),
                    first_session_date=first_dt.isoformat(),
                    weeks_to_team_average=None,
                    current_success_rate=None,
                    weekly_success_rates=[],
                )
            )
            continue

        # Compute weekly success rates
        max_week = max(weekly_buckets.keys())
        weekly_points: list[WeeklySuccessPoint] = []
        weeks_to_match: int | None = None
        rolling_outcomes: list[str] = []

        for wk in range(max_week + 1):
            bucket = weekly_buckets.get(wk, [])
            rolling_outcomes.extend(bucket)
            count = len(bucket)
            if rolling_outcomes:
                sr = sum(1 for outcome in rolling_outcomes if is_success_outcome(outcome)) / len(
                    rolling_outcomes
                )
            else:
                sr = None

            weekly_points.append(
                WeeklySuccessPoint(
                    week_number=wk,
                    success_rate=round(sr, 3) if sr is not None else None,
                    session_count=count,
                )
            )

            if weeks_to_match is None and sr is not None and sr >= team_avg_sr:
                weeks_to_match = wk

        # Current success rate
        current_outcomes = [outcome_map.get(s.id) for s in sess_list if outcome_map.get(s.id)]
        current_sr = (
            sum(1 for outcome in current_outcomes if is_success_outcome(outcome))
            / len(current_outcomes)
            if current_outcomes
            else None
        )

        if weeks_to_match is not None:
            matched_count += 1
            weeks_list.append(weeks_to_match)

        engineers.append(
            EngineerRampup(
                engineer_id=eid,
                name=eng_names.get(eid, "Unknown"),
                first_session_date=first_dt.isoformat(),
                weeks_to_team_average=weeks_to_match,
                current_success_rate=round(current_sr, 3) if current_sr is not None else None,
                weekly_success_rates=weekly_points,
            )
        )

    avg_weeks = round(sum(weeks_list) / len(weeks_list), 1) if weeks_list else None

    return TimeToTeamAverageResponse(
        engineers=engineers,
        team_avg_success_rate=round(team_avg_sr, 3),
        avg_weeks_to_match=avg_weeks,
        engineers_who_matched=matched_count,
        total_engineers=len(engineers),
    )
