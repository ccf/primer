def test_create_engineer_audit(client, admin_headers):
    """Creating an engineer should create an audit log entry."""
    client.post(
        "/api/v1/engineers",
        json={"name": "Audit Test", "email": "audit@example.com"},
        headers=admin_headers,
    )
    resp = client.get(
        "/api/v1/admin/audit-logs",
        params={"resource_type": "engineer", "action": "create"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    logs = resp.json()
    assert any(log["action"] == "create" and log["resource_type"] == "engineer" for log in logs)


def test_update_engineer_audit(client, admin_headers, db_session):
    """Updating an engineer should create an audit log entry with changes."""
    from primer.common.models import Engineer

    eng = db_session.query(Engineer).first()
    if not eng:
        # Create one first
        create_resp = client.post(
            "/api/v1/engineers",
            json={"name": "Update Test", "email": "update-audit@example.com"},
            headers=admin_headers,
        )
        eng_id = create_resp.json()["engineer"]["id"]
    else:
        eng_id = eng.id

    client.patch(
        f"/api/v1/engineers/{eng_id}",
        json={"role": "team_lead"},
        headers=admin_headers,
    )
    resp = client.get(
        "/api/v1/admin/audit-logs",
        params={"resource_type": "engineer", "action": "update"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    logs = resp.json()
    assert any(log["action"] == "update" and log["resource_type"] == "engineer" for log in logs)


def test_create_team_audit(client, admin_headers):
    """Creating a team should create an audit log entry."""
    client.post(
        "/api/v1/teams",
        json={"name": "Audit Team"},
        headers=admin_headers,
    )
    resp = client.get(
        "/api/v1/admin/audit-logs",
        params={"resource_type": "team", "action": "create"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    logs = resp.json()
    assert any(log["action"] == "create" and log["resource_type"] == "team" for log in logs)


def test_alert_config_audit(client, admin_headers):
    """CRUD on alert configs should create audit entries."""
    # Create
    create_resp = client.post(
        "/api/v1/alert-configs",
        json={"alert_type": "friction_spike", "threshold": 3.0},
        headers=admin_headers,
    )
    config_id = create_resp.json()["id"]

    # Update
    client.patch(
        f"/api/v1/alert-configs/{config_id}",
        json={"threshold": 4.0},
        headers=admin_headers,
    )

    # Delete
    client.delete(f"/api/v1/alert-configs/{config_id}", headers=admin_headers)

    resp = client.get(
        "/api/v1/admin/audit-logs",
        params={"resource_type": "alert_config"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    logs = resp.json()
    actions = [log["action"] for log in logs]
    assert "create" in actions
    assert "update" in actions
    assert "delete" in actions


def test_audit_filter_by_resource_type(client, admin_headers):
    resp = client.get(
        "/api/v1/admin/audit-logs",
        params={"resource_type": "team"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    for log in resp.json():
        assert log["resource_type"] == "team"


def test_audit_filter_by_action(client, admin_headers):
    resp = client.get(
        "/api/v1/admin/audit-logs",
        params={"action": "create"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    for log in resp.json():
        assert log["action"] == "create"


def test_audit_admin_only(client):
    resp = client.get("/api/v1/admin/audit-logs")
    assert resp.status_code in (401, 403, 422)
