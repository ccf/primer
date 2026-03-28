import logging
import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.common.models import Alert, Engineer, ModelUsage, SessionFacets
from primer.common.models import Session as SessionModel
from primer.common.pricing import estimate_cost
from primer.server.services.alert_config_service import resolve_alert_policy_map

logger = logging.getLogger(__name__)


def detect_anomalies(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
) -> tuple[list[Alert], list[dict]]:
    """Run all anomaly detectors and return newly created alerts + notification snapshots.

    Returns (alerts, snapshots).  Callers should commit the transaction first,
    then call ``send_alert_notifications(snapshots)`` so that Slack messages
    are only sent for alerts that were actually persisted.
    """
    policies = resolve_alert_policy_map(db, team_id=team_id)
    alerts: list[Alert] = []
    for detector in [
        _detect_friction_spike,
        _detect_usage_drop,
        _detect_cost_spike,
        _detect_success_rate_drop,
    ]:
        try:
            result = detector(db, team_id=team_id, engineer_id=engineer_id, policies=policies)
            if result:
                alerts.append(result)
        except Exception:
            logger.exception("Anomaly detector %s failed", detector.__name__)

    # Snapshot alert data while the session is still open.  ORM objects become
    # detached after commit (expire_on_commit=True), so we capture plain dicts
    # now and let the caller dispatch notifications post-commit.
    snapshots = [_snapshot_alert(a) for a in alerts]

    return alerts, snapshots


def send_alert_notifications(snapshots: list[dict]) -> None:
    """Dispatch Slack notifications in a background thread.

    Call this *after* the DB transaction has been committed so that phantom
    notifications are never sent for rolled-back alerts.
    """
    if snapshots:
        threading.Thread(target=_notify_slack_batch, args=(snapshots,), daemon=True).start()


def _recent_window(
    db: Session,
    team_id: str | None,
    engineer_id: str | None,
    days: int,
):
    """Return base session query filtered to last N days."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    q = db.query(SessionModel).filter(SessionModel.started_at >= cutoff)
    if engineer_id:
        q = q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        q = q.join(Engineer).filter(Engineer.team_id == team_id)
    return q


def _create_alert_if_new(
    db: Session,
    team_id: str | None,
    engineer_id: str | None,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    metric_name: str,
    expected_value: float | None,
    actual_value: float | None,
    threshold: float | None,
) -> Alert | None:
    """Check for recent duplicate and create alert atomically within the session.

    Combines dedup check + insert in one method with a flush to minimise
    the race window under concurrent ingest traffic.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    q = db.query(Alert).filter(
        Alert.alert_type == alert_type,
        Alert.dismissed == False,  # noqa: E712
        Alert.detected_at >= cutoff,
    )
    if engineer_id:
        q = q.filter(Alert.engineer_id == engineer_id)
    elif team_id:
        q = q.filter(Alert.team_id == team_id)

    if q.first() is not None:
        return None

    alert = Alert(
        team_id=team_id,
        engineer_id=engineer_id,
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        metric_name=metric_name,
        expected_value=expected_value,
        actual_value=actual_value,
        threshold=threshold,
    )
    db.add(alert)
    db.flush()

    return alert


def _snapshot_alert(alert: Alert) -> dict:
    """Capture alert attributes as a plain dict for use outside the DB session."""
    return {
        "id": alert.id,
        "severity": alert.severity,
        "title": alert.title,
        "message": alert.message,
        "alert_type": alert.alert_type,
        "metric_name": alert.metric_name,
        "expected_value": alert.expected_value,
        "actual_value": alert.actual_value,
    }


class _AlertSnapshot:
    """Lightweight stand-in for Alert that satisfies send_alert_to_slack's attribute access."""

    def __init__(self, data: dict):
        self.__dict__.update(data)


