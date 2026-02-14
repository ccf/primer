import uuid
from datetime import UTC, datetime

from primer.common.models import Alert


def _ingest_session(client, api_key, **kwargs):
    session_id = kwargs.pop("session_id", str(uuid.uuid4()))
    payload = {
        "session_id": session_id,
        "api_key": api_key,
        "message_count": 10,
        "user_message_count": 5,
        "assistant_message_count": 5,
        "tool_call_count": 3,
        "input_tokens": 1000,
        "output_tokens": 500,
        "duration_seconds": 120.0,
        **kwargs,
    }
    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 200
    return session_id


def test_alerts_empty(client, admin_headers):
    r = client.get("/api/v1/alerts", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_detect_requires_admin(client, engineer_with_key):
    _eng, api_key = engineer_with_key
    r = client.post(
        "/api/v1/alerts/detect",
        headers={"x-api-key": api_key},
    )
    assert r.status_code == 403


def test_detect_returns_result(client, admin_headers):
    r = client.post("/api/v1/alerts/detect", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "alerts_created" in data
    assert "alert_ids" in data


def test_acknowledge_alert(client, db_session, admin_headers):
    alert = Alert(
        team_id=None,
        engineer_id=None,
        alert_type="cost_spike",
        severity="warning",
        title="Test alert",
        message="This is a test",
        metric_name="daily_cost",
    )
    db_session.add(alert)
    db_session.flush()
    alert_id = alert.id

    r = client.patch(f"/api/v1/alerts/{alert_id}/acknowledge", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["acknowledged_at"] is not None


def test_dismiss_alert(client, db_session, admin_headers):
    alert = Alert(
        team_id=None,
        engineer_id=None,
        alert_type="usage_drop",
        severity="warning",
        title="Test dismiss",
        message="This is a test",
        metric_name="daily_sessions",
    )
    db_session.add(alert)
    db_session.flush()
    alert_id = alert.id

    r = client.patch(f"/api/v1/alerts/{alert_id}/dismiss", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["dismissed"] is True

    # Dismissed alerts should not appear by default
    r = client.get("/api/v1/alerts", headers=admin_headers)
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    assert alert_id not in ids


def test_acknowledge_not_found(client, admin_headers):
    r = client.patch("/api/v1/alerts/nonexistent/acknowledge", headers=admin_headers)
    assert r.status_code == 404


def test_dedup_alerts(db_session, client, admin_headers):
    """Alerts of the same type within 24h should not duplicate."""
    # Create a recent alert
    alert = Alert(
        team_id=None,
        engineer_id=None,
        alert_type="friction_spike",
        severity="warning",
        title="Existing friction alert",
        message="Already exists",
        metric_name="friction_count",
        detected_at=datetime.now(UTC),
    )
    db_session.add(alert)
    db_session.flush()

    # Trigger detection — should not create another friction_spike
    r = client.post("/api/v1/alerts/detect", headers=admin_headers)
    assert r.status_code == 200
    r.json()
    # The friction_spike detector should be deduped
    friction_alerts = (
        db_session.query(Alert)
        .filter(Alert.alert_type == "friction_spike", Alert.dismissed == False)  # noqa: E712
        .all()
    )
    assert len(friction_alerts) == 1
