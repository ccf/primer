from datetime import datetime

from sqlalchemy.orm import Session

from primer.common.models import Engineer, ModelUsage, SessionFacets, ToolUsage
from primer.common.models import Session as SessionModel
from primer.common.pricing import estimate_cost
from primer.common.schemas import (
    EngineerProfileResponse,
    WeeklyMetricPoint,
)
from primer.server.services.analytics_service import (
    _build_overview,
    get_friction_report,
)
from primer.server.services.insights_service import (
    get_config_optimization,
    get_learning_paths,
    get_skill_inventory,
)


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
    outcome_map = {f.session_id: f.outcome for f in facets}

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
        sr = sum(1 for o in outcomes if o == "success") / len(outcomes) if outcomes else None

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

    # Quality placeholder (no quality_service models yet)
    quality: dict = {}

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
        quality=quality,
        leverage_score=leverage_score,
        projects=projects,
    )