def _notify_slack_batch(snapshots: list[dict]) -> None:
    """Send Slack notifications for a batch of alerts. Runs in a background thread."""
    from primer.server.services.slack_service import send_alert_to_slack

    for snap in snapshots:
        try:
            send_alert_to_slack(_AlertSnapshot(snap))  # type: ignore[arg-type]
        except Exception:
            logger.exception("Slack notification failed for alert %s", snap.get("id"))


def _detect_friction_spike(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    policies=None,
) -> Alert | None:
    policy = (policies or {}).get("friction_spike")
    if policy and not policy.effective_enabled:
        return None
    multiplier = policy.effective_threshold if policy else 2.0
    # Last day friction
    day_q = _recent_window(db, team_id, engineer_id, 1)
    day_sessions = day_q.all()
    day_friction = 0
    for s in day_sessions:
        if s.facets and s.facets.friction_counts:
            day_friction += sum(s.facets.friction_counts.values())

    # 7-day avg friction per day
    week_q = _recent_window(db, team_id, engineer_id, 7)
    week_sessions = week_q.all()
    week_friction = 0
    for s in week_sessions:
        if s.facets and s.facets.friction_counts:
            week_friction += sum(s.facets.friction_counts.values())
    avg_daily_friction = week_friction / 7

    if avg_daily_friction > 0 and day_friction > avg_daily_friction * multiplier:
        return _create_alert_if_new(
            db,
            team_id=team_id,
            engineer_id=engineer_id,
            alert_type="friction_spike",
            severity="warning",
            title="Friction spike detected",
            message=(
                f"Friction count today ({day_friction}) is more than "
                f"{multiplier:.1f}x the 7-day average ({avg_daily_friction:.1f})"
            ),
            metric_name="friction_count",
            expected_value=avg_daily_friction,
            actual_value=float(day_friction),
            threshold=avg_daily_friction * multiplier,
        )
    return None


def _detect_usage_drop(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    policies=None,
) -> Alert | None:
    policy = (policies or {}).get("usage_drop")
    if policy and not policy.effective_enabled:
        return None
    ratio_threshold = policy.effective_threshold if policy else 0.5
    day_count = _recent_window(db, team_id, engineer_id, 1).count()
    week_q = _recent_window(db, team_id, engineer_id, 7)
    week_count = week_q.count()
    avg_daily = week_count / 7

    if avg_daily >= 2 and day_count < avg_daily * ratio_threshold:
        return _create_alert_if_new(
            db,
            team_id=team_id,
            engineer_id=engineer_id,
            alert_type="usage_drop",
            severity="warning",
            title="Usage drop detected",
            message=(
                f"Sessions today ({day_count}) dropped more than "
                f"{(1 - ratio_threshold) * 100:.0f}% below 7-day average ({avg_daily:.1f})"
            ),
            metric_name="daily_sessions",
            expected_value=avg_daily,
            actual_value=float(day_count),
            threshold=avg_daily * ratio_threshold,
        )
    return None


def _detect_cost_spike(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    policies=None,
) -> Alert | None:
    warning_policy = (policies or {}).get("cost_spike_warning")
    critical_policy = (policies or {}).get("cost_spike_critical")
    warning_enabled = warning_policy.effective_enabled if warning_policy else True
    critical_enabled = critical_policy.effective_enabled if critical_policy else True
    warning_multiplier = warning_policy.effective_threshold if warning_policy else 2.0
    critical_multiplier = critical_policy.effective_threshold if critical_policy else 3.0
    if not warning_enabled and not critical_enabled:
        return None

    def _daily_cost(days: int) -> float:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        q = (
            db.query(
                ModelUsage.model_name,
                func.sum(ModelUsage.input_tokens),
                func.sum(ModelUsage.output_tokens),
                func.sum(ModelUsage.cache_read_tokens),
                func.sum(ModelUsage.cache_creation_tokens),
            )
            .join(SessionModel)
            .filter(SessionModel.started_at >= cutoff)
        )
        if engineer_id:
            q = q.filter(SessionModel.engineer_id == engineer_id)
        elif team_id:
            q = q.join(Engineer).filter(Engineer.team_id == team_id)
        q = q.group_by(ModelUsage.model_name)
        total = sum(
            estimate_cost(n, i or 0, o or 0, cr or 0, cc or 0) for n, i, o, cr, cc in q.all()
        )
        return total

    day_cost = _daily_cost(1)
    week_cost = _daily_cost(7)
    avg_daily_cost = week_cost / 7

    if avg_daily_cost > 0:
        ratio = day_cost / avg_daily_cost
        if critical_enabled and ratio > critical_multiplier:
            severity = "critical"
            threshold_multiplier = critical_multiplier
        elif warning_enabled and ratio > warning_multiplier:
            severity = "warning"
            threshold_multiplier = warning_multiplier
        else:
            return None

        return _create_alert_if_new(
            db,
            team_id=team_id,
            engineer_id=engineer_id,
            alert_type="cost_spike",
            severity=severity,
            title="Cost spike detected",
            message=(
                f"Today's cost (${day_cost:.2f}) is {ratio:.1f}x "
                f"the 7-day average (${avg_daily_cost:.2f})"
            ),
            metric_name="daily_cost",
            expected_value=avg_daily_cost,
            actual_value=day_cost,
            threshold=avg_daily_cost * threshold_multiplier,
        )
    return None


