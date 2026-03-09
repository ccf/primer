import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt

from primer.common.models import Engineer, Team


def _make_engineer(
    db_session,
    team: Team,
    *,
    name: str,
    role: str = "engineer",
) -> tuple[Engineer, str]:
    raw_key = f"primer_{secrets.token_urlsafe(32)}"
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    engineer = Engineer(
        name=name,
        email=f"{name.lower().replace(' ', '.')}@example.com",
        team_id=team.id,
        api_key_hash=hashed,
        role=role,
    )
    db_session.add(engineer)
    db_session.flush()
    return engineer, raw_key


def _ingest_measured_session(client, api_key: str, *, project_name: str | None = None):
    now = datetime.now(UTC)
    response = client.post(
        "/api/v1/ingest/session",
        json={
            "session_id": str(uuid4()),
            "api_key": api_key,
            "project_name": project_name,
            "started_at": (now - timedelta(days=2)).isoformat(),
            "ended_at": (now - timedelta(days=2, minutes=-20)).isoformat(),
            "duration_seconds": 1200,
            "message_count": 2,
            "user_message_count": 1,
            "assistant_message_count": 1,
            "tool_call_count": 2,
            "input_tokens": 1200,
            "output_tokens": 600,
            "primary_model": "claude-sonnet-4-5-20250929",
            "messages": [
                {"ordinal": 1, "role": "human", "content_text": "Please fix the failing tests"},
                {
                    "ordinal": 2,
                    "role": "assistant",
                    "content_text": "I fixed them.",
                    "model": "claude-sonnet-4-5-20250929",
                    "token_count": 200,
                },
            ],
            "model_usages": [
                {
                    "model_name": "claude-sonnet-4-5-20250929",
                    "input_tokens": 1200,
                    "output_tokens": 600,
                }
            ],
            "tool_usages": [{"tool_name": "Edit", "call_count": 2}],
            "facets": {
                "outcome": "success",
                "session_type": "implementation",
                "primary_success": "complete",
                "friction_counts": {"context_switching": 1},
                "friction_detail": "Needed to reconcile failing tests with a migration change.",
            },
        },
    )
    assert response.status_code == 200


