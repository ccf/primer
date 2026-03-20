import uuid
from datetime import UTC, datetime, timedelta

import pytest

from primer.common.models import (
    Engineer,
    GitRepository,
    ModelUsage,
    PullRequest,
    Session,
    SessionCommit,
    SessionCustomization,
    SessionFacets,
    SessionMessage,
    SessionRecoveryPath,
    SessionWorkflowProfile,
    Team,
    ToolUsage,
)


@pytest.fixture()
def seeded_maturity_data(db_session):
    """Create team, engineers, sessions with diverse tool usage for maturity tests."""
    team = Team(name="maturity-team")
    db_session.add(team)
    db_session.flush()

    eng1 = Engineer(
        name="Alice",
        email="alice@test.com",
        team_id=team.id,
        api_key_hash="x",
    )
    eng2 = Engineer(
        name="Bob",
        email="bob@test.com",
        team_id=team.id,
        api_key_hash="x",
    )
    db_session.add_all([eng1, eng2])
    db_session.flush()

    now = datetime.now(tz=UTC)
    # Alice: uses orchestration + diverse tools
    s1 = Session(
        id=str(uuid.uuid4()),
        engineer_id=eng1.id,
        started_at=now - timedelta(days=1),
        input_tokens=1000,
        cache_read_tokens=500,
    )
    # Bob: core tools only
    s2 = Session(
        id=str(uuid.uuid4()),
        engineer_id=eng2.id,
        started_at=now - timedelta(days=2),
        input_tokens=800,
        cache_read_tokens=100,
    )
    db_session.add_all([s1, s2])
    db_session.flush()

    # Alice's tools: orchestration + search + core + skill
    tools_s1 = [
        ToolUsage(session_id=s1.id, tool_name="Read", call_count=10),
        ToolUsage(session_id=s1.id, tool_name="Glob", call_count=5),
        ToolUsage(session_id=s1.id, tool_name="Task:explore", call_count=3),
        ToolUsage(session_id=s1.id, tool_name="Skill:commit", call_count=2),
    ]
    # Bob's tools: core only
    tools_s2 = [
        ToolUsage(session_id=s2.id, tool_name="Read", call_count=20),
        ToolUsage(session_id=s2.id, tool_name="Write", call_count=5),
    ]
    db_session.add_all(tools_s1 + tools_s2)
    db_session.flush()

    return {"team": team, "eng1": eng1, "eng2": eng2, "s1": s1, "s2": s2}


