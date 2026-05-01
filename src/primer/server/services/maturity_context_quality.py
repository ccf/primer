"""Project readiness and context quality helpers for maturity analytics."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from primer.common.models import GitRepository, SessionFacets
from primer.common.models import Session as SessionModel
from primer.common.schemas import ContextQualityEntry, ProjectReadinessEntry
from primer.server.services.maturity_harness_fingerprints import context_signal_count


def build_project_readiness_and_context_quality(
    *,
    db: Session,
    session_id_subq: Any,
    model_rows: list[Any],
    per_session: dict[str, dict[str, int]],
    sessions_analyzed: int,
) -> tuple[list[ProjectReadinessEntry], list[ContextQualityEntry]]:
    """Build repository readiness and context quality rows for scoped sessions."""
    project_readiness: list[ProjectReadinessEntry] = []
    context_quality: list[ContextQualityEntry] = []
    if sessions_analyzed <= 0:
        return project_readiness, context_quality

    repo_context_buckets = _build_repo_context_buckets(
        db=db,
        session_id_subq=session_id_subq,
        model_rows=model_rows,
        per_session=per_session,
    )
    if not repo_context_buckets:
        return project_readiness, context_quality

    repos = (
        db.query(GitRepository)
        .filter(
            GitRepository.id.in_(list(repo_context_buckets.keys())),
        )
        .all()
    )
    repos_by_id = {repo.id: repo for repo in repos}
    for repo in repos:
        if repo.ai_readiness_score is not None:
            project_readiness.append(
                ProjectReadinessEntry(
                    repository=repo.full_name,
                    has_claude_md=repo.has_claude_md or False,
                    has_agents_md=repo.has_agents_md or False,
                    has_claude_dir=repo.has_claude_dir or False,
                    ai_readiness_score=repo.ai_readiness_score or 0.0,
                    session_count=len(repo_context_buckets[repo.id]["sessions"]),
                )
            )

    for repository_id, bucket in repo_context_buckets.items():
        repo = repos_by_id.get(repository_id)
        if repo is None:
            continue
        context_quality.append(_build_context_quality_entry(repo, bucket))

    project_readiness.sort(key=lambda p: p.ai_readiness_score, reverse=True)
    context_quality.sort(key=lambda row: (-row.context_quality_score, -row.session_count))
    return project_readiness, context_quality


def _build_repo_context_buckets(
    *,
    db: Session,
    session_id_subq: Any,
    model_rows: list[Any],
    per_session: dict[str, dict[str, int]],
) -> dict[str, dict[str, Any]]:
    repo_session_rows = (
        db.query(
            SessionModel.id,
            SessionModel.repository_id,
            SessionModel.input_tokens,
            SessionModel.cache_read_tokens,
            SessionModel.source_metadata,
        )
        .filter(
            SessionModel.id.in_(db.query(session_id_subq.c.id)),
            SessionModel.repository_id.isnot(None),
        )
        .all()
    )
    facet_session_ids = {
        row.session_id
        for row in (
            db.query(SessionFacets.session_id)
            .filter(SessionFacets.session_id.in_(db.query(session_id_subq.c.id)))
            .all()
        )
    }
    model_session_ids = {session_id for session_id, *_rest in model_rows}
    repo_context_buckets: dict[str, dict[str, Any]] = {}
    for (
        session_id,
        repository_id,
        input_tokens,
        cache_read_tokens,
        source_metadata,
    ) in repo_session_rows:
        if repository_id is None:
            continue
        bucket = repo_context_buckets.setdefault(
            repository_id,
            {
                "sessions": set(),
                "input_tokens": 0,
                "cache_read_tokens": 0,
                "tool_sessions": set(),
                "model_sessions": set(),
                "facet_sessions": set(),
                "context_usage_sessions": set(),
            },
        )
        bucket["sessions"].add(session_id)
        bucket["input_tokens"] += input_tokens or 0
        bucket["cache_read_tokens"] += cache_read_tokens or 0
        if per_session.get(session_id):
            bucket["tool_sessions"].add(session_id)
        if session_id in model_session_ids:
            bucket["model_sessions"].add(session_id)
        if session_id in facet_session_ids:
            bucket["facet_sessions"].add(session_id)
        if context_signal_count(source_metadata) > 0:
            bucket["context_usage_sessions"].add(session_id)
    return repo_context_buckets


def _build_context_quality_entry(
    repo: GitRepository,
    bucket: dict[str, Any],
) -> ContextQualityEntry:
    session_count = len(bucket["sessions"])
    input_tokens = bucket["input_tokens"]
    cache_read_tokens = bucket["cache_read_tokens"]
    token_denominator = input_tokens + cache_read_tokens
    cache_hit_rate = (
        round(cache_read_tokens / token_denominator, 3) if token_denominator > 0 else None
    )
    avg_input_tokens = (
        round(input_tokens / session_count, 1)
        if session_count > 0 and token_denominator > 0
        else None
    )

    guide_coverage_score = _guide_coverage_score(repo)
    guide_freshness_score = _guide_freshness_score(repo.ai_readiness_checked_at)
    context_usage_coverage_pct = _coverage_pct(
        len(bucket["context_usage_sessions"]),
        session_count,
    )
    tool_coverage_pct = _coverage_pct(len(bucket["tool_sessions"]), session_count)
    model_coverage_pct = _coverage_pct(len(bucket["model_sessions"]), session_count)
    facet_coverage_pct = _coverage_pct(len(bucket["facet_sessions"]), session_count)
    sensor_coverage_score = round(
        (context_usage_coverage_pct + tool_coverage_pct + model_coverage_pct + facet_coverage_pct)
        / 4,
        1,
    )
    cache_score = min((cache_hit_rate or 0.0) / 0.5, 1.0)
    token_efficiency_score = round(
        ((cache_score * 0.6) + (_prompt_efficiency_score(avg_input_tokens) * 0.4)) * 100,
        1,
    )
    context_quality_score = round(
        (guide_coverage_score * 0.30)
        + (guide_freshness_score * 0.15)
        + (token_efficiency_score * 0.25)
        + (sensor_coverage_score * 0.30),
        1,
    )

    return ContextQualityEntry(
        repository=repo.full_name,
        session_count=session_count,
        context_quality_score=context_quality_score,
        guide_coverage_score=round(guide_coverage_score, 1),
        guide_freshness_score=guide_freshness_score,
        token_efficiency_score=token_efficiency_score,
        sensor_coverage_score=sensor_coverage_score,
        cache_hit_rate=cache_hit_rate,
        avg_input_tokens=avg_input_tokens,
        context_usage_coverage_pct=context_usage_coverage_pct,
        tool_coverage_pct=tool_coverage_pct,
        model_coverage_pct=model_coverage_pct,
        facet_coverage_pct=facet_coverage_pct,
        has_claude_md=repo.has_claude_md or False,
        has_agents_md=repo.has_agents_md or False,
        readiness_checked_at=repo.ai_readiness_checked_at,
        top_gaps=_context_quality_gaps(
            repo=repo,
            guide_freshness_score=guide_freshness_score,
            cache_hit_rate=cache_hit_rate,
            avg_input_tokens=avg_input_tokens,
            context_usage_coverage_pct=context_usage_coverage_pct,
            tool_coverage_pct=tool_coverage_pct,
            model_coverage_pct=model_coverage_pct,
            facet_coverage_pct=facet_coverage_pct,
        )[:4],
    )


def _guide_coverage_score(repo: GitRepository) -> float:
    if repo.ai_readiness_score is not None:
        return repo.ai_readiness_score
    return (
        (50.0 if repo.has_claude_md else 0.0)
        + (20.0 if repo.has_agents_md else 0.0)
        + (30.0 if repo.has_claude_dir else 0.0)
    )


def _coverage_pct(count: int, total: int) -> float:
    return round((count / total) * 100, 1) if total > 0 else 0.0


def _guide_freshness_score(checked_at: datetime | None) -> float:
    if checked_at is None:
        return 0.0
    now = datetime.now(tz=checked_at.tzinfo) if checked_at.tzinfo else datetime.now()
    age_days = max((now - checked_at).days, 0)
    if age_days <= 14:
        return 100.0
    if age_days <= 30:
        return 80.0
    if age_days <= 90:
        return 50.0
    return 25.0


def _prompt_efficiency_score(avg_input_tokens: float | None) -> float:
    if avg_input_tokens is None:
        return 0.0
    if avg_input_tokens <= 20_000:
        return 1.0
    if avg_input_tokens <= 50_000:
        return 0.8
    if avg_input_tokens <= 100_000:
        return 0.5
    return 0.25


def _context_quality_gaps(
    *,
    repo: GitRepository,
    guide_freshness_score: float,
    cache_hit_rate: float | None,
    avg_input_tokens: float | None,
    context_usage_coverage_pct: float,
    tool_coverage_pct: float,
    model_coverage_pct: float,
    facet_coverage_pct: float,
) -> list[str]:
    gaps: list[str] = []
    if not repo.has_claude_md:
        gaps.append("Add CLAUDE.md")
    if not repo.has_agents_md:
        gaps.append("Add AGENTS.md")
    if guide_freshness_score < 75:
        gaps.append("Refresh guidance scan")
    if cache_hit_rate is None:
        gaps.append("Add token/cache telemetry")
    elif cache_hit_rate < 0.25:
        gaps.append("Improve cache reuse")
    if avg_input_tokens is not None and avg_input_tokens > 50_000:
        gaps.append("Trim prompt/context payloads")
    if context_usage_coverage_pct < 50:
        gaps.append("Increase context telemetry coverage")
    if tool_coverage_pct < 90:
        gaps.append("Complete tool telemetry")
    if model_coverage_pct < 90:
        gaps.append("Complete model telemetry")
    if facet_coverage_pct < 90:
        gaps.append("Complete outcome facets")
    return gaps
