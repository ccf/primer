import logging
from collections import Counter
from datetime import datetime

from sqlalchemy.orm import Session

from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.common.models import Engineer, ModelUsage, SessionFacets, ToolUsage
from primer.common.models import Session as SessionModel
from primer.common.pricing import estimate_cost
from primer.common.schemas import (
    EngineerProfileResponse,
    ToolRecommendation,
    WeeklyMetricPoint,
)
from primer.server.services.analytics_service import (
    _build_overview,
    get_friction_report,
    get_productivity_metrics,
    get_tool_rankings,
)
from primer.server.services.effectiveness_service import (
    build_effectiveness_score,
    get_peer_cost_per_success_benchmark,
)
from primer.server.services.insights_service import (
    get_config_optimization,
    get_learning_paths,
    get_skill_inventory,
)
from primer.server.services.workflow_playbook_service import get_workflow_playbooks

logger = logging.getLogger(__name__)


_RECOMMENDATION_PRIORITY_SCORE = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


def _build_tool_recommendations(
    db: Session,
    engineer_id: str,
    learning_paths: list,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 6,
) -> list[ToolRecommendation]:
    if not learning_paths:
        return []

    session_query = db.query(SessionModel.id, SessionModel.project_name).filter(
        SessionModel.engineer_id == engineer_id
    )
    if start_date:
        session_query = session_query.filter(SessionModel.started_at >= start_date)
    if end_date:
        session_query = session_query.filter(SessionModel.started_at <= end_date)

    session_rows = session_query.all()
    session_ids = [row.id for row in session_rows]
    project_counts = Counter(row.project_name for row in session_rows if row.project_name)

    engineer_tools: set[str] = set()
    if session_ids:
        engineer_tools = {
            tool_name
            for (tool_name,) in (
                db.query(ToolUsage.tool_name)
                .filter(ToolUsage.session_id.in_(session_ids))
                .distinct()
                .all()
            )
        }

    buckets: dict[str, dict[str, object]] = {}
    for path in learning_paths:
        for recommendation in path.recommendations:
            priority_score = _RECOMMENDATION_PRIORITY_SCORE.get(recommendation.priority, 1)
            for exemplar in recommendation.exemplars:
                project_match = bool(
                    exemplar.project_name and exemplar.project_name in project_counts
                )
                for tool_name in exemplar.tools_used:
                    if tool_name in engineer_tools:
                        continue

                    bucket = buckets.setdefault(
                        tool_name,
                        {
                            "score": 0,
                            "priority_score": 0,
                            "supporting_exemplar_ids": set(),
                            "project_context_match_count": 0,
                            "related_skill_areas": set(),
                            "related_categories": set(),
                            "matching_projects": Counter(),
                            "best_exemplar": None,
                            "best_rank": None,
                        },
                    )
                    bucket["score"] = (
                        int(bucket["score"]) + (priority_score * 2) + int(project_match)
                    )
                    bucket["priority_score"] = max(int(bucket["priority_score"]), priority_score)
                    supporting_exemplar_ids = bucket["supporting_exemplar_ids"]
                    assert isinstance(supporting_exemplar_ids, set)
                    supporting_exemplar_ids.add(exemplar.session_id)
                    if project_match:
                        bucket["project_context_match_count"] = (
                            int(bucket["project_context_match_count"]) + 1
                        )

                    related_skill_areas = bucket["related_skill_areas"]
                    assert isinstance(related_skill_areas, set)
                    related_skill_areas.add(recommendation.skill_area)

                    related_categories = bucket["related_categories"]
                    assert isinstance(related_categories, set)
                    related_categories.add(recommendation.category)

                    matching_projects = bucket["matching_projects"]
                    assert isinstance(matching_projects, Counter)
                    if exemplar.project_name:
                        matching_projects[exemplar.project_name] += 1

                    exemplar_rank = (
                        int(project_match),
                        priority_score,
                        -(
                            exemplar.estimated_cost
                            if exemplar.estimated_cost is not None
                            else float("inf")
                        ),
                        -(exemplar.duration_seconds or float("inf")),
                    )
                    best_rank = bucket["best_rank"]
                    if best_rank is None or exemplar_rank > best_rank:
                        bucket["best_rank"] = exemplar_rank
                        bucket["best_exemplar"] = exemplar

    recommendations: list[ToolRecommendation] = []
    for tool_name, bucket in buckets.items():
        related_skill_areas = sorted(bucket["related_skill_areas"])
        related_categories = sorted(bucket["related_categories"])
        matching_projects_counter = bucket["matching_projects"]
        assert isinstance(matching_projects_counter, Counter)
        matching_projects = [name for name, _count in matching_projects_counter.most_common(3)]
        exemplar = bucket["best_exemplar"]
        assert exemplar is None or hasattr(exemplar, "session_id")

        context_phrase = ", ".join(area.replace("_", " ") for area in related_skill_areas[:2])
        if len(related_skill_areas) > 2:
            context_phrase = f"{context_phrase}, and similar work"

        project_phrase = f" on {matching_projects[0]}" if matching_projects else ""

        if context_phrase:
            description = (
                f"Peers repeatedly use {tool_name} in successful {context_phrase} workflows"
                f"{project_phrase}."
            )
        else:
            description = f"Peers repeatedly use {tool_name} in similar successful workflows."

        if exemplar is not None:
            description = (
                f"{description} Start with {exemplar.title} from {exemplar.engineer_name}."
            )

        priority = next(
            label
            for label, score in _RECOMMENDATION_PRIORITY_SCORE.items()
            if score == int(bucket["priority_score"])
        )

        recommendations.append(
            ToolRecommendation(
                tool_name=tool_name,
                title=f"Try {tool_name}",
                description=description,
                priority=priority,
                related_skill_areas=related_skill_areas[:4],
                related_categories=related_categories[:3],
                matching_projects=matching_projects,
                supporting_exemplar_count=len(bucket["supporting_exemplar_ids"]),
                project_context_match_count=int(bucket["project_context_match_count"]),
                exemplar=exemplar,
            )
        )

    recommendations.sort(
        key=lambda recommendation: (
            -_RECOMMENDATION_PRIORITY_SCORE.get(recommendation.priority, 0),
            -recommendation.project_context_match_count,
            -recommendation.supporting_exemplar_count,
            recommendation.tool_name,
        )
    )
    return recommendations[:limit]


