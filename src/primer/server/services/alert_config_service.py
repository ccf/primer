from fastapi import HTTPException
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.models import AlertConfig
from primer.common.schemas import AlertConfigCreate, AlertConfigUpdate, AlertThresholds

VALID_ALERT_TYPES = [
    "friction_spike",
    "usage_drop",
    "cost_spike_warning",
    "cost_spike_critical",
    "success_rate_drop",
]


def get_alert_configs(db: Session, team_id: str | None = None) -> list[AlertConfig]:
    q = db.query(AlertConfig)
    if team_id is not None:
        q = q.filter(AlertConfig.team_id == team_id)
    return q.order_by(AlertConfig.created_at.desc()).all()


def create_alert_config(db: Session, payload: AlertConfigCreate) -> AlertConfig:
    if payload.alert_type not in VALID_ALERT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid alert type: {payload.alert_type}")

    existing = (
        db.query(AlertConfig)
        .filter(
            AlertConfig.team_id == payload.team_id,
            AlertConfig.alert_type == payload.alert_type,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="Alert config for this team+type already exists"
        )

    config = AlertConfig(
        team_id=payload.team_id,
        alert_type=payload.alert_type,
        enabled=payload.enabled,
        threshold=payload.threshold,
    )
    db.add(config)
    db.flush()
    return config


def update_alert_config(db: Session, config_id: str, payload: AlertConfigUpdate) -> AlertConfig:
    config = db.query(AlertConfig).filter(AlertConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Alert config not found")

    if payload.enabled is not None:
        config.enabled = payload.enabled
    if payload.threshold is not None:
        config.threshold = payload.threshold

    db.flush()
    return config


def delete_alert_config(db: Session, config_id: str) -> None:
    config = db.query(AlertConfig).filter(AlertConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Alert config not found")
    db.delete(config)
    db.flush()


def resolve_thresholds(db: Session, team_id: str | None = None) -> AlertThresholds:
    """Resolve effective thresholds: team override > global override > settings defaults."""
    defaults = {
        "friction_spike": settings.alert_friction_spike_multiplier,
        "usage_drop": settings.alert_usage_drop_ratio,
        "cost_spike_warning": settings.alert_cost_spike_warning,
        "cost_spike_critical": settings.alert_cost_spike_critical,
        "success_rate_drop": settings.alert_success_rate_drop_pp,
    }

    # Load global overrides (team_id IS NULL)
    global_configs = db.query(AlertConfig).filter(AlertConfig.team_id.is_(None)).all()
    for cfg in global_configs:
        if cfg.alert_type in defaults and cfg.enabled:
            defaults[cfg.alert_type] = cfg.threshold

    # Load team-specific overrides (higher priority)
    if team_id:
        team_configs = db.query(AlertConfig).filter(AlertConfig.team_id == team_id).all()
        for cfg in team_configs:
            if cfg.alert_type in defaults and cfg.enabled:
                defaults[cfg.alert_type] = cfg.threshold

    return AlertThresholds(
        friction_spike_multiplier=defaults["friction_spike"],
        usage_drop_ratio=defaults["usage_drop"],
        cost_spike_warning=defaults["cost_spike_warning"],
        cost_spike_critical=defaults["cost_spike_critical"],
        success_rate_drop_pp=defaults["success_rate_drop"],
    )
