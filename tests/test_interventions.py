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


def _ingest_measured_session(
    client,
    api_key: str,
    *,
    project_name: str | None = None,
    started_at: datetime | None = None,
    duration_seconds: int = 1200,
    outcome: str = "success",
    friction_events: int = 1,
    input_tokens: int = 1200,
    output_tokens: int = 600,
):
    start = started_at or (datetime.now(UTC) - timedelta(days=2))
    end = start + timedelta(seconds=duration_seconds)
    response = client.post(
        "/api/v1/ingest/session",
        json={
            "session_id": str(uuid4()),
            "api_key": api_key,
            "project_name": project_name,
            "started_at": start.isoformat(),
            "ended_at": end.isoformat(),
            "duration_seconds": duration_seconds,
            "message_count": 2,
            "user_message_count": 1,
            "assistant_message_count": 1,
            "tool_call_count": 2,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
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
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                }
            ],
            "tool_usages": [{"tool_name": "Edit", "call_count": 2}],
            "facets": {
                "outcome": outcome,
                "session_type": "implementation",
                "primary_success": "complete" if outcome == "success" else "blocked",
                "friction_counts": (
                    {"context_switching": friction_events} if friction_events else {}
                ),
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


def test_intervention_effectiveness_endpoint_groups_by_scope_and_cohort(client, engineer_with_key):
    engineer, api_key = engineer_with_key
    now = datetime.now(UTC)
    baseline_end = now - timedelta(days=120)
    baseline_start = baseline_end - timedelta(days=30)

    _ingest_measured_session(
        client,
        api_key,
        project_name="alpha",
        started_at=now - timedelta(days=135),
        outcome="failure",
        friction_events=5,
        input_tokens=3600,
        output_tokens=1800,
    )
    _ingest_measured_session(
        client,
        api_key,
        project_name="alpha",
        started_at=now - timedelta(days=5),
        outcome="success",
        friction_events=1,
        input_tokens=600,
        output_tokens=300,
    )

    created = client.post(
        "/api/v1/interventions",
        headers={"x-api-key": api_key},
        json={
            "title": "Stabilize implementation workflow",
            "description": "Measure whether the new triage checklist reduced friction.",
            "category": "workflow",
            "project_name": "alpha",
            "status": "completed",
            "baseline_start_at": baseline_start.isoformat(),
            "baseline_end_at": baseline_end.isoformat(),
        },
    )
    assert created.status_code == 201

    response = client.get("/api/v1/interventions/effectiveness", headers={"x-api-key": api_key})
    assert response.status_code == 200
    data = response.json()

    assert data["summary"]["total_interventions"] == 1
    assert data["summary"]["completed_interventions"] == 1
    assert data["summary"]["measured_interventions"] == 1
    assert data["summary"]["improved_interventions"] == 1
    assert data["summary"]["improvement_rate"] == 1.0
    assert data["summary"]["avg_success_rate_delta"] == 1.0
    assert data["summary"]["avg_friction_delta"] == 4.0
    assert data["summary"]["avg_cost_per_session_delta"] is not None

    assert data["by_project"][0]["key"] == "alpha"
    assert data["by_project"][0]["improvement_rate"] == 1.0
    assert data["by_team"][0]["key"] == engineer.team_id
    assert data["by_team"][0]["label"] == "Test Team"
    assert data["by_engineer_cohort"][0]["key"] == "experienced"


def test_team_lead_lists_and_reports_org_scoped_team_interventions(
    client, db_session, admin_headers
):
    team = Team(name="Lead Team")
    db_session.add(team)
    db_session.flush()
    lead, lead_key = _make_engineer(db_session, team, name="Lead", role="team_lead")
    engineer, engineer_key = _make_engineer(db_session, team, name="Engineer")
    db_session.commit()

    now = datetime.now(UTC)
    baseline_end = now - timedelta(days=60)
    baseline_start = baseline_end - timedelta(days=30)
    _ingest_measured_session(
        client,
        engineer_key,
        project_name="primer",
        started_at=now - timedelta(days=75),
        outcome="failure",
        friction_events=3,
    )
    _ingest_measured_session(
        client,
        engineer_key,
        project_name="primer",
        started_at=now - timedelta(days=3),
        outcome="success",
        friction_events=0,
    )

    created = client.post(
        "/api/v1/interventions",
        headers=admin_headers,
        json={
            "title": "Org scoped but team relevant",
            "description": (
                "Should remain visible to the team lead because the target engineer is on the team."
            ),
            "category": "workflow",
            "engineer_id": engineer.id,
            "owner_engineer_id": lead.id,
            "team_id": None,
            "status": "completed",
            "project_name": "primer",
            "baseline_start_at": baseline_start.isoformat(),
            "baseline_end_at": baseline_end.isoformat(),
        },
    )
    assert created.status_code == 201
    intervention_id = created.json()["id"]

    listed = client.get("/api/v1/interventions", headers={"x-api-key": lead_key})
    assert listed.status_code == 200
    assert any(item["id"] == intervention_id for item in listed.json())

    report = client.get("/api/v1/interventions/effectiveness", headers={"x-api-key": lead_key})
    assert report.status_code == 200
    report_data = report.json()
    assert report_data["summary"]["total_interventions"] == 1
    assert report_data["summary"]["completed_interventions"] == 1
    assert report_data["by_team"][0]["label"] == "Lead Team"