def test_maturity_empty(client, admin_headers):
    resp = client.get("/api/v1/analytics/maturity", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sessions_analyzed"] == 0
    assert data["avg_leverage_score"] == 0.0
    assert data["orchestration_adoption_rate"] == 0.0
    assert data["tool_categories"]["core"] == {}
    assert data["engineer_profiles"] == []
    assert data["daily_leverage"] == []
    assert data["agent_skill_breakdown"] == []


def test_maturity_with_data(client, admin_headers, seeded_maturity_data):
    resp = client.get("/api/v1/analytics/maturity", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sessions_analyzed"] == 2

    # Tool categories should have entries
    cats = data["tool_categories"]
    assert "Read" in cats["core"]
    assert "Glob" in cats["search"]
    assert "Task:explore" in cats["orchestration"]
    assert "Skill:commit" in cats["skill"]

    # Engineer profiles
    profiles = data["engineer_profiles"]
    assert len(profiles) == 2
    # Alice should have higher leverage score (uses orchestration)
    alice = next(p for p in profiles if p["name"] == "Alice")
    bob = next(p for p in profiles if p["name"] == "Bob")
    assert alice["leverage_score"] > bob["leverage_score"]
    assert alice["orchestration_calls"] == 3
    assert alice["skill_calls"] == 2
    assert bob["orchestration_calls"] == 0


def test_maturity_effectiveness_scores_reflect_quality_and_follow_through(
    client, admin_headers, seeded_maturity_data, db_session
):
    now = datetime.now(tz=UTC)
    team = seeded_maturity_data["team"]
    alice = seeded_maturity_data["eng1"]
    alice_session = seeded_maturity_data["s1"]
    bob_session = seeded_maturity_data["s2"]

    repo = GitRepository(full_name=f"acme/{uuid.uuid4().hex[:8]}")
    db_session.add(repo)
    db_session.flush()

    db_session.add_all(
        [
            SessionFacets(session_id=alice_session.id, outcome="success", session_type="feature"),
            SessionFacets(session_id=bob_session.id, outcome="failure", session_type="debugging"),
            ModelUsage(
                session_id=alice_session.id,
                model_name="claude-sonnet-4-5-20250929",
                input_tokens=1000,
                output_tokens=500,
                cache_read_tokens=0,
                cache_creation_tokens=0,
            ),
            ModelUsage(
                session_id=bob_session.id,
                model_name="claude-sonnet-4-5-20250929",
                input_tokens=4000,
                output_tokens=2000,
                cache_read_tokens=0,
                cache_creation_tokens=0,
            ),
        ]
    )

    pr = PullRequest(
        repository_id=repo.id,
        engineer_id=alice.id,
        github_pr_number=101,
        title="Ship maturity work",
        state="merged",
        pr_created_at=now - timedelta(days=1),
        merged_at=now - timedelta(hours=8),
    )
    db_session.add(pr)
    db_session.flush()
    db_session.add(
        SessionCommit(
            session_id=alice_session.id,
            repository_id=repo.id,
            pull_request_id=pr.id,
            commit_sha=uuid.uuid4().hex[:12],
            commit_message="feat: improve maturity",
            committed_at=now - timedelta(hours=12),
        )
    )
    db_session.flush()

    response = client.get(f"/api/v1/analytics/maturity?team_id={team.id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()

    alice_profile = next(item for item in data["engineer_profiles"] if item["name"] == "Alice")
    bob_profile = next(item for item in data["engineer_profiles"] if item["name"] == "Bob")

    assert alice_profile["effectiveness_score"] is not None
    assert bob_profile["effectiveness_score"] is not None
    assert alice_profile["effectiveness_score"] > bob_profile["effectiveness_score"]
    assert data["avg_effectiveness_score"] is not None


def test_maturity_orchestration_adoption(client, admin_headers, seeded_maturity_data):
    resp = client.get("/api/v1/analytics/maturity", headers=admin_headers)
    data = resp.json()
    # Alice uses orchestration+skill, Bob uses core only → 1/2
    assert data["orchestration_adoption_rate"] == 0.5


def test_maturity_skill_only_adoption(client, admin_headers, db_session):
    """Engineer using only Skill tools (no orchestration) should count for adoption."""
    team = Team(name="skill-team")
    db_session.add(team)
    db_session.flush()

    eng = Engineer(name="Carol", email="carol@test.com", team_id=team.id, api_key_hash="x")
    db_session.add(eng)
    db_session.flush()

    now = datetime.now(tz=UTC)
    s = Session(id=str(uuid.uuid4()), engineer_id=eng.id, started_at=now)
    db_session.add(s)
    db_session.flush()

    # Only skill tools, no orchestration
    db_session.add(ToolUsage(session_id=s.id, tool_name="Skill:commit", call_count=5))
    db_session.add(ToolUsage(session_id=s.id, tool_name="Read", call_count=10))
    db_session.flush()

    resp = client.get(f"/api/v1/analytics/maturity?team_id={team.id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Carol uses skill tools → should count for adoption rate
    assert data["orchestration_adoption_rate"] == 1.0


def test_maturity_agent_skill_breakdown(client, admin_headers, seeded_maturity_data):
    resp = client.get("/api/v1/analytics/maturity", headers=admin_headers)
    data = resp.json()
    breakdown = data["agent_skill_breakdown"]
    names = [item["name"] for item in breakdown]
    assert "Task:explore" in names
    assert "Skill:commit" in names
    task_explore = next(i for i in breakdown if i["name"] == "Task:explore")
    assert task_explore["category"] == "orchestration"
    assert task_explore["total_calls"] == 3


def test_maturity_filters_to_explicit_customizations(
    client, admin_headers, seeded_maturity_data, db_session
):
    s1 = seeded_maturity_data["s1"]
    s2 = seeded_maturity_data["s2"]

    db_session.add_all(
        [
            SessionCustomization(
                session_id=s1.id,
                customization_type="mcp",
                state="available",
                identifier="github",
                provenance="user_local",
                source_classification="marketplace",
                invocation_count=0,
            ),
            SessionCustomization(
                session_id=s1.id,
                customization_type="mcp",
                state="enabled",
                identifier="github",
                provenance="user_local",
                source_classification="marketplace",
                invocation_count=0,
            ),
            SessionCustomization(
                session_id=s1.id,
                customization_type="mcp",
                state="invoked",
                identifier="github",
                provenance="user_local",
                source_classification="marketplace",
                invocation_count=3,
            ),
            SessionCustomization(
                session_id=s1.id,
                customization_type="skill",
                state="available",
                identifier="review-pr",
                provenance="repo_defined",
                source_classification="custom",
                invocation_count=0,
            ),
            SessionCustomization(
                session_id=s1.id,
                customization_type="skill",
                state="enabled",
                identifier="review-pr",
                provenance="repo_defined",
                source_classification="custom",
                invocation_count=0,
            ),
            SessionCustomization(
                session_id=s1.id,
                customization_type="skill",
                state="invoked",
                identifier="review-pr",
                provenance="repo_defined",
                source_classification="custom",
                invocation_count=1,
            ),
            SessionCustomization(
                session_id=s2.id,
                customization_type="skill",
                state="available",
                identifier="always-on",
                provenance="built_in",
                source_classification="built_in",
                invocation_count=0,
            ),
            SessionCustomization(
                session_id=s2.id,
                customization_type="skill",
                state="invoked",
                identifier="always-on",
                provenance="built_in",
                source_classification="built_in",
                invocation_count=5,
            ),
        ]
    )
    db_session.flush()

    response = client.get("/api/v1/analytics/maturity", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["explicit_customization_adoption_rate"] == 0.5
    identifiers = [item["identifier"] for item in data["customization_breakdown"]]
    assert identifiers == ["github", "review-pr"]
    github = next(
        item for item in data["customization_breakdown"] if item["identifier"] == "github"
    )
    assert github["provenance"] == "user_local"
    assert github["source_classification"] == "marketplace"
    assert github["engineer_count"] == 1
    assert github["top_engineers"] == ["Alice"]
    assert len(data["high_performer_stacks"]) == 1
    stack = data["high_performer_stacks"][0]
    assert stack["engineer_count"] == 1
    assert stack["label"] == "github + review-pr"
    assert [item["identifier"] for item in stack["customizations"]] == ["github", "review-pr"]
    assert [item["source_classification"] for item in stack["customizations"]] == [
        "marketplace",
        "custom",
    ]
    assert stack["top_engineers"] == ["Alice"]
    outcome_labels = {(row["dimension"], row["label"]) for row in data["customization_outcomes"]}
    assert ("customization", "github") in outcome_labels
    assert ("stack", "github + review-pr") in outcome_labels
    github_outcome = next(
        row
        for row in data["customization_outcomes"]
        if row["dimension"] == "customization" and row["label"] == "github"
    )
    assert github_outcome["source_classification"] == "marketplace"
    github_state = next(
        row for row in data["customization_state_funnel"] if row["identifier"] == "github"
    )
    assert github_state["available_engineer_count"] == 1
    assert github_state["enabled_engineer_count"] == 1
    assert github_state["invoked_engineer_count"] == 1
    assert github_state["activation_rate"] == 1.0
    assert github_state["usage_rate"] == 1.0
    built_in_state = next(
        row for row in data["customization_state_funnel"] if row["identifier"] == "always-on"
    )
    assert built_in_state["provenance"] == "built_in"
    assert built_in_state["available_engineer_count"] == 1
    assert built_in_state["enabled_engineer_count"] == 0
    assert built_in_state["invoked_engineer_count"] == 1
    assert built_in_state["available_not_enabled_engineer_count"] == 1


def test_maturity_builds_team_customization_landscape(client, admin_headers, db_session):
    team_one = Team(name="Platform")
    team_two = Team(name="Product")
    db_session.add_all([team_one, team_two])
    db_session.flush()

    alice = Engineer(
        name="Alice",
        email="alice-landscape@test.com",
        team_id=team_one.id,
        api_key_hash="x",
    )
    bob = Engineer(
        name="Bob",
        email="bob-landscape@test.com",
        team_id=team_one.id,
        api_key_hash="x",
    )
    cara = Engineer(
        name="Cara",
        email="cara-landscape@test.com",
        team_id=team_two.id,
        api_key_hash="x",
    )
    db_session.add_all([alice, bob, cara])
    db_session.flush()

    now = datetime.now(tz=UTC)
    sessions = [
        Session(id=str(uuid.uuid4()), engineer_id=alice.id, started_at=now - timedelta(days=1)),
        Session(id=str(uuid.uuid4()), engineer_id=bob.id, started_at=now - timedelta(days=1)),
        Session(id=str(uuid.uuid4()), engineer_id=cara.id, started_at=now - timedelta(days=1)),
    ]
    db_session.add_all(sessions)
    db_session.flush()

    db_session.add_all(
        [
            ToolUsage(session_id=sessions[0].id, tool_name="Read", call_count=2),
            ToolUsage(session_id=sessions[1].id, tool_name="Read", call_count=2),
            ToolUsage(session_id=sessions[2].id, tool_name="Read", call_count=2),
            SessionCustomization(
                session_id=sessions[0].id,
                customization_type="mcp",
                state="invoked",
                identifier="github",
                provenance="user_local",
                invocation_count=3,
            ),
            SessionCustomization(
                session_id=sessions[1].id,
                customization_type="skill",
                state="invoked",
                identifier="review-pr",
                provenance="repo_defined",
                invocation_count=1,
            ),
            SessionCustomization(
                session_id=sessions[2].id,
                customization_type="mcp",
                state="invoked",
                identifier="linear",
                provenance="user_local",
                invocation_count=2,
            ),
        ]
    )
    db_session.flush()

    response = client.get("/api/v1/analytics/maturity", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()

    team_rows = {row["team_name"]: row for row in data["team_customization_landscape"]}
    assert team_rows["Platform"]["explicit_customization_count"] == 2
    assert team_rows["Platform"]["adoption_rate"] == 1.0
    assert team_rows["Platform"]["top_customizations"] == ["github", "review-pr"]
    assert team_rows["Platform"]["unique_customizations"] == ["github", "review-pr"]
    assert team_rows["Product"]["top_customizations"] == ["linear"]


def test_maturity_builds_toolchain_reliability_view(
    client, admin_headers, seeded_maturity_data, db_session
):
    s1 = seeded_maturity_data["s1"]
    s2 = seeded_maturity_data["s2"]

    db_session.add_all(
        [
            SessionFacets(
                session_id=s1.id,
                outcome="success",
                friction_counts={"tool_error": 2, "timeout": 1},
            ),
            SessionFacets(
                session_id=s2.id,
                outcome="failure",
                friction_counts={"permission_denied": 1},
            ),
            SessionRecoveryPath(
                session_id=s1.id,
                friction_detected=True,
                recovery_step_count=2,
                recovery_result="recovered",
                final_outcome="success",
            ),
            SessionRecoveryPath(
                session_id=s2.id,
                friction_detected=True,
                recovery_step_count=1,
                recovery_result="abandoned",
                final_outcome="failure",
            ),
            SessionCustomization(
                session_id=s1.id,
                customization_type="mcp",
                state="invoked",
                identifier="github",
                provenance="user_local",
                source_classification="marketplace",
                invocation_count=3,
            ),
        ]
    )
    db_session.flush()

    response = client.get("/api/v1/analytics/maturity", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    reliability_rows = {
        (row["surface_type"], row["identifier"]): row for row in data["toolchain_reliability"]
    }
    github = reliability_rows[("mcp", "github")]
    assert github["session_count"] == 1
    assert github["engineer_count"] == 1
    assert github["friction_session_rate"] == 1.0
    assert github["failure_session_rate"] == 1.0
    assert github["recovery_rate"] == 1.0
    assert github["success_rate"] == 1.0
    assert github["abandonment_rate"] == 0.0
    assert github["top_friction_types"] == ["tool_error", "timeout"]

    read_tool = reliability_rows[("built_in_tool", "Read")]
    assert read_tool["session_count"] == 2
    assert read_tool["engineer_count"] == 2
    assert read_tool["friction_session_rate"] == 1.0
    assert read_tool["failure_session_rate"] == 0.5
    assert read_tool["recovery_rate"] == 0.5
    assert read_tool["success_rate"] == 0.5
    assert read_tool["abandonment_rate"] == 0.5


def test_maturity_builds_delegation_patterns(
    client, admin_headers, seeded_maturity_data, db_session
):
    s1 = seeded_maturity_data["s1"]
    s2 = seeded_maturity_data["s2"]

    db_session.add_all(
        [
            SessionFacets(session_id=s1.id, outcome="success"),
            SessionFacets(session_id=s2.id, outcome="failure"),
            SessionWorkflowProfile(session_id=s1.id, archetype="debugging"),
            SessionWorkflowProfile(session_id=s2.id, archetype="investigation"),
        ]
    )
    db_session.flush()

    response = client.get("/api/v1/analytics/maturity", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    explore = next(row for row in data["delegation_patterns"] if row["target_node"] == "explore")
    assert explore["edge_type"] == "subagent_task"
    assert explore["session_count"] == 1
    assert explore["engineer_count"] == 1
    assert explore["total_calls"] == 3
    assert explore["success_rate"] == 1.0
    assert explore["top_workflow_archetypes"] == ["debugging"]


def test_maturity_builds_agent_team_modes(client, admin_headers, seeded_maturity_data, db_session):
    s1 = seeded_maturity_data["s1"]
    s2 = seeded_maturity_data["s2"]

    db_session.add_all(
        [
            SessionFacets(session_id=s1.id, outcome="success"),
            SessionFacets(session_id=s2.id, outcome="failure"),
            SessionWorkflowProfile(session_id=s1.id, archetype="debugging"),
            SessionWorkflowProfile(session_id=s2.id, archetype="investigation"),
            SessionMessage(
                session_id=s1.id,
                ordinal=0,
                role="assistant",
                tool_calls=[
                    {
                        "name": "Task",
                        "input_preview": '{"subagent_type":"reviewer","prompt":"Review the diff"}',
                    },
                    {
                        "name": "SendMessage",
                        "input_preview": '{"recipient":"qa","message":"Smoke test it"}',
                    },
                ],
            ),
        ]
    )
    db_session.flush()

    response = client.get("/api/v1/analytics/maturity", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    rows = {row["coordination_mode"]: row for row in data["agent_team_modes"]}
    assert rows["agent_team"]["session_count"] == 1
    assert rows["agent_team"]["engineer_count"] == 1
    assert rows["agent_team"]["success_rate"] == 1.0
    assert rows["agent_team"]["avg_delegation_edges"] == 3.0
    assert rows["agent_team"]["top_targets"] == ["explore", "qa", "reviewer"]
    assert rows["solo"]["session_count"] == 1
    assert rows["solo"]["success_rate"] == 0.0


def test_maturity_toolchain_reliability_deduplicates_duplicate_tool_rows(
    client, admin_headers, seeded_maturity_data, db_session
):
    s1 = seeded_maturity_data["s1"]
    s2 = seeded_maturity_data["s2"]

    db_session.add(ToolUsage(session_id=s1.id, tool_name="Read", call_count=7))
    db_session.add_all(
        [
            SessionFacets(session_id=s1.id, outcome="success", friction_counts={"tool_error": 1}),
            SessionFacets(session_id=s2.id, outcome="failure", friction_counts={"timeout": 1}),
            SessionRecoveryPath(
                session_id=s1.id,
                friction_detected=True,
                recovery_step_count=1,
                recovery_result="recovered",
                final_outcome="success",
            ),
            SessionRecoveryPath(
                session_id=s2.id,
                friction_detected=True,
                recovery_step_count=3,
                recovery_result="abandoned",
                final_outcome="failure",
            ),
        ]
    )
    db_session.flush()

    response = client.get("/api/v1/analytics/maturity", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    read_tool = next(
        row
        for row in data["toolchain_reliability"]
        if row["surface_type"] == "built_in_tool" and row["identifier"] == "Read"
    )
    assert read_tool["session_count"] == 2
    assert read_tool["friction_session_count"] == 2
    assert read_tool["avg_recovery_steps"] == 2.0


def test_maturity_date_filtering(client, admin_headers, seeded_maturity_data):
    now = datetime.now(tz=UTC)
    # Filter to only include yesterday (Alice's session)
    start = (now - timedelta(days=1, hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
    end = now.strftime("%Y-%m-%dT%H:%M:%S")
    resp = client.get(
        f"/api/v1/analytics/maturity?start_date={start}&end_date={end}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sessions_analyzed"] == 1
    assert len(data["engineer_profiles"]) == 1
    assert data["engineer_profiles"][0]["name"] == "Alice"


def test_maturity_auth(client):
    resp = client.get("/api/v1/analytics/maturity")
    assert resp.status_code in (401, 403)
