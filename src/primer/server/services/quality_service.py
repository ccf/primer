"""Quality metrics analytics service."""

import logging
from datetime import datetime

from sqlalchemy import case, distinct, func
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.models import (
    Engineer,
    GitRepository,
    PullRequest,
    SessionCommit,
    SessionFacets,
)
from primer.common.models import Session as SessionModel
from primer.common.schemas import (
    ClaudePRComparisonResponse,
    DailyCodeVolume,
    EngineerQuality,
    PRGroupMetrics,
    PRSummary,
    QualityByType,
    QualityMetricsResponse,
    QualityOverview,
)
from primer.server.services.analytics_service import base_session_query

logger = logging.getLogger(__name__)


def get_quality_metrics(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> QualityMetricsResponse:
    """Compute quality metrics from session commits and pull requests."""

    base_q = base_session_query(
        db, team_id=team_id, engineer_id=engineer_id, start_date=start_date, end_date=end_date
    )
    # Use subquery instead of materializing IDs to avoid SQLite 999-variable limit
    session_id_q = base_q.with_entities(SessionModel.id)
    total_sessions = session_id_q.count()

    # Always fetch GitHub-synced PRs (not dependent on sessions)
    github_prs = _compute_github_prs(db, team_id, engineer_id, start_date, end_date)

    if total_sessions == 0:
        # Still compute PR overview from GitHub-synced data
        pr_overview = _compute_pr_overview_from_github(
            db, team_id, engineer_id, start_date, end_date
        )
        return QualityMetricsResponse(
            overview=pr_overview,
            daily_volume=[],
            by_session_type=[],
            engineer_quality=[],
            recent_prs=github_prs,
            sessions_analyzed=0,
            github_connected=bool(settings.github_app_id),
        )

    overview = _compute_overview(db, session_id_q)
    daily_volume = _compute_daily_volume(db, session_id_q)
    by_session_type = _compute_by_session_type(db, session_id_q)
    engineer_quality = _compute_engineer_quality(db, session_id_q)
    session_prs = _compute_recent_prs(db, session_id_q)

    # Enrich overview with GitHub-synced PR stats if session-linked PRs are empty
    if overview.total_prs == 0 and github_prs:
        gh_overview = _compute_pr_overview_from_github(
            db, team_id, engineer_id, start_date, end_date
        )
        overview.total_prs = gh_overview.total_prs
        overview.pr_merge_rate = gh_overview.pr_merge_rate
        overview.avg_review_comments_per_pr = gh_overview.avg_review_comments_per_pr
        overview.avg_time_to_merge_hours = gh_overview.avg_time_to_merge_hours
        overview.total_lines_added += gh_overview.total_lines_added
        overview.total_lines_deleted += gh_overview.total_lines_deleted

    # Merge session-linked PRs with GitHub-synced PRs (dedupe by repo+number)
    seen = {(pr.repository, pr.pr_number) for pr in session_prs}
    merged_prs = list(session_prs)
    for pr in github_prs:
        if (pr.repository, pr.pr_number) not in seen:
            merged_prs.append(pr)
    merged_prs.sort(key=lambda p: p.pr_created_at or "", reverse=True)

    return QualityMetricsResponse(
        overview=overview,
        daily_volume=daily_volume,
        by_session_type=by_session_type,
        engineer_quality=engineer_quality,
        recent_prs=merged_prs[:30],
        sessions_analyzed=total_sessions,
        github_connected=bool(settings.github_app_id),
    )


def _compute_overview(db: Session, session_id_q) -> QualityOverview:
    """Compute overview quality metrics."""
    commit_stats = (
        db.query(
            func.count(distinct(SessionCommit.session_id)).label("sessions_with_commits"),
            func.count(SessionCommit.id).label("total_commits"),
            func.coalesce(func.sum(SessionCommit.lines_added), 0).label("total_lines_added"),
            func.coalesce(func.sum(SessionCommit.lines_deleted), 0).label("total_lines_deleted"),
        )
        .filter(SessionCommit.session_id.in_(session_id_q))
        .first()
    )

    sessions_with_commits = commit_stats[0] or 0
    total_commits = commit_stats[1] or 0
    total_lines_added = commit_stats[2] or 0
    total_lines_deleted = commit_stats[3] or 0

    # PR stats from commits linked to PRs
    pr_ids = (
        db.query(distinct(SessionCommit.pull_request_id))
        .filter(
            SessionCommit.session_id.in_(session_id_q),
            SessionCommit.pull_request_id.isnot(None),
        )
        .all()
    )
    pr_id_list = [pid[0] for pid in pr_ids]

    total_prs = len(pr_id_list)
    pr_merge_rate = None
    avg_review_comments = None
    avg_time_to_merge_hours = None

    if pr_id_list:
        pr_stats = (
            db.query(
                func.count(PullRequest.id).label("total"),
                func.sum(case((PullRequest.state == "merged", 1), else_=0)).label("merged"),
                func.sum(case((PullRequest.state == "closed", 1), else_=0)).label(
                    "closed_not_merged"
                ),
                func.avg(PullRequest.review_comments_count).label("avg_comments"),
            )
            .filter(PullRequest.id.in_(pr_id_list))
            .first()
        )

        merged = pr_stats[1] or 0
        closed_not_merged = pr_stats[2] or 0
        denominator = merged + closed_not_merged
        if denominator > 0:
            pr_merge_rate = merged / denominator
        avg_review_comments = float(pr_stats[3]) if pr_stats[3] is not None else None

        # Average time to merge — compute in Python for DB portability
        merge_rows = (
            db.query(PullRequest.merged_at, PullRequest.pr_created_at)
            .filter(
                PullRequest.id.in_(pr_id_list),
                PullRequest.merged_at.isnot(None),
                PullRequest.pr_created_at.isnot(None),
            )
            .all()
        )
        if merge_rows:
            total_secs = sum(
                (row.merged_at - row.pr_created_at).total_seconds() for row in merge_rows
            )
            avg_time_to_merge_hours = total_secs / len(merge_rows) / 3600

    avg_commits_per_session = (
        total_commits / sessions_with_commits if sessions_with_commits else None
    )
    avg_lines = (
        (total_lines_added + total_lines_deleted) / sessions_with_commits
        if sessions_with_commits
        else None
    )

    return QualityOverview(
        sessions_with_commits=sessions_with_commits,
        total_commits=total_commits,
        total_lines_added=total_lines_added,
        total_lines_deleted=total_lines_deleted,
        total_prs=total_prs,
        pr_merge_rate=pr_merge_rate,
        avg_commits_per_session=avg_commits_per_session,
        avg_lines_per_session=avg_lines,
        avg_review_comments_per_pr=avg_review_comments,
        avg_time_to_merge_hours=avg_time_to_merge_hours,
    )


def _compute_daily_volume(db: Session, session_id_q) -> list[DailyCodeVolume]:
    """Aggregate code volume by day."""
    date_expr = func.date(SessionCommit.committed_at)
    rows = (
        db.query(
            date_expr.label("date"),
            func.sum(SessionCommit.lines_added).label("lines_added"),
            func.sum(SessionCommit.lines_deleted).label("lines_deleted"),
            func.count(SessionCommit.id).label("commits"),
            func.count(distinct(SessionCommit.session_id)).label("sessions"),
        )
        .filter(
            SessionCommit.session_id.in_(session_id_q),
            SessionCommit.committed_at.isnot(None),
        )
        .group_by(date_expr)
        .order_by(date_expr)
        .all()
    )

    return [
        DailyCodeVolume(
            date=str(row.date),
            lines_added=row.lines_added or 0,
            lines_deleted=row.lines_deleted or 0,
            commits=row.commits or 0,
            sessions=row.sessions or 0,
        )
        for row in rows
        if row.date
    ]


def _compute_by_session_type(db: Session, session_id_q) -> list[QualityByType]:
    """Quality metrics grouped by session type."""
    session_type_expr = func.coalesce(SessionFacets.session_type, "unknown")
    rows = (
        db.query(
            session_type_expr.label("session_type"),
            func.count(distinct(SessionModel.id)).label("session_count"),
            func.count(SessionCommit.id).label("total_commits"),
            func.coalesce(func.sum(SessionCommit.lines_added), 0).label("total_lines_added"),
            func.coalesce(func.sum(SessionCommit.lines_deleted), 0).label("total_lines_deleted"),
        )
        .select_from(SessionModel)
        .outerjoin(SessionFacets, SessionFacets.session_id == SessionModel.id)
        .join(SessionCommit, SessionCommit.session_id == SessionModel.id)
        .filter(SessionModel.id.in_(session_id_q))
        .group_by(session_type_expr)
        .all()
    )

    # Batch PR counts by session type (avoids N+1)
    pr_count_rows = (
        db.query(
            session_type_expr.label("session_type"),
            func.count(distinct(SessionCommit.pull_request_id)).label("pr_count"),
        )
        .select_from(SessionCommit)
        .join(SessionModel, SessionModel.id == SessionCommit.session_id)
        .outerjoin(SessionFacets, SessionFacets.session_id == SessionModel.id)
        .filter(
            SessionModel.id.in_(session_id_q),
            SessionCommit.pull_request_id.isnot(None),
        )
        .group_by(session_type_expr)
        .all()
    )
    pr_count_map = {row.session_type: row.pr_count for row in pr_count_rows}

    results = []
    for row in rows:
        session_count = row.session_count or 1
        results.append(
            QualityByType(
                session_type=row.session_type,
                session_count=session_count,
                avg_commits=row.total_commits / session_count,
                avg_lines_added=row.total_lines_added / session_count,
                avg_lines_deleted=row.total_lines_deleted / session_count,
                pr_count=pr_count_map.get(row.session_type, 0),
                merge_rate=None,
            )
        )

    return results


def _compute_engineer_quality(db: Session, session_id_q) -> list[EngineerQuality]:
    """Per-engineer quality metrics."""
    rows = (
        db.query(
            SessionModel.engineer_id,
            Engineer.name,
            func.count(distinct(SessionModel.id)).label("sessions_with_commits"),
            func.count(SessionCommit.id).label("total_commits"),
            func.coalesce(func.sum(SessionCommit.lines_added), 0).label("total_lines_added"),
            func.coalesce(func.sum(SessionCommit.lines_deleted), 0).label("total_lines_deleted"),
        )
        .join(SessionCommit, SessionCommit.session_id == SessionModel.id)
        .join(Engineer, Engineer.id == SessionModel.engineer_id)
        .filter(SessionModel.id.in_(session_id_q))
        .group_by(SessionModel.engineer_id, Engineer.name)
        .all()
    )

    # Batch: get distinct PR IDs per engineer (avoids N+1)
    engineer_pr_rows = (
        db.query(SessionModel.engineer_id, SessionCommit.pull_request_id)
        .join(SessionCommit, SessionCommit.session_id == SessionModel.id)
        .filter(
            SessionModel.id.in_(session_id_q),
            SessionCommit.pull_request_id.isnot(None),
        )
        .distinct()
        .all()
    )
    engineer_prs: dict[str, set[str]] = {}
    all_pr_ids: set[str] = set()
    for eng_id, pr_id in engineer_pr_rows:
        engineer_prs.setdefault(eng_id, set()).add(pr_id)
        all_pr_ids.add(pr_id)

    # Batch: get PR stats for all relevant PRs at once
    pr_stats_map: dict[str, tuple[str, int]] = {}
    if all_pr_ids:
        pr_detail_rows = (
            db.query(PullRequest.id, PullRequest.state, PullRequest.review_comments_count)
            .filter(PullRequest.id.in_(list(all_pr_ids)))
            .all()
        )
        for pr in pr_detail_rows:
            pr_stats_map[pr.id] = (pr.state, pr.review_comments_count)

    results = []
    for row in rows:
        pr_id_set = engineer_prs.get(row.engineer_id, set())
        pr_count = len(pr_id_set)
        merge_rate = None
        avg_review_comments = None

        if pr_id_set:
            merged = sum(1 for pid in pr_id_set if pr_stats_map.get(pid, ("",))[0] == "merged")
            closed = sum(1 for pid in pr_id_set if pr_stats_map.get(pid, ("",))[0] == "closed")
            if merged + closed > 0:
                merge_rate = merged / (merged + closed)
            comment_counts = [pr_stats_map[pid][1] for pid in pr_id_set if pid in pr_stats_map]
            if comment_counts:
                avg_review_comments = sum(comment_counts) / len(comment_counts)

        results.append(
            EngineerQuality(
                engineer_id=row.engineer_id,
                name=row.name,
                sessions_with_commits=row.sessions_with_commits,
                total_commits=row.total_commits,
                total_lines_added=row.total_lines_added,
                total_lines_deleted=row.total_lines_deleted,
                pr_count=pr_count,
                merge_rate=merge_rate,
                avg_review_comments=avg_review_comments,
            )
        )

    return results


def _compute_recent_prs(db: Session, session_id_q) -> list[PRSummary]:
    """Recent pull requests linked to sessions."""
    # Get PRs linked to sessions via commits
    pr_ids = (
        db.query(distinct(SessionCommit.pull_request_id))
        .filter(
            SessionCommit.session_id.in_(session_id_q),
            SessionCommit.pull_request_id.isnot(None),
        )
        .all()
    )
    pr_id_list = [p[0] for p in pr_ids]

    if not pr_id_list:
        return []

    prs = (
        db.query(PullRequest, GitRepository.full_name, Engineer.name.label("author_name"))
        .join(GitRepository, GitRepository.id == PullRequest.repository_id)
        .outerjoin(Engineer, Engineer.id == PullRequest.engineer_id)
        .filter(PullRequest.id.in_(pr_id_list))
        .order_by(PullRequest.pr_created_at.desc())
        .limit(20)
        .all()
    )

    # Batch: count linked sessions per PR (avoids N+1)
    fetched_pr_ids = [pr.id for pr, _, _ in prs]
    linked_rows = (
        db.query(
            SessionCommit.pull_request_id,
            func.count(distinct(SessionCommit.session_id)).label("linked"),
        )
        .filter(
            SessionCommit.pull_request_id.in_(fetched_pr_ids),
            SessionCommit.session_id.in_(session_id_q),
        )
        .group_by(SessionCommit.pull_request_id)
        .all()
    )
    linked_map = {row.pull_request_id: row.linked for row in linked_rows}

    results = []
    for pr, repo_name, author_name in prs:
        results.append(
            PRSummary(
                repository=repo_name,
                pr_number=pr.github_pr_number,
                title=pr.title,
                state=pr.state,
                head_branch=pr.head_branch,
                additions=pr.additions,
                deletions=pr.deletions,
                review_comments_count=pr.review_comments_count,
                author=author_name,
                linked_sessions=linked_map.get(pr.id, 0),
                pr_created_at=pr.pr_created_at.isoformat() if pr.pr_created_at else None,
                merged_at=pr.merged_at.isoformat() if pr.merged_at else None,
            )
        )

    return results


def _build_pr_scope_query(
    db: Session,
    team_id: str | None,
    engineer_id: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
):
    """Build a query for GitHub-synced PRs scoped by team/engineer/date."""
    q = (
        db.query(PullRequest, GitRepository.full_name, Engineer.name.label("author_name"))
        .join(GitRepository, GitRepository.id == PullRequest.repository_id)
        .outerjoin(Engineer, Engineer.id == PullRequest.engineer_id)
    )
    if engineer_id:
        q = q.filter(PullRequest.engineer_id == engineer_id)
    elif team_id:
        q = q.filter(Engineer.team_id == team_id)
    if start_date:
        q = q.filter(PullRequest.pr_created_at >= start_date)
    if end_date:
        q = q.filter(PullRequest.pr_created_at <= end_date)
    return q


def _compute_github_prs(
    db: Session,
    team_id: str | None,
    engineer_id: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> list[PRSummary]:
    """Fetch recent PRs directly from GitHub sync data (not session-linked)."""
    rows = (
        _build_pr_scope_query(db, team_id, engineer_id, start_date, end_date)
        .order_by(PullRequest.pr_created_at.desc())
        .limit(30)
        .all()
    )

    return [
        PRSummary(
            repository=repo_name,
            pr_number=pr.github_pr_number,
            title=pr.title,
            state=pr.state,
            head_branch=pr.head_branch,
            additions=pr.additions,
            deletions=pr.deletions,
            review_comments_count=pr.review_comments_count,
            author=author_name,
            linked_sessions=0,
            pr_created_at=pr.pr_created_at.isoformat() if pr.pr_created_at else None,
            merged_at=pr.merged_at.isoformat() if pr.merged_at else None,
        )
        for pr, repo_name, author_name in rows
    ]


def _compute_pr_overview_from_github(
    db: Session,
    team_id: str | None,
    engineer_id: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> QualityOverview:
    """Compute PR overview stats directly from GitHub-synced PRs."""
    q = db.query(PullRequest).outerjoin(Engineer, Engineer.id == PullRequest.engineer_id)
    if engineer_id:
        q = q.filter(PullRequest.engineer_id == engineer_id)
    elif team_id:
        q = q.filter(Engineer.team_id == team_id)
    if start_date:
        q = q.filter(PullRequest.pr_created_at >= start_date)
    if end_date:
        q = q.filter(PullRequest.pr_created_at <= end_date)

    stats = q.with_entities(
        func.count(PullRequest.id).label("total"),
        func.sum(case((PullRequest.state == "merged", 1), else_=0)).label("merged"),
        func.sum(case((PullRequest.state == "closed", 1), else_=0)).label("closed"),
        func.coalesce(func.sum(PullRequest.additions), 0).label("additions"),
        func.coalesce(func.sum(PullRequest.deletions), 0).label("deletions"),
        func.avg(PullRequest.review_comments_count).label("avg_comments"),
    ).first()

    total_prs = stats[0] or 0
    merged = stats[1] or 0
    closed = stats[2] or 0
    pr_merge_rate = merged / (merged + closed) if (merged + closed) > 0 else None
    avg_review_comments = float(stats[5]) if stats[5] is not None else None

    # Average time to merge
    avg_time_to_merge_hours = None
    merge_rows = (
        q.with_entities(PullRequest.merged_at, PullRequest.pr_created_at)
        .filter(PullRequest.merged_at.isnot(None), PullRequest.pr_created_at.isnot(None))
        .all()
    )
    if merge_rows:
        total_secs = sum(
            (row.merged_at - row.pr_created_at).total_seconds() for row in merge_rows
        )
        avg_time_to_merge_hours = total_secs / len(merge_rows) / 3600

    return QualityOverview(
        sessions_with_commits=0,
        total_commits=0,
        total_lines_added=stats[3] or 0,
        total_lines_deleted=stats[4] or 0,
        total_prs=total_prs,
        pr_merge_rate=pr_merge_rate,
        avg_commits_per_session=None,
        avg_lines_per_session=None,
        avg_review_comments_per_pr=avg_review_comments,
        avg_time_to_merge_hours=avg_time_to_merge_hours,
    )


def get_claude_pr_comparison(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> ClaudePRComparisonResponse:
    """Compare Claude-assisted PRs vs non-Claude PRs.

    NOTE: This feature requires PR tracking models (PullRequest, SessionCommit)
    which are not yet implemented.  Until those tables exist this function
    returns empty metrics so the API contract is honoured and the frontend
    can render a "no data" state.
    """
    empty = PRGroupMetrics(
        pr_count=0,
        merge_rate=None,
        avg_review_comments=None,
        avg_time_to_merge_hours=None,
        avg_additions=None,
        avg_deletions=None,
    )
    return ClaudePRComparisonResponse(
        claude_assisted=empty,
        non_claude=empty,
        delta_review_comments=None,
        delta_merge_time_hours=None,
        delta_merge_rate=None,
        total_prs_analyzed=0,
    )