def _get_weekly_trajectory(
    db: Session,
    engineer_id: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[WeeklyMetricPoint]:
    """Group sessions by ISO week, compute per-week metrics."""
    q = db.query(SessionModel).filter(
        SessionModel.engineer_id == engineer_id,
        SessionModel.started_at.isnot(None),
    )
    if start_date:
        q = q.filter(SessionModel.started_at >= start_date)
    if end_date:
        q = q.filter(SessionModel.started_at <= end_date)

    sessions = q.all()
    if not sessions:
        return []

    session_ids = [s.id for s in sessions]

    # Facets for outcomes
    facets = (
        db.query(SessionFacets.session_id, SessionFacets.outcome)
        .filter(SessionFacets.session_id.in_(session_ids))
        .all()
    )
    outcome_map = {}
    for facet in facets:
        normalized_outcome = canonical_outcome(facet.outcome)
        if normalized_outcome is not None:
            outcome_map[facet.session_id] = normalized_outcome

    # Tool usages for diversity
    tool_usages = (
        db.query(ToolUsage.session_id, ToolUsage.tool_name)
        .filter(ToolUsage.session_id.in_(session_ids))
        .all()
    )
    session_tools: dict[str, set[str]] = {}
    for tu in tool_usages:
        session_tools.setdefault(tu.session_id, set()).add(tu.tool_name)

    # Model usages for cost
    model_usages = (
        db.query(
            ModelUsage.session_id,
            ModelUsage.model_name,
            ModelUsage.input_tokens,
            ModelUsage.output_tokens,
            ModelUsage.cache_read_tokens,
            ModelUsage.cache_creation_tokens,
        )
        .filter(ModelUsage.session_id.in_(session_ids))
        .all()
    )
    session_costs: dict[str, float] = {}
    for mu in model_usages:
        cost = estimate_cost(
            mu.model_name,
            mu.input_tokens or 0,
            mu.output_tokens or 0,
            mu.cache_read_tokens or 0,
            mu.cache_creation_tokens or 0,
        )
        session_costs[mu.session_id] = session_costs.get(mu.session_id, 0.0) + cost

    # Group by ISO week
    weekly: dict[str, list] = {}
    for s in sessions:
        week_key = s.started_at.strftime("%G-W%V")
        weekly.setdefault(week_key, []).append(s)

    points: list[WeeklyMetricPoint] = []
    for week_key in sorted(weekly.keys()):
        week_sessions = weekly[week_key]
        count = len(week_sessions)

        # Success rate
        outcomes = [outcome_map.get(s.id) for s in week_sessions if outcome_map.get(s.id)]
        sr = (
            sum(1 for outcome in outcomes if is_success_outcome(outcome)) / len(outcomes)
            if outcomes
            else None
        )

        # Avg duration
        durations = [s.duration_seconds for s in week_sessions if s.duration_seconds is not None]
        avg_dur = sum(durations) / len(durations) if durations else None

        # Tool diversity
        all_tools: set[str] = set()
        for s in week_sessions:
            all_tools.update(session_tools.get(s.id, set()))

        # Cost
        total_cost = sum(session_costs.get(s.id, 0.0) for s in week_sessions)

        points.append(
            WeeklyMetricPoint(
                week=week_key,
                success_rate=round(sr, 3) if sr is not None else None,
                avg_duration=round(avg_dur, 1) if avg_dur is not None else None,
                tool_diversity=len(all_tools),
                estimated_cost=round(total_cost, 4),
                session_count=count,
            )
        )

    return points


def get_engineer_profile(
    db: Session,
    engineer_id: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> EngineerProfileResponse | None:
    """Build a comprehensive profile for a single engineer."""
    engineer = db.query(Engineer).filter(Engineer.id == engineer_id).first()
    if not engineer:
        return None

    team_name = None
    if engineer.team_id:
        from primer.common.models import Team

        team = db.query(Team).filter(Team.id == engineer.team_id).first()
        team_name = team.name if team else None

    # Overview stats scoped to this engineer
    overview = _build_overview(
        db, engineer_id=engineer_id, start_date=start_date, end_date=end_date
    )

    # Weekly trajectory
    trajectory = _get_weekly_trajectory(db, engineer_id, start_date, end_date)

    # Friction report
    friction = get_friction_report(
        db, engineer_id=engineer_id, start_date=start_date, end_date=end_date
    )

    # Config suggestions
    config = get_config_optimization(
        db, engineer_id=engineer_id, start_date=start_date, end_date=end_date
    )

    # Skill inventory
    skills = get_skill_inventory(
        db, engineer_id=engineer_id, start_date=start_date, end_date=end_date
    )

    # Learning paths — use team scope so adoption baselines are team-wide
    learning = get_learning_paths(
        db, team_id=engineer.team_id, start_date=start_date, end_date=end_date
    )
    # Extract this engineer's learning path
    eng_paths = [p for p in learning.engineer_paths if p.engineer_id == engineer_id]

    # Quality data from PR/commit tracking
    quality: dict = {}
    quality_metrics = None
    try:
        from primer.server.services.quality_service import get_quality_metrics

        quality_metrics = get_quality_metrics(
            db, engineer_id=engineer_id, start_date=start_date, end_date=end_date
        )
        ov = quality_metrics.overview
        if ov.total_commits > 0 or ov.total_prs > 0:
            merge_rate = f"{ov.pr_merge_rate * 100:.0f}%" if ov.pr_merge_rate is not None else None
            merge_time = (
                f"{ov.avg_time_to_merge_hours:.1f}h"
                if ov.avg_time_to_merge_hours is not None
                else None
            )
            quality = {
                "total_commits": ov.total_commits,
                "lines_added": f"+{ov.total_lines_added:,}",
                "lines_deleted": f"-{ov.total_lines_deleted:,}",
                "pull_requests": ov.total_prs,
                "merge_rate": merge_rate,
                "avg_time_to_merge": merge_time,
            }
            if quality_metrics.findings_overview:
                quality["findings_overview"] = quality_metrics.findings_overview.model_dump()
        elif quality_metrics.github_connected:
            quality = {"github_connected": True, "no_data_yet": True}
        if quality_metrics.findings_overview and "findings_overview" not in quality:
            quality["findings_overview"] = quality_metrics.findings_overview.model_dump()
    except Exception:
        logger.exception("Failed to compute quality data for engineer %s", engineer_id)
        quality = {}

    productivity = get_productivity_metrics(
        db, engineer_id=engineer_id, start_date=start_date, end_date=end_date
    )

    # Tool rankings
    tool_rankings = get_tool_rankings(
        db, engineer_id=engineer_id, limit=10, start_date=start_date, end_date=end_date
    )

    workflow_playbooks = get_workflow_playbooks(
        db,
        engineer_id,
        team_id=engineer.team_id,
        start_date=start_date,
        end_date=end_date,
    )

    # Distinct project names
    project_rows = (
        db.query(SessionModel.project_name)
        .filter(
            SessionModel.engineer_id == engineer_id,
            SessionModel.project_name.isnot(None),
        )
        .distinct()
        .all()
    )
    projects = [r[0] for r in project_rows if r[0]]
    tool_recommendations = _build_tool_recommendations(
        db,
        engineer_id,
        eng_paths,
        start_date=start_date,
        end_date=end_date,
    )

    # Leverage score from maturity analytics
    leverage_score: float | None = None
    try:
        from primer.server.services.maturity_service import get_maturity_analytics

        maturity = get_maturity_analytics(
            db, engineer_id=engineer_id, start_date=start_date, end_date=end_date
        )
        for ep in maturity.engineer_profiles:
            if ep.engineer_id == engineer_id:
                leverage_score = ep.leverage_score
                break
    except Exception:
        leverage_score = None

    effectiveness = build_effectiveness_score(
        success_rate=overview.success_rate,
        cost_per_successful_outcome=productivity.cost_per_successful_outcome,
        benchmark_cost_per_successful_outcome=get_peer_cost_per_success_benchmark(
            db,
            group_by="engineer_id",
            target_value=engineer_id,
            team_id=engineer.team_id,
            start_date=start_date,
            end_date=end_date,
        ),
        pr_merge_rate=quality_metrics.overview.pr_merge_rate if quality_metrics else None,
        findings_fix_rate=(
            quality_metrics.findings_overview.fix_rate
            if quality_metrics and quality_metrics.findings_overview
            else None
        ),
        total_sessions=overview.total_sessions,
        sessions_with_commits=(
            quality_metrics.overview.sessions_with_commits if quality_metrics else 0
        ),
    )

    return EngineerProfileResponse(
        engineer_id=engineer.id,
        name=engineer.name,
        email=engineer.email,
        display_name=engineer.display_name,
        team_id=engineer.team_id,
        team_name=team_name,
        avatar_url=engineer.avatar_url,
        github_username=engineer.github_username,
        created_at=engineer.created_at.isoformat() if engineer.created_at else "",
        overview=overview,
        weekly_trajectory=trajectory,
        friction=friction,
        config_suggestions=config.suggestions,
        strengths=skills,
        learning_paths=eng_paths,
        tool_recommendations=tool_recommendations,
        quality=quality,
        leverage_score=leverage_score,
        effectiveness=effectiveness,
        projects=projects,
        tool_rankings=tool_rankings,
        workflow_playbooks=workflow_playbooks,
    )
