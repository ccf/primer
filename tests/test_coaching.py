"""Tests for the coaching brief endpoint."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from primer.common.models import Session as SessionModel
from primer.common.models import SessionFacets, ToolUsage


def test_coaching_requires_engineer_key(client, admin_headers):
    """Admin keys can't get a coaching brief — need engineer context."""
    resp = client.get("/api/v1/analytics/coaching", headers=admin_headers)
    assert resp.status_code == 400
    assert "engineer context" in resp.json()["detail"]


def test_coaching_empty(client, engineer_with_key):
    """Coaching brief with no sessions returns valid structure."""
    _eng, key = engineer_with_key
    resp = client.get("/api/v1/analytics/coaching", headers={"x-api-key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert "status_summary" in data
    assert "sections" in data
    assert isinstance(data["sections"], list)
    assert data["sessions_analyzed"] == 0


def test_coaching_with_sessions(client, db_session, engineer_with_key):
    """Coaching brief with session data returns populated sections."""
    eng, key = engineer_with_key

    # Create sessions with tool usage and facets
    for i in range(5):
        s = SessionModel(
            id=str(uuid.uuid4()),
            engineer_id=eng.id,
            started_at=datetime.now(tz=UTC),
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=200,
        )
        db_session.add(s)
        db_session.flush()

        db_session.add(ToolUsage(session_id=s.id, tool_name="Read", call_count=10))
        db_session.add(ToolUsage(session_id=s.id, tool_name="Bash", call_count=5))
        db_session.flush()

        db_session.add(
            SessionFacets(
                session_id=s.id,
                outcome="full" if i < 3 else "partial",
                friction_counts={"permission_denied": 1} if i == 0 else {},
            )
        )
        db_session.flush()

    resp = client.get("/api/v1/analytics/coaching", headers={"x-api-key": key})
    assert resp.status_code == 200
    data = resp.json()

    assert data["sessions_analyzed"] == 5
    assert len(data["sections"]) == 3  # friction, skills, recommendations
    assert data["sections"][0]["title"] == "What's slowing you down"
    assert data["sections"][1]["title"] == "Where you could level up"
    assert data["sections"][2]["title"] == "Top recommendations"

    # Each section should have at least one item
    for section in data["sections"]:
        assert len(section["items"]) >= 1


def test_coaching_days_param(client, engineer_with_key):
    """Custom days parameter is accepted."""
    _eng, key = engineer_with_key
    resp = client.get(
        "/api/v1/analytics/coaching",
        params={"days": 7},
        headers={"x-api-key": key},
    )
    assert resp.status_code == 200


def test_session_start_coaching_requires_engineer_key(client, admin_headers):
    resp = client.get("/api/v1/analytics/coaching/session-start", headers=admin_headers)
    assert resp.status_code == 400
    assert "engineer context" in resp.json()["detail"]


def test_session_start_coaching_with_context(client, engineer_with_key, monkeypatch):
    _eng, key = engineer_with_key

    monkeypatch.setattr(
        "primer.server.services.engineer_profile_service.get_engineer_profile",
        lambda *args, **kwargs: SimpleNamespace(
            overview=SimpleNamespace(total_sessions=12, success_rate=0.83),
            workflow_playbooks=[
                SimpleNamespace(
                    title="Debugging: Read -> Test -> Fix",
                    session_type="debugging",
                    example_projects=["api-server"],
                    recommended_tools=["Read", "Bash"],
                    summary="Reproduce the bug quickly and keep the loop tight.",
                )
            ],
            model_recommendations=[
                SimpleNamespace(
                    workflow_archetype="debugging",
                    title="Use Sonnet for debugging work",
                    description="Peers keep similar success while spending less.",
                )
            ],
            tool_recommendations=[
                SimpleNamespace(
                    title="Lean on grep before edits",
                    description="Use search to narrow the failing path before you patch.",
                    matching_projects=["api-server"],
                    project_context_match_count=1,
                )
            ],
            learning_paths=[
                SimpleNamespace(
                    recommendations=[
                        SimpleNamespace(
                            title="Reuse the failing-test prompt",
                            description="Start from the prompt that reproduces the auth failure.",
                        )
                    ]
                )
            ],
            config_suggestions=[
                SimpleNamespace(
                    title="Check GitHub MCP availability",
                    description="GitHub lookups are more reliable once the MCP is connected.",
                )
            ],
        ),
    )
    monkeypatch.setattr(
        "primer.server.services.project_workspace_service.get_project_workspace",
        lambda *args, **kwargs: SimpleNamespace(
            enablement=SimpleNamespace(
                recommendations=[
                    SimpleNamespace(
                        title="Run the fastest verification loop first",
                        description="Start with the auth regression test before broad edits.",
                    )
                ],
                permission_mode_counts={"default": 4},
            ),
            workflow_summary=SimpleNamespace(
                friction_hotspots=[
                    SimpleNamespace(
                        friction_type="tool_error",
                        session_count=5,
                    )
                ]
            ),
        ),
    )

    resp = client.get(
        "/api/v1/analytics/coaching/session-start",
        params={
            "project_name": "api-server",
            "workflow_hint": "debugging",
            "task_hint": "Fix auth regression",
        },
        headers={"x-api-key": key},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["brief_type"] == "session_start"
    assert "Project: api-server" in data["context_summary"]
    assert "Workflow: debugging" in data["context_summary"]
    assert len(data["sections"]) == 3
    assert data["sections"][0]["title"] == "How to start this session"
    assert any("Debugging: Read -> Test -> Fix" in item for item in data["sections"][0]["items"])
    assert any("Use Sonnet for debugging work" in item for item in data["sections"][1]["items"])
    assert any("tool_error" in item for item in data["sections"][2]["items"])


def test_session_start_coaching_matches_hyphenated_workflow_hints(
    client, engineer_with_key, monkeypatch
):
    _eng, key = engineer_with_key

    monkeypatch.setattr(
        "primer.server.services.engineer_profile_service.get_engineer_profile",
        lambda *args, **kwargs: SimpleNamespace(
            overview=SimpleNamespace(total_sessions=8, success_rate=0.75),
            workflow_playbooks=[
                SimpleNamespace(
                    title="Feature-delivery: Read -> Edit -> Ship",
                    session_type="feature-delivery",
                    example_projects=[],
                    recommended_tools=["Edit"],
                    summary="Ship the smallest viable change first.",
                )
            ],
            model_recommendations=[
                SimpleNamespace(
                    workflow_archetype="feature-delivery",
                    title="Use Sonnet for feature-delivery work",
                    description="Peers keep quality while spending less.",
                )
            ],
            tool_recommendations=[],
            learning_paths=[],
            config_suggestions=[],
        ),
    )
    monkeypatch.setattr(
        "primer.server.services.project_workspace_service.get_project_workspace",
        lambda *args, **kwargs: None,
    )

    resp = client.get(
        "/api/v1/analytics/coaching/session-start",
        params={"workflow_hint": "feature-delivery"},
        headers={"x-api-key": key},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert any(
        "Feature-delivery: Read -> Edit -> Ship" in item for item in data["sections"][0]["items"]
    )
    assert any(
        "Use Sonnet for feature-delivery work" in item for item in data["sections"][1]["items"]
    )