def test_engineer_can_create_intervention_with_metrics(client, engineer_with_key):
    engineer, api_key = engineer_with_key
    _ingest_measured_session(client, api_key, project_name="alpha")

    response = client.post(
        "/api/v1/interventions",
        headers={"x-api-key": api_key},
        json={
            "title": "Reduce context switching",
            "description": "Add a tighter triage checklist before implementation sessions.",
            "category": "friction",
            "severity": "warning",
            "project_name": "alpha",
            "source_type": "recommendation",
            "source_title": "Recurring friction: context_switching",
            "evidence": {"friction_type": "context_switching", "count": 1},
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["team_id"] == engineer.team_id
    assert data["engineer_id"] == engineer.id
    assert data["owner_engineer_id"] == engineer.id
    assert data["baseline_metrics"]["total_sessions"] == 1
    assert data["baseline_metrics"]["success_rate"] == 1.0
    assert data["baseline_metrics"]["friction_events"] == 1
    assert data["current_metrics"]["total_sessions"] == 1
    assert data["source_type"] == "recommendation"


def test_engineer_only_sees_assigned_or_targeted_interventions(
    client, admin_headers, engineer_with_key, db_session
):
    engineer, api_key = engineer_with_key
    other_team = Team(name="Other Team")
    db_session.add(other_team)
    db_session.flush()
    other_engineer, _other_key = _make_engineer(db_session, other_team, name="Other Engineer")
    db_session.commit()

    client.post(
        "/api/v1/interventions",
        headers=admin_headers,
        json={
            "title": "Help test engineer",
            "description": "Assigned to the engineer in scope.",
            "category": "workflow",
            "engineer_id": engineer.id,
            "owner_engineer_id": engineer.id,
        },
    )
    client.post(
        "/api/v1/interventions",
        headers=admin_headers,
        json={
            "title": "Other team intervention",
            "description": "Should not be visible to the first engineer.",
            "category": "workflow",
            "engineer_id": other_engineer.id,
            "owner_engineer_id": other_engineer.id,
        },
    )

    response = client.get("/api/v1/interventions", headers={"x-api-key": api_key})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["engineer_id"] == engineer.id


def test_team_lead_cannot_create_intervention_for_other_team(client, db_session):
    team_a = Team(name="Team A")
    team_b = Team(name="Team B")
    db_session.add_all([team_a, team_b])
    db_session.flush()
    lead, lead_key = _make_engineer(db_session, team_a, name="Lead", role="team_lead")
    other_engineer, _other_key = _make_engineer(db_session, team_b, name="Elsewhere")
    db_session.commit()

    response = client.post(
        "/api/v1/interventions",
        headers={"x-api-key": lead_key},
        json={
            "title": "Cross-team coaching",
            "description": "This should be blocked.",
            "category": "coaching",
            "engineer_id": other_engineer.id,
            "owner_engineer_id": lead.id,
        },
    )

    assert response.status_code == 403


def test_team_lead_patch_keeps_org_scoped_intervention_when_team_id_is_omitted(
    client, db_session, admin_headers
):
    team = Team(name="Lead Team")
    db_session.add(team)
    db_session.flush()
    lead, lead_key = _make_engineer(db_session, team, name="Lead", role="team_lead")
    engineer, _engineer_key = _make_engineer(db_session, team, name="Engineer")
    db_session.commit()

    created = client.post(
        "/api/v1/interventions",
        headers=admin_headers,
        json={
            "title": "Org-scoped intervention",
            "description": "Should remain org scoped when a lead updates status only.",
            "category": "workflow",
            "engineer_id": engineer.id,
            "owner_engineer_id": lead.id,
            "team_id": None,
        },
    )
    assert created.status_code == 201
    intervention_id = created.json()["id"]
    assert created.json()["team_id"] is None

    patched = client.patch(
        f"/api/v1/interventions/{intervention_id}",
        headers={"x-api-key": lead_key},
        json={"status": "in_progress"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "in_progress"
    assert patched.json()["team_id"] is None


def test_engineer_patch_is_limited_to_workflow_fields(client, admin_headers, engineer_with_key):
    engineer, api_key = engineer_with_key
    created = client.post(
        "/api/v1/interventions",
        headers=admin_headers,
        json={
            "title": "Close the feedback loop",
            "description": "Track the recommendation to completion.",
            "category": "workflow",
            "engineer_id": engineer.id,
            "owner_engineer_id": engineer.id,
        },
    )
    intervention_id = created.json()["id"]

    update_response = client.patch(
        f"/api/v1/interventions/{intervention_id}",
        headers={"x-api-key": api_key},
        json={"status": "completed"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "completed"
    assert update_response.json()["completed_at"] is not None

    forbidden = client.patch(
        f"/api/v1/interventions/{intervention_id}",
        headers={"x-api-key": api_key},
        json={"title": "Engineers should not retitle interventions"},
    )
    assert forbidden.status_code == 403


def test_engineer_patch_cannot_clear_owner_assignment(client, admin_headers, engineer_with_key):
    engineer, api_key = engineer_with_key
    created = client.post(
        "/api/v1/interventions",
        headers=admin_headers,
        json={
            "title": "Keep ownership intact",
            "description": "Engineers should not be able to unassign ownership.",
            "category": "workflow",
            "engineer_id": engineer.id,
            "owner_engineer_id": engineer.id,
        },
    )
    intervention_id = created.json()["id"]

    forbidden = client.patch(
        f"/api/v1/interventions/{intervention_id}",
        headers={"x-api-key": api_key},
        json={"owner_engineer_id": None},
    )
    assert forbidden.status_code == 403


def test_recommendations_endpoint_accepts_engineer_scope_for_team_leads(client, db_session):
    team = Team(name="Scoped Team")
    db_session.add(team)
    db_session.flush()
    _lead, lead_key = _make_engineer(db_session, team, name="Scoped Lead", role="team_lead")
    eng_one, key_one = _make_engineer(db_session, team, name="Engineer One")
    _eng_two, key_two = _make_engineer(db_session, team, name="Engineer Two")
    db_session.commit()

    for _ in range(5):
        _ingest_measured_session(client, key_one, project_name="scoped")
    _ingest_measured_session(client, key_two, project_name="quiet")

    response = client.get(
        "/api/v1/analytics/recommendations",
        headers={"x-api-key": lead_key},
        params={"engineer_id": eng_one.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert any(item["category"] == "friction" for item in data)


def test_intervention_list_skips_expensive_current_metrics_computation(client, engineer_with_key):
    _engineer, api_key = engineer_with_key
    _ingest_measured_session(client, api_key, project_name="alpha")

    created = client.post(
        "/api/v1/interventions",
        headers={"x-api-key": api_key},
        json={
            "title": "Track alpha improvements",
            "description": "Use the intervention list without recomputing current metrics.",
            "category": "workflow",
            "project_name": "alpha",
        },
    )
    assert created.status_code == 201
    assert created.json()["current_metrics"] is not None

    listed = client.get("/api/v1/interventions", headers={"x-api-key": api_key})
    assert listed.status_code == 200
    data = listed.json()
    assert len(data) == 1
    assert data[0]["baseline_metrics"] is not None
    assert data[0]["current_metrics"] is None
