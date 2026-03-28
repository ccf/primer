from primer.common.config import settings


def test_create_alert_config(client, admin_headers):
    resp = client.post(
        "/api/v1/alert-configs",
        json={"alert_type": "friction_spike", "threshold": 3.0},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["alert_type"] == "friction_spike"
    assert data["threshold"] == 3.0
    assert data["enabled"] is True
    assert data["team_id"] is None


def test_create_alert_config_duplicate(client, admin_headers):
    client.post(
        "/api/v1/alert-configs",
        json={"alert_type": "usage_drop", "threshold": 0.3},
        headers=admin_headers,
    )
    resp = client.post(
        "/api/v1/alert-configs",
        json={"alert_type": "usage_drop", "threshold": 0.4},
        headers=admin_headers,
    )
    assert resp.status_code == 409


def test_create_alert_config_invalid_type(client, admin_headers):
    resp = client.post(
        "/api/v1/alert-configs",
        json={"alert_type": "invalid_type", "threshold": 1.0},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_list_alert_configs(client, admin_headers):
    client.post(
        "/api/v1/alert-configs",
        json={"alert_type": "cost_spike_warning", "threshold": 2.5},
        headers=admin_headers,
    )
    resp = client.get("/api/v1/alert-configs", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_update_alert_config(client, admin_headers):
    create_resp = client.post(
        "/api/v1/alert-configs",
        json={"alert_type": "cost_spike_critical", "threshold": 4.0},
        headers=admin_headers,
    )
    config_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/alert-configs/{config_id}",
        json={"threshold": 5.0, "enabled": False},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["threshold"] == 5.0
    assert resp.json()["enabled"] is False


def test_delete_alert_config(client, admin_headers):
    create_resp = client.post(
        "/api/v1/alert-configs",
        json={"alert_type": "success_rate_drop", "threshold": 15.0},
        headers=admin_headers,
    )
    config_id = create_resp.json()["id"]

    resp = client.delete(f"/api/v1/alert-configs/{config_id}", headers=admin_headers)
    assert resp.status_code == 204


def test_resolve_thresholds_defaults(client, admin_headers):
    resp = client.get("/api/v1/alert-configs/resolved", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["friction_spike_multiplier"] == settings.alert_friction_spike_multiplier
    assert data["usage_drop_ratio"] == settings.alert_usage_drop_ratio
    assert data["cost_spike_warning"] == settings.alert_cost_spike_warning
    assert data["cost_spike_critical"] == settings.alert_cost_spike_critical
    assert data["success_rate_drop_pp"] == settings.alert_success_rate_drop_pp


def test_resolve_thresholds_with_override(client, admin_headers):
    client.post(
        "/api/v1/alert-configs",
        json={"alert_type": "friction_spike", "threshold": 5.0},
        headers=admin_headers,
    )
    resp = client.get("/api/v1/alert-configs/resolved", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["friction_spike_multiplier"] == 5.0


def test_resolve_policy_defaults(client, admin_headers):
    resp = client.get("/api/v1/alert-configs/policy", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["notifications_enabled"] is False
    assert data["webhook_configured"] is False
    friction = next(item for item in data["policies"] if item["alert_type"] == "friction_spike")
    assert friction["source"] == "default"
    assert friction["effective_enabled"] is True
    assert friction["effective_threshold"] == settings.alert_friction_spike_multiplier


def test_resolve_policy_team_override_and_disable(client, admin_headers):
    create_global = client.post(
        "/api/v1/alert-configs",
        json={"alert_type": "friction_spike", "threshold": 4.0, "enabled": False},
        headers=admin_headers,
    )
    assert create_global.status_code == 201
    create_team = client.post(
        "/api/v1/alert-configs",
        json={
            "team_id": "team-123",
            "alert_type": "friction_spike",
            "threshold": 5.0,
            "enabled": True,
        },
        headers=admin_headers,
    )
    assert create_team.status_code == 201

    global_policy = client.get("/api/v1/alert-configs/policy", headers=admin_headers)
    team_policy = client.get(
        "/api/v1/alert-configs/policy?team_id=team-123",
        headers=admin_headers,
    )

    assert global_policy.status_code == 200
    assert team_policy.status_code == 200

    global_friction = next(
        item for item in global_policy.json()["policies"] if item["alert_type"] == "friction_spike"
    )
    team_friction = next(
        item for item in team_policy.json()["policies"] if item["alert_type"] == "friction_spike"
    )

    assert global_friction["source"] == "global_disabled"
    assert global_friction["effective_enabled"] is False
    assert team_friction["source"] == "team_override"
    assert team_friction["effective_enabled"] is True
    assert team_friction["effective_threshold"] == 5.0


def test_admin_only_access(client):
    resp = client.get("/api/v1/alert-configs")
    assert resp.status_code in (401, 403, 422)
