"""GitHub App integration: token management, API client, PR sync."""

import logging
import threading
import time
from datetime import UTC

import httpx
import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.models import (
    Engineer,
    GitRepository,
    PullRequest,
    SessionCommit,
)
from primer.common.utils import parse_github_datetime
from primer.server.services.ingest_service import find_or_create_repository

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"

# Module-level token cache (protected by lock for thread safety)
_token_cache: dict[str, object] = {"access_token": None, "expires_at": 0.0}
_token_lock = threading.Lock()


def is_configured() -> bool:
    return bool(
        settings.github_app_id
        and settings.github_app_private_key
        and settings.github_installation_id
    )


def _generate_app_jwt() -> str:
    """Generate a JWT signed with the GitHub App private key (RS256, 10-min TTL)."""
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": settings.github_app_id,
    }
    return jwt.encode(payload, settings.github_app_private_key, algorithm="RS256")


def _get_installation_token() -> str:
    """Get or refresh the GitHub App installation token (cached for 50 min)."""
    with _token_lock:
        now = time.time()
        if _token_cache["access_token"] and _token_cache["expires_at"] > now:  # type: ignore[operator]
            return _token_cache["access_token"]  # type: ignore[return-value]

        app_jwt = _generate_app_jwt()
        installation_id = settings.github_installation_id
        resp = httpx.post(
            f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        token = resp.json()["token"]
        _token_cache["access_token"] = token
        _token_cache["expires_at"] = now + 3000  # 50 minutes
        return token


def _github_headers() -> dict[str, str]:
    token = _get_installation_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def upsert_pull_request(
    db: Session, repo: GitRepository, pr_number: int, pr_data: dict
) -> PullRequest:
    """Find or create a PullRequest and update its fields from GitHub API data.

    Handles concurrent inserts via IntegrityError catch-and-retry.
    Only sets engineer_id if not already linked (avoids overwriting manual links).
    """
    state = "merged" if pr_data.get("merged_at") else pr_data.get("state", "open")

    existing = (
        db.query(PullRequest)
        .filter(
            PullRequest.repository_id == repo.id,
            PullRequest.github_pr_number == pr_number,
        )
        .first()
    )

    if existing:
        pr = existing
    else:
        try:
            with db.begin_nested():
                pr = PullRequest(repository_id=repo.id, github_pr_number=pr_number, state=state)
                db.add(pr)
        except IntegrityError:
            pr = (
                db.query(PullRequest)
                .filter(
                    PullRequest.repository_id == repo.id,
                    PullRequest.github_pr_number == pr_number,
                )
                .one()
            )

    pr.title = (pr_data.get("title") or "")[:500]
    pr.state = state
    pr.head_branch = (pr_data.get("head") or {}).get("ref")
    pr.additions = pr_data.get("additions") or 0
    pr.deletions = pr_data.get("deletions") or 0
    pr.changed_files = pr_data.get("changed_files") or 0
    pr.review_comments_count = pr_data.get("review_comments") or 0
    pr.commits_count = pr_data.get("commits") or 0
    pr.merged_at = parse_github_datetime(pr_data.get("merged_at"))
    pr.closed_at = parse_github_datetime(pr_data.get("closed_at"))
    pr.pr_created_at = parse_github_datetime(pr_data.get("created_at"))

    # Only set engineer if not already linked (avoids overwriting manual links)
    pr_author = (pr_data.get("user") or {}).get("login")
    if pr_author and not pr.engineer_id:
        eng = db.query(Engineer).filter(Engineer.github_username == pr_author).first()
        if eng:
            pr.engineer_id = eng.id

    db.flush()
    return pr


def get_repository(full_name: str) -> dict | None:
    """Fetch repository metadata from GitHub."""
    if not is_configured():
        return None
    try:
        resp = httpx.get(
            f"{GITHUB_API}/repos/{full_name}",
            headers=_github_headers(),
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError:
        logger.exception("Failed to fetch repo %s", full_name)
        return None


def list_pull_requests(full_name: str, state: str = "all", since: str | None = None) -> list[dict]:
    """List pull requests for a repository with pagination."""
    if not is_configured():
        return []
    prs: list[dict] = []
    page = 1
    try:
        while True:
            params: dict[str, str | int] = {
                "state": state,
                "per_page": 100,
                "page": page,
                "sort": "updated",
                "direction": "desc",
            }
            if since:
                params["since"] = since
            resp = httpx.get(
                f"{GITHUB_API}/repos/{full_name}/pulls",
                params=params,
                headers=_github_headers(),
                timeout=15.0,
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            prs.extend(batch)
            page += 1
            if len(batch) < 100:
                break
    except httpx.HTTPError:
        logger.exception("Failed to list PRs for %s", full_name)
    return prs


def get_pull_request(full_name: str, pr_number: int) -> dict | None:
    """Fetch full pull request details (includes additions, deletions, review_comments)."""
    if not is_configured():
        return None
    try:
        resp = httpx.get(
            f"{GITHUB_API}/repos/{full_name}/pulls/{pr_number}",
            headers=_github_headers(),
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError:
        logger.exception("Failed to fetch PR %s#%d", full_name, pr_number)
        return None


def get_pull_request_commits(full_name: str, pr_number: int) -> list[str]:
    """Get commit SHAs for a pull request."""
    if not is_configured():
        return []
    try:
        resp = httpx.get(
            f"{GITHUB_API}/repos/{full_name}/pulls/{pr_number}/commits",
            params={"per_page": 100},
            headers=_github_headers(),
            timeout=10.0,
        )
        resp.raise_for_status()
        return [c["sha"] for c in resp.json()]
    except httpx.HTTPError:
        logger.exception("Failed to get PR commits for %s#%d", full_name, pr_number)
        return []


def check_file_exists(full_name: str, path: str, ref: str | None = None) -> bool | None:
    """Check if a file or directory exists in a GitHub repository.

    Returns True if exists, False if confirmed not found (404),
    None on transient errors (rate limit, server error, network).
    """
    if not is_configured():
        return False
    try:
        params: dict[str, str] = {}
        if ref:
            params["ref"] = ref
        resp = httpx.get(
            f"{GITHUB_API}/repos/{full_name}/contents/{path}",
            params=params,
            headers=_github_headers(),
            timeout=10.0,
        )
        if resp.status_code == 200:
            return True
        if resp.status_code == 404:
            return False
        # Other status codes (rate limit, server error) are transient
        logger.warning("Unexpected status %d checking %s/%s", resp.status_code, full_name, path)
        return None
    except httpx.HTTPError:
        logger.warning("HTTP error checking %s/%s", full_name, path)
        return None


def check_ai_readiness(full_name: str, default_branch: str | None = None) -> dict | None:
    """Check a repo for CLAUDE.md, AGENTS.md, and .claude/ directory.

    Returns dict with has_claude_md, has_agents_md, has_claude_dir, ai_readiness_score.
    Scoring: CLAUDE.md = 50pts, .claude/ = 30pts, AGENTS.md = 20pts.
    Returns None if any check had a transient error (caller should not cache).
    """
    ref = default_branch or None  # let GitHub API use repo's actual default branch
    has_claude_md = check_file_exists(full_name, "CLAUDE.md", ref=ref)
    has_agents_md = check_file_exists(full_name, "AGENTS.md", ref=ref)
    has_claude_dir = check_file_exists(full_name, ".claude", ref=ref)

    # If any check had a transient error, don't return results to avoid caching bad data
    if has_claude_md is None or has_agents_md is None or has_claude_dir is None:
        return None

    score = 0.0
    if has_claude_md:
        score += 50.0
    if has_claude_dir:
        score += 30.0
    if has_agents_md:
        score += 20.0

    return {
        "has_claude_md": has_claude_md,
        "has_agents_md": has_agents_md,
        "has_claude_dir": has_claude_dir,
        "ai_readiness_score": score,
    }


def sync_repository(db: Session, full_name: str, since_days: int = 30) -> dict:
    """Sync PRs from GitHub for a repository and correlate commits."""
    from datetime import datetime, timedelta

    stats = {"prs_found": 0, "commits_correlated": 0}

    if not is_configured():
        return stats

    # Ensure repo exists locally
    repo = find_or_create_repository(db, full_name)

    # Fetch repo metadata
    gh_repo = get_repository(full_name)
    if gh_repo:
        repo.github_id = gh_repo.get("id")
        repo.default_branch = gh_repo.get("default_branch")

    # AI readiness check with 24h cooldown
    now = datetime.now(tz=UTC)
    should_check_readiness = (
        repo.ai_readiness_checked_at is None
        or (now - repo.ai_readiness_checked_at).total_seconds() > 86400
    )
    if should_check_readiness:
        readiness = check_ai_readiness(full_name, repo.default_branch)
        if readiness is not None:  # Only cache if all checks succeeded
            repo.has_claude_md = readiness["has_claude_md"]
            repo.has_agents_md = readiness["has_agents_md"]
            repo.has_claude_dir = readiness["has_claude_dir"]
            repo.ai_readiness_score = readiness["ai_readiness_score"]
            repo.ai_readiness_checked_at = now

    since = (now - timedelta(days=since_days)).isoformat()
    prs = list_pull_requests(full_name, state="all", since=since)
    stats["prs_found"] = len(prs)

    for pr_list_item in prs:
        pr_number = pr_list_item["number"]

        # Fetch full PR details (list endpoint omits additions/deletions/review_comments)
        pr_data = get_pull_request(full_name, pr_number) or pr_list_item

        pr = upsert_pull_request(db, repo, pr_number, pr_data)

        # Correlate commits
        commit_shas = get_pull_request_commits(full_name, pr_number)
        if commit_shas:
            correlated = (
                db.query(SessionCommit)
                .filter(
                    SessionCommit.commit_sha.in_(commit_shas),
                    SessionCommit.pull_request_id.is_(None),
                )
                .all()
            )
            for sc in correlated:
                sc.pull_request_id = pr.id
                stats["commits_correlated"] += 1

    db.flush()
    return stats
