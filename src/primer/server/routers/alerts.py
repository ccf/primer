import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.schemas import AlertResponse, DetectionResult
from primer.server.deps import AuthContext, get_auth_context, require_role
from primer.server.services.alerting_service import (
    acknowledge_alert,
    detect_anomalies,
    dismiss_alert,
    get_alerts,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    acknowledged: bool | None = None,
    dismissed: bool = False,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    # Scope alerts by role
    team_id = None
    engineer_id = None
    if auth.role == "team_lead":
        if not auth.team_id:
            return []
        team_id = auth.team_id
    elif auth.role == "engineer":
        engineer_id = auth.engineer_id

    alerts = get_alerts(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        acknowledged=acknowledged,
        dismissed=dismissed,
        limit=limit,
    )
    return alerts


@router.post("/detect", response_model=DetectionResult)
def trigger_detection(
    team_id: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    alerts = detect_anomalies(db, team_id=team_id)
    db.commit()
    return DetectionResult(
        alerts_created=len(alerts),
        alert_ids=[a.id for a in alerts],
    )


def _check_alert_access(alert, auth: AuthContext):
    """Verify the caller has access to this alert based on role scoping."""
    if auth.role == "admin":
        return
    if auth.role == "team_lead":
        if not auth.team_id or alert.team_id != auth.team_id:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return
    if auth.role == "engineer" and alert.engineer_id != auth.engineer_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
def ack_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    alert = acknowledge_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    _check_alert_access(alert, auth)
    db.commit()
    return alert


@router.patch("/{alert_id}/dismiss", response_model=AlertResponse)
def dismiss(
    alert_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    alert = dismiss_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    _check_alert_access(alert, auth)
    db.commit()
    return alert
