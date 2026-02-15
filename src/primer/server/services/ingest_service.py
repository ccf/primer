import logging
import re

from sqlalchemy.orm import Session

from primer.common.models import (
    GitRepository,
    IngestEvent,
    ModelUsage,
    SessionCommit,
    SessionFacets,
    SessionMessage,
    ToolUsage,
)
from primer.common.models import (
    Session as SessionModel,
)
from primer.common.schemas import SessionFacetsPayload, SessionIngestPayload

logger = logging.getLogger(__name__)


def _parse_repo_full_name(url: str) -> str | None:
    """Extract owner/repo from a git remote URL."""
    m = re.match(r"git@[^:]+:(.+?)(?:\.git)?$", url)
    if m:
        return m.group(1)
    m = re.match(r"https?://[^/]+/(.+?)(?:\.git)?$", url)
    if m:
        return m.group(1)
    return None


def _find_or_create_repository(db: Session, full_name: str) -> GitRepository:
    """Find or create a GitRepository by full_name."""
    repo = db.query(GitRepository).filter(GitRepository.full_name == full_name).first()
    if repo:
        return repo
    repo = GitRepository(full_name=full_name)
    db.add(repo)
    db.flush()
    return repo


def upsert_session(db: Session, engineer_id: str, payload: SessionIngestPayload) -> bool:
    """Upsert a session and its related data. Returns True if newly created."""
    existing = db.query(SessionModel).filter(SessionModel.id == payload.session_id).first()
    created = existing is None

    if existing:
        session = existing
    else:
        session = SessionModel(id=payload.session_id, engineer_id=engineer_id)
        db.add(session)

    # Update scalar fields
    for field in [
        "project_path",
        "project_name",
        "git_branch",
        "claude_version",
        "permission_mode",
        "end_reason",
        "started_at",
        "ended_at",
        "duration_seconds",
        "message_count",
        "user_message_count",
        "assistant_message_count",
        "tool_call_count",
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_creation_tokens",
        "primary_model",
        "summary",
    ]:
        value = getattr(payload, field, None)
        if value is not None:
            setattr(session, field, value)

    # Truncate first_prompt
    if payload.first_prompt:
        session.first_prompt = payload.first_prompt[:500]

    # Repository linking
    if payload.git_remote_url:
        full_name = _parse_repo_full_name(payload.git_remote_url)
        if full_name:
            repo = _find_or_create_repository(db, full_name)
            session.repository_id = repo.id

    # Tool usages — replace all
    if payload.tool_usages:
        db.query(ToolUsage).filter(ToolUsage.session_id == session.id).delete()
        for tu in payload.tool_usages:
            db.add(
                ToolUsage(session_id=session.id, tool_name=tu.tool_name, call_count=tu.call_count)
            )

    # Model usages — replace all
    if payload.model_usages:
        db.query(ModelUsage).filter(ModelUsage.session_id == session.id).delete()
        for mu in payload.model_usages:
            db.add(
                ModelUsage(
                    session_id=session.id,
                    model_name=mu.model_name,
                    input_tokens=mu.input_tokens,
                    output_tokens=mu.output_tokens,
                    cache_read_tokens=mu.cache_read_tokens,
                    cache_creation_tokens=mu.cache_creation_tokens,
                )
            )

    # Commits — replace all
    if payload.commits:
        db.query(SessionCommit).filter(SessionCommit.session_id == session.id).delete()
        for c in payload.commits:
            db.add(
                SessionCommit(
                    session_id=session.id,
                    repository_id=session.repository_id,
                    commit_sha=c.sha,
                    commit_message=c.message,
                    author_name=c.author_name,
                    author_email=c.author_email,
                    committed_at=c.committed_at,
                    files_changed=c.files_changed,
                    lines_added=c.lines_added,
                    lines_deleted=c.lines_deleted,
                )
            )

    # Messages
    if payload.messages:
        db.query(SessionMessage).filter(SessionMessage.session_id == session.id).delete()
        for msg in payload.messages:
            db.add(SessionMessage(session_id=session.id, **msg.model_dump()))

    # Facets
    if payload.facets:
        upsert_facets(db, session.id, payload.facets)
        session.has_facets = True

    db.flush()
    return created


def upsert_facets(db: Session, session_id: str, facets: SessionFacetsPayload) -> None:
    """Upsert facets for a session."""
    existing = db.query(SessionFacets).filter(SessionFacets.session_id == session_id).first()
    if existing:
        record = existing
    else:
        record = SessionFacets(session_id=session_id)
        db.add(record)

    for field in [
        "underlying_goal",
        "goal_categories",
        "outcome",
        "session_type",
        "primary_success",
        "claude_helpfulness",
        "brief_summary",
        "user_satisfaction_counts",
        "friction_counts",
        "friction_detail",
    ]:
        value = getattr(facets, field, None)
        if value is not None:
            setattr(record, field, value)

    db.flush()


def log_ingest_event(
    db: Session,
    engineer_id: str,
    event_type: str,
    session_id: str | None,
    payload_size: int | None,
    status: str,
    error_message: str | None = None,
) -> None:
    db.add(
        IngestEvent(
            engineer_id=engineer_id,
            event_type=event_type,
            session_id=session_id,
            payload_size_bytes=payload_size,
            status=status,
            error_message=error_message,
        )
    )
    db.flush()
