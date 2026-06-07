"""Memory store service layer: scopes, sketches, dedup, flood control.

Plan 2a of the hive-mind memory spec
(docs/superpowers/specs/2026-05-18-hive-mind-memory-design.md §4-§5).
The write path persists quarantined `sketch` entries only; promotion to
`active` is the consolidation engine's job (Plan 2b).
"""

import hashlib
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.models import (
    GitRepository,
    MemoryEntry,
    MemoryEvent,
    MemoryEvidence,
    MemoryScope,
)

logger = logging.getLogger(__name__)

MEMORY_KINDS = ("project_fact", "anti_pattern", "tool_pointer", "harness_config", "procedure")

# Statuses that block re-proposal of identical content (spec §7: only
# `retired` reopens the door, and it does so via manual un-retire).
_DEDUP_BLOCKING_STATUSES = ("sketch", "active", "validated", "decaying", "rejected")


def memory_capture_active() -> bool:
    """Memory capture is gated on the redaction pipeline (spec §16 #1).

    Sketches persist transcript-derived text, so no sketch is ever written
    while redaction is disabled — there is no unredacted capture mode.
    """
    return settings.memory_enabled and settings.redaction_enabled


def canonical_content_hash(body: str) -> str:
    """sha256 over whitespace-normalized, lowercased body text."""
    normalized = " ".join(body.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def get_or_create_project_scope(db: Session, repository_id: str) -> MemoryScope:
    """Every repository gets exactly one project scope (spec §4)."""
    scope = db.query(MemoryScope).filter(MemoryScope.repository_id == repository_id).first()
    if scope:
        return scope
    repo = db.query(GitRepository).filter(GitRepository.id == repository_id).one()
    try:
        with db.begin_nested():
            scope = MemoryScope(kind="project", name=repo.full_name, repository_id=repository_id)
            db.add(scope)
        # Cold start (spec §5): the first time a project scope exists, queue a
        # one-time backfill over its history so memory is useful in week one.
        if memory_capture_active():
            from primer.server.services.background_job_service import (
                JOB_TYPE_MEMORY_BACKFILL,
                enqueue_background_job,
            )

            enqueue_background_job(
                db,
                job_type=JOB_TYPE_MEMORY_BACKFILL,
                payload={"repository_id": repository_id},
            )
        return scope
    except IntegrityError:
        return db.query(MemoryScope).filter(MemoryScope.repository_id == repository_id).one()


def create_sketch(
    db: Session,
    *,
    scope: MemoryScope,
    card: dict,
    origin: str,
    engineer_id: str | None,
    session_id: str | None,
    citation: dict | None,
) -> MemoryEntry | None:
    """Persist a candidate memory card as a quarantined sketch.

    Dedup semantics (spec §5): an exact content-hash match on a
    non-retired entry accretes evidence onto the existing entry instead of
    creating a new one — unless the existing entry is `rejected`, in which
    case the card is dropped silently (sticky rejection).
    Returns the entry evidence landed on, or None if dropped.
    """
    if scope.memory_paused_at is not None:
        return None

    body = (card.get("body") or "").strip()
    title = (card.get("title") or "").strip()[:200]
    kind = card.get("kind") or "project_fact"
    if not body or not title or kind not in MEMORY_KINDS:
        return None

    content_hash = canonical_content_hash(body)
    existing = (
        db.query(MemoryEntry)
        .filter(MemoryEntry.scope_id == scope.id, MemoryEntry.content_hash == content_hash)
        .first()
    )
    if existing is not None:
        if existing.status == "rejected":
            return None
        if existing.status in _DEDUP_BLOCKING_STATUSES:
            _attach_evidence(db, existing, engineer_id, session_id, citation)
            return existing
        return None  # retired: only manual un-retire reopens (spec §7)

    entry = MemoryEntry(
        scope_id=scope.id,
        kind=kind,
        title=title,
        body=body,
        concepts=card.get("concepts") or None,
        files=card.get("files") or None,
        content_hash=content_hash,
        origin=origin,
        created_by_engineer_id=engineer_id,
    )
    db.add(entry)
    db.flush()
    _attach_evidence(db, entry, engineer_id, session_id, citation)
    db.add(MemoryEvent(memory_id=entry.id, event_kind="sketch_created", actor="system"))
    db.flush()
    return entry


def _attach_evidence(
    db: Session,
    entry: MemoryEntry,
    engineer_id: str | None,
    session_id: str | None,
    citation: dict | None,
) -> None:
    db.add(
        MemoryEvidence(
            memory_id=entry.id,
            evidence_kind="transcript_citation",
            session_id=session_id,
            engineer_id=engineer_id,
            payload=citation,
        )
    )
    db.flush()
