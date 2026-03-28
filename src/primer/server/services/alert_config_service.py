from fastapi import HTTPException
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.models import AlertConfig
from primer.common.schemas import (
    AlertConfigCreate,
    AlertConfigUpdate,
    AlertThresholds,
    ResolvedAlertPolicy,
    ResolvedAlertPolicyResponse,
)

VALID_ALERT_TYPES = [
    "friction_spike",
    "usage_drop",
    "cost_spike_warning",
    "cost_spike_critical",
    "success_rate_drop",
]

ALERT_POLICY_METADATA = {
    "friction_spike": {
        "label": "Friction Spike",
        "description": (
            "Alert when today's friction count exceeds the recent baseline by a multiplier."
        ),
        "detector_window": "today vs trailing 7-day daily average",
        "unit_label": "x baseline",
    },
    "usage_drop": {
        "label": "Usage Drop",
        "description": "Alert when daily session volume drops below the recent average by a ratio.",
        "detector_window": "today vs trailing 7-day daily average",
        "unit_label": "x average",
    },
    "cost_spike_warning": {
        "label": "Cost Spike Warning",
        "description": "Warn when daily cost spikes above the recent daily average.",
        "detector_window": "today vs trailing 7-day daily average",
        "unit_label": "x average",
    },
    "cost_spike_critical": {
        "label": "Cost Spike Critical",
        "description": "Escalate when the cost spike is severe enough to warrant critical paging.",
        "detector_window": "today vs trailing 7-day daily average",
        "unit_label": "x average",
    },
    "success_rate_drop": {
        "label": "Success Rate Drop",
        "description": (
            "Alert when today's success rate drops below the recent baseline by percentage points."
        ),
        "detector_window": "today vs trailing 7-day success rate",
        "unit_label": "percentage points",
    },
}


def get_alert_configs(db: Session, team_id: str | None = None) -> list[AlertConfig]:
    q = db.query(AlertConfig)
    if team_id is not None:
        q = q.filter(AlertConfig.team_id == team_id)
    return q.order_by(AlertConfig.created_at.desc()).all()


def create_alert_config(db: Session, payload: AlertConfigCreate) -> AlertConfig:
    if payload.alert_type not in VALID_ALERT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid alert type: {payload.alert_type}")

    if payload.team_id is None:
        team_filter = AlertConfig.team_id.is_(None)
    else:
        team_filter = AlertConfig.team_id == payload.team_id
    existing = (
        db.query(AlertConfig)
        .filter(team_filter, AlertConfig.alert_type == payload.alert_type)
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
        policy.alert_type: policy.effective_threshold
        for policy in resolve_alert_policies(db, team_id=team_id).policies
    }

    return AlertThresholds(
        friction_spike_multiplier=defaults["friction_spike"],
        usage_drop_ratio=defaults["usage_drop"],
        cost_spike_warning=defaults["cost_spike_warning"],
        cost_spike_critical=defaults["cost_spike_critical"],
        success_rate_drop_pp=defaults["success_rate_drop"],
    )


def resolve_alert_policies(
    db: Session,
    team_id: str | None = None,
) -> ResolvedAlertPolicyResponse:
    defaults = _default_thresholds()
    global_configs = {
        cfg.alert_type: cfg
        for cfg in db.query(AlertConfig).filter(AlertConfig.team_id.is_(None)).all()
    }
    team_configs = (
        {
            cfg.alert_type: cfg
            for cfg in db.query(AlertConfig).filter(AlertConfig.team_id == team_id).all()
        }
        if team_id
        else {}
    )

    policies: list[ResolvedAlertPolicy] = []
    for alert_type in VALID_ALERT_TYPES:
        default_threshold = defaults[alert_type]
        global_cfg = global_configs.get(alert_type)
        team_cfg = team_configs.get(alert_type)

        effective_threshold = default_threshold
        effective_enabled = True
        source = "default"

        if global_cfg is not None:
            effective_threshold = global_cfg.threshold
            effective_enabled = global_cfg.enabled
            source = "global_override" if global_cfg.enabled else "global_disabled"

        if team_cfg is not None:
            effective_threshold = team_cfg.threshold
            effective_enabled = team_cfg.enabled
            source = "team_override" if team_cfg.enabled else "team_disabled"

        metadata = ALERT_POLICY_METADATA[alert_type]
        policies.append(
            ResolvedAlertPolicy(
                alert_type=alert_type,
                label=metadata["label"],
                description=metadata["description"],
                detector_window=metadata["detector_window"],
                unit_label=metadata["unit_label"],
                effective_threshold=effective_threshold,
                effective_enabled=effective_enabled,
                source=source,  # type: ignore[arg-type]
                default_threshold=default_threshold,
                global_override_threshold=global_cfg.threshold if global_cfg else None,
                global_override_enabled=global_cfg.enabled if global_cfg else None,
                team_override_threshold=team_cfg.threshold if team_cfg else None,
                team_override_enabled=team_cfg.enabled if team_cfg else None,
            )
        )

    return ResolvedAlertPolicyResponse(
        team_id=team_id,
        notifications_enabled=settings.slack_alerts_enabled,
        webhook_configured=bool(settings.slack_webhook_url),
        policies=policies,
    )


def resolve_alert_policy_map(
    db: Session,
    team_id: str | None = None,
) -> dict[str, ResolvedAlertPolicy]:
    response = resolve_alert_policies(db, team_id=team_id)
    return {policy.alert_type: policy for policy in response.policies}


def _default_thresholds() -> dict[str, float]:
    return {
        "friction_spike": settings.alert_friction_spike_multiplier,
        "usage_drop": settings.alert_usage_drop_ratio,
        "cost_spike_warning": settings.alert_cost_spike_warning,
        "cost_spike_critical": settings.alert_cost_spike_critical,
        "success_rate_drop": settings.alert_success_rate_drop_pp,
    }
