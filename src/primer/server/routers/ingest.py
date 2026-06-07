import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import get_db
from primer.common.models import Session as SessionModel
from primer.common.redaction import (
    build_disabled_set,
    build_extra_detectors,
    redact_ingest_dict,
    scrub_url_credentials,
)
from primer.common.schemas import (
    BulkIngestPayload,
    BulkIngestResponse,
    IngestResponse,
    SessionFacetsPayload,
    SessionIngestPayload,
)
from primer.server.deps import verify_api_key, verify_device_token
from primer.server.middleware import limiter
from primer.server.services.background_job_service import (
    JOB_TYPE_SESSION_INGEST,
    enqueue_background_job,
)
from primer.server.services.ingest_service import (
    log_ingest_event,
    upsert_facets,
    upsert_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


def _authenticate_ingest_engineer(
    db: Session,
    *,
    api_key: str | None = None,
    device_token: str | None = None,
):
    if device_token:
        return verify_device_token(device_token, db)
    if api_key:
        return verify_api_key(api_key, db)
    raise HTTPException(status_code=401, detail="Authentication required")


# Fields that can carry sensitive content and are dropped wholesale if redaction
# itself fails (fail closed on content, open on metrics). git_remote_url is
# handled separately (targeted scrub, see _apply_redaction).
_TEXT_BEARING_FIELDS = (
    "first_prompt",
    "summary",
    "messages",
    "commits",
    "source_metadata",
    "facets",
    "customizations",
)


def _apply_redaction(payload: SessionIngestPayload) -> SessionIngestPayload:
    """Redact text-bearing fields before any persistence (incl. job queue).

    On any redaction failure: fail closed on content, open on metrics —
    strip the text-bearing fields and persist the structural telemetry,
    never an unredacted payload and never a 500.
    """
    if not settings.redaction_enabled:
        return payload
    try:
        raw = payload.model_dump(mode="json")
        api_key = raw.pop("api_key", None)  # auth credential — exclude from the walk
        redacted, counts = redact_ingest_dict(
            raw,
            disabled=build_disabled_set(settings.redaction_disabled_detectors),
            extra=build_extra_detectors(settings.redaction_extra_patterns),
        )
        redacted["api_key"] = api_key
        if counts:
            logger.info(
                "Redacted %d sensitive value(s) in session %s",
                sum(counts.values()),
                payload.session_id,
            )
        return SessionIngestPayload(**redacted)
    except Exception:
        logger.error(
            "Redaction failed for session %s — stripping text content from payload",
            payload.session_id,
            exc_info=True,
        )
        # model_copy(update=...) bypasses validators; all six fields are Optional.
        stripped = payload.model_copy(update=dict.fromkeys(_TEXT_BEARING_FIELDS))
        # git_remote_url isn't text-bearing, but HTTPS remotes can carry
        # user:token credentials. Attempt the one-regex targeted scrub (almost
        # certainly not what crashed); if even that fails, drop the field.
        if stripped.git_remote_url:
            try:
                cleaned, _ = scrub_url_credentials(stripped.git_remote_url)
                stripped = stripped.model_copy(update={"git_remote_url": cleaned})
            except Exception:
                stripped = stripped.model_copy(update={"git_remote_url": None})
        return stripped


@router.post("/session", response_model=IngestResponse)
@limiter.limit(settings.rate_limit_ingest)
def ingest_session(
    request: Request,
    payload: SessionIngestPayload,
    background_tasks: BackgroundTasks,
    x_device_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    engineer = _authenticate_ingest_engineer(
        db,
        api_key=payload.api_key,
        device_token=x_device_token,
    )
    payload = _apply_redaction(payload)

    # ── Async path: enqueue the heavy work and return immediately ──
    if settings.background_jobs_enabled:
        # Strip the raw api_key before persisting — engineer_id is already
        # resolved and the plaintext key must not be stored in the jobs table.
        serialized = payload.model_dump(mode="json", exclude={"api_key"})
        enqueue_background_job(
            db,
            job_type=JOB_TYPE_SESSION_INGEST,
            payload={
                "engineer_id": engineer.id,
                "ingest_payload": serialized,
            },
            created_by_engineer_id=engineer.id,
        )
        db.commit()
        return Response(
            content=IngestResponse(
                status="accepted", session_id=payload.session_id, created=False
            ).model_dump_json(),
            status_code=202,
            media_type="application/json",
        )

    # ── Sync fallback: inline processing when background jobs are disabled ──
    try:
        created = upsert_session(db, engineer.id, payload)
        log_ingest_event(db, engineer.id, "session", payload.session_id, None, "ok")

        # Trigger anomaly detection (non-blocking)
        alert_snapshots: list[dict] = []
        try:
            from primer.server.services.alerting_service import (
                detect_anomalies,
                send_alert_notifications,
            )

            _alerts, alert_snapshots = detect_anomalies(
                db, team_id=engineer.team_id, engineer_id=engineer.id
            )
        except Exception:
            logger.exception("Anomaly detection failed during ingest")

        # Auto-extract facets
        if (
            settings.facet_extraction_enabled
            and settings.anthropic_api_key
            and payload.messages
            and not payload.facets
        ):
            from primer.server.services.facet_extraction_service import (
                extract_and_store_facets_for_session,
            )

            background_tasks.add_task(extract_and_store_facets_for_session, payload.session_id)

        db.commit()

        if alert_snapshots:
            send_alert_notifications(alert_snapshots)

        return IngestResponse(status="ok", session_id=payload.session_id, created=created)
    except Exception as e:
        db.rollback()
        log_ingest_event(db, engineer.id, "session", payload.session_id, None, "error", str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/bulk", response_model=BulkIngestResponse)
@limiter.limit(settings.rate_limit_ingest)
def ingest_bulk(
    request: Request,
    payload: BulkIngestPayload,
    x_device_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    engineer = _authenticate_ingest_engineer(
        db,
        api_key=payload.api_key,
        device_token=x_device_token,
    )
    results = []
    for session_payload in payload.sessions:
        # Redact before any persistence. If an async path is ever added to bulk,
        # _apply_redaction must still run before enqueue_background_job.
        session_payload = _apply_redaction(session_payload)
        try:
            created = upsert_session(db, engineer.id, session_payload)
            log_ingest_event(db, engineer.id, "bulk", session_payload.session_id, None, "ok")
            results.append(
                IngestResponse(status="ok", session_id=session_payload.session_id, created=created)
            )
        except Exception as e:
            db.rollback()
            log_ingest_event(
                db, engineer.id, "bulk", session_payload.session_id, None, "error", str(e)
            )
            results.append(
                IngestResponse(status="error", session_id=session_payload.session_id, created=False)
            )
    db.commit()
    return BulkIngestResponse(status="ok", results=results)


@router.post("/facets/{session_id}", response_model=IngestResponse)
@limiter.limit(settings.rate_limit_ingest)
def ingest_facets(
    request: Request,
    session_id: str,
    payload: SessionFacetsPayload,
    x_api_key: str | None = Header(default=None),
    x_device_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    engineer = _authenticate_ingest_engineer(db, api_key=x_api_key, device_token=x_device_token)
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.engineer_id != engineer.id:
        raise HTTPException(status_code=403, detail="Not your session")

    upsert_facets(db, session_id, payload)
    session.has_facets = True
    log_ingest_event(db, engineer.id, "facets", session_id, None, "ok")
    db.commit()
    return IngestResponse(status="ok", session_id=session_id, created=False)
