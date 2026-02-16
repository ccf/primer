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
    DailyCodeVolume,
    EngineerQuality,
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
    session_ids = [s.id for s in base_q.all()]
    total_sessions = len(session_ids)

    if not session_ids:
        return QualityMetricsResponse(
            overview=QualityOverview(
                sessions_with_commits=0,
                total_commits=0,
                total_lines_added=0,
                total_lines_deleted=0,
                total_prs=0,
                pr_merge_rate=None,
                avg_commits_per_session=None,
                avg_lines_per_session=None,
                avg_review_comments_per_pr=None,
                avg_time_to_merge_hours=None,
            ),
            daily_volume=[],
            by_session_type=[],
            engineer_quality=[],
            recent_prs=[],
            sessions_analyzed=0,
            github_connected=bool(settings.github_app_id),
        )

    overview = _compute_overview(db, session_ids)
    daily_volume = _compute_daily_volume(db, session_ids)
    by_session_type = _compute_by_session_type(db, session_ids)
    engineer_quality = _compute_engineer_quality(db, session_ids)
    recent_prs = _compute_recent_prs(db, session_ids)

    return QualityMetricsResponse(
        overview=overview,
        daily_volume=daily_volume,
        by_session_type=by_session_type,
        engineer_quality=engineer_quality,
        recent_prs=recent_prs,
        sessions_analyzed=total_sessions,
        github_connected=bool(settings.github_app_id),
    )


def _compute_overview(db: Session, session_ids: list[str]) -> QualityOverview:
    """Compute overview quality metrics."""
    commit_stats = (
        db.query(
            func.count(distinct(SessionCommit.session_id)).label("sessions_with_commits"),
            func.count(SessionCommit.id).label("total_commits"),
            func.coalesce(func.sum(SessionCommit.lines_added), 0).label("total_lines_added"),
            func.coalesce(func.sum(SessionCommit.lines_deleted), 0).label("total_lines_deleted"),
        )
        .filter(SessionCommit.session_id.in_(session_ids))
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
            SessionCommit.session_id.in_(session_ids),
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


def _compute_daily_volume(db: Session, session_ids: list[str]) -> list[DailyCodeVolume]:
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
            SessionCommit.session_id.in_(session_ids),
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


def _compute_by_session_type(db: Session, session_ids: list[str]) -> list[QualityByType]:
    """Quality metrics grouped by session type."""
    rows = (
        db.query(
            func.coalesce(SessionFacets.session_type, "unknown").label("session_type"),
            func.count(distinct(SessionModel.id)).label("session_count"),
            func.count(SessionCommit.id).label("total_commits"),
            func.coalesce(func.sum(SessionCommit.lines_added), 0).label("total_lines_added"),
            func.coalesce(func.sum(SessionCommit.lines_deleted), 0).label("total_lines_deleted"),
        )
        .select_from(SessionModel)
        .outerjoin(SessionFacets, SessionFacets.session_id == SessionModel.id)
        .join(SessionCommit, SessionCommit.session_id == SessionModel.id)
        .filter(SessionModel.id.in_(session_ids))
        .group_by(func.coalesce(SessionFacets.session_type, "unknown"))
        .all()
    )

    results = []
    for row in rows:
        session_count = row.session_count or 1
        # Count PRs for this session type
        pr_count_q = (
            db.query(func.count(distinct(SessionCommit.pull_request_id)))
            .join(SessionModel, SessionModel.id == SessionCommit.session_id)
            .outerjoin(SessionFacets, SessionFacets.session_id == SessionModel.id)
            .filter(
                SessionModel.id.in_(session_ids),
                func.coalesce(SessionFacets.session_type, "unknown") == row.session_type,
                SessionCommit.pull_request_id.isnot(None),
            )
            .scalar()
        ) or 0

        results.append(
            QualityByType(
                session_type=row.session_type,
                session_count=session_count,
                avg_commits=row.total_commits / session_count,
                avg_lines_added=row.total_lines_added / session_count,
                avg_lines_deleted=row.total_lines_deleted / session_count,
                pr_count=pr_count_q,
                merge_rate=None,
            )
        )

    return results


def _compute_engineer_quality(db: Session, session_ids: list[str]) -> list[EngineerQuality]:
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
        .filter(SessionModel.id.in_(session_ids))
        .group_by(SessionModel.engineer_id, Engineer.name)
        .all()
    )

    results = []
    for row in rows:
        # Count PRs linked to this engineer's commits
        pr_ids = (
            db.query(distinct(SessionCommit.pull_request_id))
            .join(SessionModel, SessionModel.id == SessionCommit.session_id)
            .filter(
                SessionModel.id.in_(session_ids),
                SessionModel.engineer_id == row.engineer_id,
                SessionCommit.pull_request_id.isnot(None),
            )
            .all()
        )
        pr_id_list = [p[0] for p in pr_ids]
        pr_count = len(pr_id_list)
        merge_rate = None
        avg_review_comments = None

        if pr_id_list:
            stats = (
                db.query(
                    func.sum(case((PullRequest.state == "merged", 1), else_=0)).label("merged"),
                    func.sum(case((PullRequest.state == "closed", 1), else_=0)).label("closed"),
                    func.avg(PullRequest.review_comments_count),
                )
                .filter(PullRequest.id.in_(pr_id_list))
                .first()
            )
            merged = stats[0] or 0
            closed = stats[1] or 0
            if merged + closed > 0:
                merge_rate = merged / (merged + closed)
            avg_review_comments = float(stats[2]) if stats[2] is not None else None

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


def _compute_recent_prs(db: Session, session_ids: list[str]) -> list[PRSummary]:
    """Recent pull requests linked to sessions."""
    # Get PRs linked to sessions via commits
    pr_ids = (
        db.query(distinct(SessionCommit.pull_request_id))
        .filter(
            SessionCommit.session_id.in_(session_ids),
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

    results = []
    for pr, repo_name, author_name in prs:
        linked = (
            db.query(func.count(distinct(SessionCommit.session_id)))
            .filter(
                SessionCommit.pull_request_id == pr.id,
                SessionCommit.session_id.in_(session_ids),
            )
            .scalar()
        ) or 0

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
                linked_sessions=linked,
                pr_created_at=pr.pr_created_at.isoformat() if pr.pr_created_at else None,
                merged_at=pr.merged_at.isoformat() if pr.merged_at else None,
            )
        )

    return results
