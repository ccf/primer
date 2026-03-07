"""GitHub webhook receiver."""

import hashlib
import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import SessionLocal, get_db
from primer.common.models import (
    GitRepository,
    SessionCommit,
)
from primer.server.services.github_service import (
    get_pull_request_comments,
    upsert_pull_request,
)
from primer.server.services.ingest_service import find_or_create_repository
from primer.server.services.review_finding_service import parse_comments, upsert_findings

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


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256")

    if not _verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("x-github-event", "")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")  # noqa: B904

    findings_task_args = None
    if event == "push":
        _handle_push(db, payload)
    elif event == "pull_request":
        pr_id, repo_full_name, pr_number = _handle_pull_request(db, payload)
        if pr_id:
            findings_task_args = (repo_full_name, pr_number, pr_id)

    db.commit()

    # Schedule findings sync only after successful commit
    if findings_task_args:
        background_tasks.add_task(_sync_findings_background, *findings_task_args)

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
        # Update all session commits with matching SHA (same SHA can exist in multiple sessions)
        matches = db.query(SessionCommit).filter(SessionCommit.commit_sha == sha).all()
        for sc in matches:
            if not sc.repository_id:
                sc.repository_id = repo.id

    db.flush()


def _handle_pull_request(db: Session, payload: dict) -> tuple[str | None, str | None, int | None]:
    """Handle pull_request event — upsert PullRequest record.

    Returns (pr_id, repo_full_name, pr_number) for background findings sync,
    or (None, None, None) if the event was skipped.
    """
    action = payload.get("action", "")
    if action not in ("opened", "closed", "reopened", "synchronize", "edited"):
        return None, None, None

    pr_data = payload.get("pull_request", {})
    repo_full_name = payload.get("repository", {}).get("full_name")
    if not repo_full_name or not pr_data:
        return None, None, None

    repo = find_or_create_repository(db, repo_full_name)

    pr_number = pr_data.get("number")
    if not pr_number:
        return None, None, None

    pr = upsert_pull_request(db, repo, pr_number, pr_data)
    return pr.id, repo_full_name, pr_number


def _sync_findings_background(repo_full_name: str, pr_number: int, pr_id: str) -> None:
    """Sync review findings in a background task (non-blocking)."""
    try:
        comments = get_pull_request_comments(repo_full_name, pr_number)
        if not comments:
            return
        findings = parse_comments(comments, pr_id)
        if not findings:
            return
        db = SessionLocal()
        try:
            upsert_findings(db, findings)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to sync findings for %s#%d", repo_full_name, pr_number)
