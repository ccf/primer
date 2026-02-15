from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.schemas import (
    AlertConfigCreate,
    AlertConfigResponse,
    AlertConfigUpdate,
    AlertThresholds,
)
from primer.server.deps import AuthContext, require_role
from primer.server.services import alert_config_service, audit_service

router = APIRouter(prefix="/api/v1/alert-configs", tags=["alert-configs"])


@router.get("", response_model=list[AlertConfigResponse])
def list_alert_configs(
    team_id: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    return alert_config_service.get_alert_configs(db, team_id=team_id)


@router.get("/resolved", response_model=AlertThresholds)
def resolved_thresholds(
    team_id: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    return alert_config_service.resolve_thresholds(db, team_id=team_id)


@router.post("", response_model=AlertConfigResponse, status_code=201)
def create_alert_config(
    payload: AlertConfigCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    config = alert_config_service.create_alert_config(db, payload)
    ip = request.client.host if request.client else None
    audit_service.log_action(
        db,
        auth,
        "create",
        "alert_config",
        config.id,
        details={"alert_type": config.alert_type, "threshold": config.threshold},
        ip_address=ip,
    )
    db.commit()
    db.refresh(config)
    return config


@router.patch("/{config_id}", response_model=AlertConfigResponse)
def update_alert_config(
    config_id: str,
    payload: AlertConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    config = alert_config_service.update_alert_config(db, config_id, payload)
    ip = request.client.host if request.client else None
    audit_service.log_action(
        db,
        auth,
        "update",
        "alert_config",
        config_id,
        details=payload.model_dump(exclude_none=True),
        ip_address=ip,
    )
    db.commit()
    db.refresh(config)
    return config


@router.delete("/{config_id}", status_code=204)
def delete_alert_config(
    config_id: str,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role("admin")),
):
    alert_config_service.delete_alert_config(db, config_id)
    ip = request.client.host if request.client else None
    audit_service.log_action(
        db,
        auth,
        "delete",
        "alert_config",
        config_id,
        ip_address=ip,
    )
    db.commit()
