import logging

import httpx

from primer.common.config import settings
from primer.common.models import Alert

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    "critical": "#dc2626",
    "warning": "#f59e0b",
    "info": "#3b82f6",
}


def _build_slack_blocks(alert: Alert) -> list[dict]:
    """Build Slack Block Kit blocks for an alert."""
    color = SEVERITY_COLORS.get(alert.severity, "#6b7280")
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": alert.title, "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": alert.message},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"*Type:* {alert.alert_type}"},
                {"type": "mrkdwn", "text": f"*Severity:* {alert.severity}"},
                {"type": "mrkdwn", "text": f"*Metric:* {alert.metric_name}"},
            ],
        },
    ]

    fields = []
    if alert.expected_value is not None:
        fields.append({"type": "mrkdwn", "text": f"*Expected:* {alert.expected_value:.2f}"})
    if alert.actual_value is not None:
        fields.append({"type": "mrkdwn", "text": f"*Actual:* {alert.actual_value:.2f}"})
    if fields:
        blocks.append({"type": "section", "fields": fields})

    return [{"color": color, "blocks": blocks}]


def send_alert_to_slack(alert: Alert) -> None:
    """Send an alert notification to Slack. Never raises."""
    if not settings.slack_alerts_enabled or not settings.slack_webhook_url:
        return

    try:
        attachments = _build_slack_blocks(alert)
        payload = {"attachments": attachments}
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(settings.slack_webhook_url, json=payload)
            resp.raise_for_status()
    except Exception:
        logger.exception("Failed to send Slack notification for alert %s", alert.id)


def send_test_message(webhook_url: str) -> tuple[bool, str | None]:
    """Send a test message to a Slack webhook. Returns (success, error)."""
    payload = {
        "text": "Primer test notification — your Slack integration is working!",
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(webhook_url, json=payload)
            resp.raise_for_status()
        return True, None
    except Exception as exc:
        return False, str(exc)
