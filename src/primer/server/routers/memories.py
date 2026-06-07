"""Memory write-path endpoints (hive mind, Plan 2a)."""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import get_db
from primer.common.models import MemoryEvidence
from primer.common.models import Session as SessionModel
from primer.common.redaction import build_extra_detectors
from primer.common.schemas import RememberRequest, RememberResponse
from primer.server.services.memory_service import (
    create_sketch,
    get_or_create_project_scope,
    memory_capture_active,
    scrub_identity,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])


@router.post("/remember", response_model=RememberResponse)
def remember(
    payload: RememberRequest,
    x_api_key: str | None = Header(default=None),
    x_device_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Explicit memory write from an in-flight session (spec §5).

    Quarantined like all writes: the sketch goes through the same
    consolidation/judge gates as passive extraction. The per-session limit is
    a best-effort soft cap — the count-then-write is not atomic under
    concurrent requests, which is acceptable because entries are quarantined
    and the cap is advisory.
    """
    from primer.server.routers.ingest import _authenticate_ingest_engineer

    engineer = _authenticate_ingest_engineer(db, api_key=x_api_key, device_token=x_device_token)

    if not memory_capture_active():
        raise HTTPException(status_code=409, detail="Memory capture is not enabled")

    session = db.query(SessionModel).filter(SessionModel.id == payload.session_id).first()
    if session is None or session.engineer_id != engineer.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.repository_id is None:
        raise HTTPException(
            status_code=422, detail="Session has no repository; cannot scope memory"
        )

    existing = (
        db.query(MemoryEvidence)
        .filter(
            MemoryEvidence.session_id == payload.session_id,
            MemoryEvidence.evidence_kind == "explicit_remember",
        )
        .count()
    )
    if existing >= settings.memory_remember_per_session:
        raise HTTPException(status_code=429, detail="Per-session remember limit reached")

    # scrub_identity does secret redaction + identity scrub in one pass — the
    # same treatment passive extraction applies, so explicit and passive
    # memories are equally clean for cross-engineer display (spec §10).
    extra = build_extra_detectors(settings.redaction_extra_patterns)
    names = [engineer.name] if engineer.name else []
    text = scrub_identity(payload.text, names, extra=extra)
    redacted_files = (
        [scrub_identity(f, names, extra=extra) for f in payload.files] if payload.files else None
    )
    scope = get_or_create_project_scope(db, session.repository_id)
    entry, created = create_sketch(
        db,
        scope=scope,
        card={"kind": payload.kind, "title": text[:120], "body": text, "files": redacted_files},
        origin="remember_tool",
        engineer_id=engineer.id,
        session_id=payload.session_id,
        citation=None,
        evidence_kind="explicit_remember",
    )
    db.commit()
    if entry is None:
        return RememberResponse(status="dropped")
    return RememberResponse(
        status="sketch_created" if created else "evidence_accreted", memory_id=entry.id
    )
