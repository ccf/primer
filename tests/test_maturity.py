import uuid
from datetime import UTC, datetime, timedelta

import pytest

from primer.common.models import Engineer, Session, Team, ToolUsage


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


def test_maturity_orchestration_adoption(client, admin_headers, seeded_maturity_data):
    resp = client.get("/api/v1/analytics/maturity", headers=admin_headers)
    data = resp.json()
    # 1 out of 2 engineers uses orchestration
    assert data["orchestration_adoption_rate"] == 0.5


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
