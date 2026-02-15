from unittest.mock import MagicMock, patch

from primer.common.models import Alert


def test_slack_disabled_by_default(db_session):
    """When slack_alerts_enabled is False (default), no HTTP call is made."""
    alert = Alert(
        alert_type="cost_spike",
        severity="warning",
        title="Test alert",
        message="Test message",
        metric_name="daily_cost",
    )
    db_session.add(alert)
    db_session.flush()

    with patch("primer.server.services.slack_service.httpx.Client") as mock_client:
        from primer.server.services.slack_service import send_alert_to_slack

        send_alert_to_slack(alert)
        mock_client.assert_not_called()


def test_slack_sends_when_enabled(db_session):
    """When enabled with webhook URL, makes HTTP POST with correct payload."""
    alert = Alert(
        alert_type="friction_spike",
        severity="critical",
        title="Friction spike detected",
        message="Friction is 3x normal",
        metric_name="friction_count",
        expected_value=5.0,
        actual_value=15.0,
    )
    db_session.add(alert)
    db_session.flush()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)
    mock_client_instance.post.return_value = mock_response

    with (
        patch("primer.server.services.slack_service.settings") as mock_settings,
        patch(
            "primer.server.services.slack_service.httpx.Client",
            return_value=mock_client_instance,
        ),
    ):
        mock_settings.slack_alerts_enabled = True
        mock_settings.slack_webhook_url = "https://hooks.slack.com/services/test"

        from primer.server.services.slack_service import send_alert_to_slack

        send_alert_to_slack(alert)

        mock_client_instance.post.assert_called_once()
        call_args = mock_client_instance.post.call_args
        assert call_args[0][0] == "https://hooks.slack.com/services/test"
        payload = call_args[1]["json"]
        assert "attachments" in payload
        assert payload["attachments"][0]["color"] == "#dc2626"  # critical


def test_slack_failure_does_not_raise(db_session):
    """Slack errors are logged but never propagated."""
    alert = Alert(
        alert_type="usage_drop",
        severity="warning",
        title="Usage drop",
        message="Drop detected",
        metric_name="daily_sessions",
    )
    db_session.add(alert)
    db_session.flush()

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)
    mock_client_instance.post.side_effect = Exception("Connection refused")

    with (
        patch("primer.server.services.slack_service.settings") as mock_settings,
        patch(
            "primer.server.services.slack_service.httpx.Client",
            return_value=mock_client_instance,
        ),
    ):
        mock_settings.slack_alerts_enabled = True
        mock_settings.slack_webhook_url = "https://hooks.slack.com/services/bad"

        from primer.server.services.slack_service import send_alert_to_slack

        # Should not raise
        send_alert_to_slack(alert)


def test_slack_config_requires_admin(client, engineer_with_key):
    _eng, api_key = engineer_with_key
    r = client.get("/api/v1/notifications/slack", headers={"x-api-key": api_key})
    assert r.status_code == 403


def test_slack_config_returns_state(client, admin_headers):
    r = client.get("/api/v1/notifications/slack", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "webhook_url_set" in data
    assert "enabled" in data
    assert data["enabled"] is False  # default
