import secrets
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import bcrypt

from primer.common.models import Alert, Engineer, NarrativeCache, Team
from primer.common.schemas import NextStepPlanResponse
from primer.server.services.next_step_plan_service import get_next_step_plan


def _make_engineer(
    db_session, team: Team, *, name: str, role: str = "engineer"
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


def test_get_next_step_plan_combines_alerts_narratives_and_project_findings(
    monkeypatch, db_session
):
    team = Team(name="Platform")
    db_session.add(team)
    db_session.flush()
    db_session.add(
        Alert(
            team_id=team.id,
            alert_type="friction_spike",
            severity="warning",
            title="Friction spike detected",
            message="tool errors jumped sharply this week",
            metric_name="friction_count",
            expected_value=2.0,
            actual_value=7.0,
            threshold=4.0,
            detected_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=14)
    db_session.add(
        NarrativeCache(
            id=str(uuid4()),
            scope="team",
            scope_id=team.id,
            date_range_key=f"{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}",
            sections=[
                {
                    "title": "Recommendations",
                    "content": "Standardize the debugging playbook and reduce tool retries.",
                }
            ],
            model_used="claude-sonnet-4-6",
            data_summary={},
            prompt_tokens=0,
            completion_tokens=0,
            created_at=end_date,
            expires_at=end_date + timedelta(hours=24),
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        "primer.server.services.next_step_plan_service.get_project_workspace",
        lambda *args, **kwargs: SimpleNamespace(
            enablement=SimpleNamespace(
                recommendations=[
                    SimpleNamespace(
                        title="Codify the debugging playbook",
                        description="Document the fastest recovery path for this repo.",
                        severity="warning",
                        category="workflow",
                        evidence={"fingerprint": "debugging"},
                    )
                ]
            )
        ),
    )
    monkeypatch.setattr(
        "primer.server.services.next_step_plan_service.get_recommendations",
        lambda *args, **kwargs: [
            SimpleNamespace(
                title="Reduce tool retries",
                description="Switch to the fallback path after repeated tool errors.",
                category="friction",
                severity="warning",
                evidence={"friction_type": "tool_error"},
            )
        ],
    )

    plan = get_next_step_plan(
        db_session,
        team_id=team.id,
        project_name="primer",
        start_date=start_date,
        end_date=end_date,
        days=14,
    )

    assert plan.scope_label == "primer"
    assert len(plan.actions) >= 3
    assert plan.actions[0].source_type == "alert"
    assert any(action.source_type == "project_finding" for action in plan.actions)
    assert any(action.source_type == "narrative" for action in plan.actions)
    assert any(action.source_type == "recommendation" for action in plan.actions)


def test_next_step_plan_route_scopes_team_lead_to_their_team(client, db_session, monkeypatch):
    team = Team(name="Lead Team")
    other_team = Team(name="Other Team")
    db_session.add_all([team, other_team])
    db_session.flush()
    _lead, lead_key = _make_engineer(db_session, team, name="Lead", role="team_lead")
    db_session.commit()

    captured: dict[str, str | None] = {}

    def fake_plan(
        db, *, team_id=None, project_name=None, start_date=None, end_date=None, days=14, limit=5
    ):
        captured["team_id"] = team_id
        return NextStepPlanResponse(
            scope_label="Lead Team",
            summary=(
                "1 next-step action synthesized from recent alerts, narratives, "
                "and project findings."
            ),
            generated_at="2026-03-27T00:00:00Z",
            actions=[],
        )

    monkeypatch.setattr(
        "primer.server.services.next_step_plan_service.get_next_step_plan",
        fake_plan,
    )

    resp = client.get(
        "/api/v1/interventions/next-step-plan",
        params={"team_id": other_team.id},
        headers={"x-api-key": lead_key},
    )

    assert resp.status_code == 200
    assert captured["team_id"] == team.id


def test_next_step_plan_route_blocks_engineer_scope(client, engineer_with_key):
    _engineer, key = engineer_with_key

    resp = client.get("/api/v1/interventions/next-step-plan", headers={"x-api-key": key})

    assert resp.status_code == 403
