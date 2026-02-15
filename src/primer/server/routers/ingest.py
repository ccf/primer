import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import get_db
from primer.common.models import Session as SessionModel
from primer.common.schemas import (
    BulkIngestPayload,
    BulkIngestResponse,
    IngestResponse,
    SessionFacetsPayload,
    SessionIngestPayload,
)
from primer.server.deps import verify_api_key
from primer.server.middleware import limiter
from primer.server.services.ingest_service import (
    log_ingest_event,
    upsert_facets,
    upsert_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


@router.post("/session", response_model=IngestResponse)
@limiter.limit(settings.rate_limit_ingest)
def ingest_session(
    request: Request,
    payload: SessionIngestPayload,
    db: Session = Depends(get_db),
):
    engineer = verify_api_key(payload.api_key, db)
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

        db.commit()

        # Send Slack notifications only after a successful commit
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
    db: Session = Depends(get_db),
):
    engineer = verify_api_key(payload.api_key, db)
    results = []
    for session_payload in payload.sessions:
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
    x_api_key: str = Header(),
    db: Session = Depends(get_db),
):
    engineer = verify_api_key(x_api_key, db)
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
