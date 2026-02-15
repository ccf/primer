import math
from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from primer.common.models import Engineer, SessionFacets, ToolUsage
from primer.common.models import Session as SessionModel
from primer.common.schemas import (
    ConfigOptimizationResponse,
    ConfigSuggestion,
    EngineerSkillProfile,
    PersonalizedTip,
    PersonalizedTipsResponse,
    SkillInventoryResponse,
    TeamSkillGap,
)
from primer.server.services.analytics_service import (
    _base_session_query,
)


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
    sessions = _base_session_query(db, team_id, engineer_id, start_date, end_date).all()
    suggestions: list[ConfigSuggestion] = []

    if not sessions:
        return ConfigOptimizationResponse(suggestions=[], sessions_analyzed=0)

    session_ids = [s.id for s in sessions]

    # 1. Repeated session types → hook suggestion
    facets = (
        db.query(SessionFacets.session_type)
        .filter(
            SessionFacets.session_id.in_(session_ids),
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
            ToolUsage.session_id.in_(session_ids),
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
                ToolUsage.session_id.in_(session_ids),
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
    eng_sessions = _base_session_query(db, team_id, engineer_id, start_date, end_date).all()
    if not eng_sessions:
        return PersonalizedTipsResponse(tips=[], sessions_analyzed=0, engineer_id=engineer_id)

    eng_session_ids = [s.id for s in eng_sessions]

    # Get engineer's tools
    eng_tools_q = (
        db.query(ToolUsage.tool_name, func.sum(ToolUsage.call_count))
        .filter(ToolUsage.session_id.in_(eng_session_ids))
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
        team_session_ids = [r[0] for r in team_session_ids_q.all()]

        team_engineer_count = (
            db.query(func.count(func.distinct(SessionModel.engineer_id)))
            .filter(SessionModel.id.in_(team_session_ids))
            .scalar()
            or 0
        )

        if team_engineer_count > 1 and team_session_ids:
            # 1. Tool gap detection
            team_tool_engineers = (
                db.query(
                    ToolUsage.tool_name,
                    func.count(func.distinct(SessionModel.engineer_id)),
                )
                .join(SessionModel, ToolUsage.session_id == SessionModel.id)
                .filter(ToolUsage.session_id.in_(team_session_ids))
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
                    SessionFacets.session_id.in_(eng_session_ids),
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
                    SessionFacets.session_id.in_(team_session_ids),
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
                        ToolUsage.session_id.in_(team_session_ids),
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
            SessionFacets.session_id.in_(eng_session_ids),
            SessionFacets.session_type.isnot(None),
            SessionFacets.outcome.isnot(None),
        )
        .all()
    )
    type_outcomes: dict[str, list[str]] = defaultdict(list)
    for stype, outcome in eng_facets_with_outcome:
        type_outcomes[stype].append(outcome)

    for stype, outcomes in type_outcomes.items():
        if len(outcomes) >= 3:
            successes = sum(1 for o in outcomes if o == "success")
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
    base_q = _base_session_query(db, team_id, engineer_id, start_date, end_date)
    sessions = base_q.all()

    if not sessions:
        return SkillInventoryResponse(
            engineer_profiles=[],
            team_skill_gaps=[],
            total_engineers=0,
            total_session_types=0,
            total_tools_used=0,
        )

    session_ids = [s.id for s in sessions]

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
            SessionFacets.session_id.in_(session_ids),
            SessionFacets.session_type.isnot(None),
        )
        .all()
    )
    session_to_type: dict[str, str] = {f.session_id: f.session_type for f in all_facets}

    # Get all tool usages
    all_tools = (
        db.query(ToolUsage.session_id, ToolUsage.tool_name, ToolUsage.call_count)
        .filter(ToolUsage.session_id.in_(session_ids))
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