def _detect_success_rate_drop(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    policies=None,
) -> Alert | None:
    policy = (policies or {}).get("success_rate_drop")
    if policy and not policy.effective_enabled:
        return None
    threshold_pp = policy.effective_threshold if policy else 20.0

    def _success_rate(days: int) -> float | None:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        q = (
            db.query(SessionFacets.outcome)
            .join(SessionModel)
            .filter(
                SessionModel.started_at >= cutoff,
                SessionFacets.outcome.isnot(None),
            )
        )
        if engineer_id:
            q = q.filter(SessionModel.engineer_id == engineer_id)
        elif team_id:
            q = q.join(Engineer).filter(Engineer.team_id == team_id)
        outcomes = [r[0] for r in q.all()]
        normalized_outcomes = [
            normalized
            for outcome in outcomes
            if (normalized := canonical_outcome(outcome)) is not None
        ]
        if not normalized_outcomes:
            return None
        return sum(1 for outcome in normalized_outcomes if is_success_outcome(outcome)) / len(
            normalized_outcomes
        )

    day_rate = _success_rate(1)
    week_rate = _success_rate(7)

    if day_rate is not None and week_rate is not None:
        drop_pp = (week_rate - day_rate) * 100
        if drop_pp > threshold_pp:
            return _create_alert_if_new(
                db,
                team_id=team_id,
                engineer_id=engineer_id,
                alert_type="success_rate_drop",
                severity="warning",
                title="Success rate drop",
                message=(
                    f"Success rate today ({day_rate:.0%}) dropped "
                    f"{drop_pp:.0f}pp from 7-day average ({week_rate:.0%})"
                ),
                metric_name="success_rate",
                expected_value=week_rate,
                actual_value=day_rate,
                threshold=week_rate - (threshold_pp / 100),
            )
    return None


def get_alerts(
    db: Session,
    team_id: str | None = None,
    engineer_id: str | None = None,
    acknowledged: bool | None = None,
    dismissed: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Alert]:
    q = db.query(Alert).filter(Alert.dismissed == dismissed)
    if team_id:
        q = q.filter(Alert.team_id == team_id)
    if engineer_id:
        q = q.filter(Alert.engineer_id == engineer_id)
    if acknowledged is not None:
        if acknowledged:
            q = q.filter(Alert.acknowledged_at.isnot(None))
        else:
            q = q.filter(Alert.acknowledged_at.is_(None))
    return q.order_by(Alert.detected_at.desc()).offset(offset).limit(limit).all()


def acknowledge_alert(db: Session, alert_id: str) -> Alert | None:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.acknowledged_at = datetime.now(UTC)
        db.flush()
    return alert


def dismiss_alert(db: Session, alert_id: str) -> Alert | None:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.dismissed = True
        db.flush()
    return alert
