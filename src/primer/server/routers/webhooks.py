"""GitHub webhook receiver."""

import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import get_db
from primer.common.models import (
    Engineer,
    GitRepository,
    PullRequest,
    SessionCommit,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


def _verify_signature(body: bytes, signature: str | None) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not settings.github_webhook_secret:
        return True  # No secret configured, skip verification
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def _parse_datetime(val: str | None):
    """Parse ISO datetime from GitHub."""
    if not val:
        return None
    from datetime import datetime

    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


@router.post("/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256")

    if not _verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("x-github-event", "")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")  # noqa: B904

    if event == "push":
        _handle_push(db, payload)
    elif event == "pull_request":
        _handle_pull_request(db, payload)

    db.commit()
    return {"status": "ok"}


def _handle_push(db: Session, payload: dict) -> None:
    """Handle push event — store commits for future correlation."""
    repo_full_name = payload.get("repository", {}).get("full_name")
    if not repo_full_name:
        return

    repo = db.query(GitRepository).filter(GitRepository.full_name == repo_full_name).first()
    if not repo:
        return  # We only track repos we already know about

    for commit in payload.get("commits", []):
        sha = commit.get("id", "")
        if not sha:
            continue
        # Check if already linked to a session
        existing = db.query(SessionCommit).filter(SessionCommit.commit_sha == sha).first()
        if existing and not existing.repository_id:
            existing.repository_id = repo.id

    db.flush()


def _handle_pull_request(db: Session, payload: dict) -> None:
    """Handle pull_request event — upsert PullRequest record."""
    action = payload.get("action", "")
    if action not in ("opened", "closed", "reopened", "synchronize", "edited"):
        return

    pr_data = payload.get("pull_request", {})
    repo_full_name = payload.get("repository", {}).get("full_name")
    if not repo_full_name or not pr_data:
        return

    repo = db.query(GitRepository).filter(GitRepository.full_name == repo_full_name).first()
    if not repo:
        repo = GitRepository(full_name=repo_full_name)
        db.add(repo)
        db.flush()

    pr_number = pr_data.get("number")
    if not pr_number:
        return

    existing = (
        db.query(PullRequest)
        .filter(
            PullRequest.repository_id == repo.id,
            PullRequest.github_pr_number == pr_number,
        )
        .first()
    )

    state = "merged" if pr_data.get("merged_at") else pr_data.get("state", "open")

    if existing:
        pr = existing
    else:
        pr = PullRequest(repository_id=repo.id, github_pr_number=pr_number, state=state)
        db.add(pr)

    pr.title = (pr_data.get("title") or "")[:500]
    pr.state = state
    pr.head_branch = (pr_data.get("head") or {}).get("ref")
    pr.additions = pr_data.get("additions", 0)
    pr.deletions = pr_data.get("deletions", 0)
    pr.changed_files = pr_data.get("changed_files", 0)
    pr.review_comments_count = pr_data.get("review_comments", 0)
    pr.commits_count = pr_data.get("commits", 0)
    pr.merged_at = _parse_datetime(pr_data.get("merged_at"))
    pr.closed_at = _parse_datetime(pr_data.get("closed_at"))
    pr.pr_created_at = _parse_datetime(pr_data.get("created_at"))

    # Link to engineer
    pr_author = (pr_data.get("user") or {}).get("login")
    if pr_author:
        eng = db.query(Engineer).filter(Engineer.github_username == pr_author).first()
        if eng:
            pr.engineer_id = eng.id

    db.flush()
