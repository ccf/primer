import uuid
from datetime import UTC, datetime, timedelta

from primer.common.models import Session, ToolUsage


def _create_session(db_session, engineer, **kwargs):
    sid = str(uuid.uuid4())
    session = Session(
        id=sid,
        engineer_id=engineer.id,
        message_count=10,
        user_message_count=5,
        assistant_message_count=5,
        tool_call_count=3,
        input_tokens=1000,
        output_tokens=500,
        duration_seconds=120.0,
        **kwargs,
    )
    db_session.add(session)
    db_session.flush()
    return session


def test_tool_adoption_empty(client, admin_headers):
    """Empty state returns zeroed response."""
    r = client.get("/api/v1/analytics/tool-adoption", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_engineers"] == 0
    assert data["total_tools_discovered"] == 0
    assert data["avg_tools_per_engineer"] == 0.0
    assert data["tool_adoption"] == []
    assert data["tool_trends"] == []
    assert data["engineer_profiles"] == []


def test_tool_adoption_with_data(client, db_session, engineer_with_key, admin_headers):
    """Sessions with tool usage produce correct adoption analytics."""
    eng, _key = engineer_with_key
    now = datetime.now(UTC)

    # Session 1 with tools
    s1 = _create_session(db_session, eng, started_at=now - timedelta(hours=2))
    db_session.add(ToolUsage(session_id=s1.id, tool_name="Read", call_count=10))
    db_session.add(ToolUsage(session_id=s1.id, tool_name="Write", call_count=5))
    db_session.add(ToolUsage(session_id=s1.id, tool_name="Bash", call_count=3))

    # Session 2 with tools
    s2 = _create_session(db_session, eng, started_at=now - timedelta(hours=1))
    db_session.add(ToolUsage(session_id=s2.id, tool_name="Read", call_count=8))
    db_session.add(ToolUsage(session_id=s2.id, tool_name="Grep", call_count=4))

    db_session.flush()

    r = client.get("/api/v1/analytics/tool-adoption", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()

    assert data["total_engineers"] == 1
    assert data["total_tools_discovered"] == 4
    assert data["avg_tools_per_engineer"] > 0

    # Tool adoption entries
    adoption = data["tool_adoption"]
    assert len(adoption) == 4
    read_tool = next(t for t in adoption if t["tool_name"] == "Read")
    assert read_tool["total_calls"] == 18  # 10 + 8
    assert read_tool["session_count"] == 2
    assert read_tool["engineer_count"] == 1
    assert read_tool["adoption_rate"] == 100.0  # 1/1 engineer

    # Tool trends (top 5 tools, daily)
    assert len(data["tool_trends"]) > 0

    # Engineer profiles
    profiles = data["engineer_profiles"]
    assert len(profiles) == 1
    assert profiles[0]["name"] == "Test Engineer"
    assert profiles[0]["tools_used"] == 4
    assert profiles[0]["total_tool_calls"] == 30  # 10+5+3+8+4
    assert len(profiles[0]["top_tools"]) > 0


def test_tool_adoption_date_filtering(client, db_session, engineer_with_key, admin_headers):
    """Date filtering restricts results."""
    eng, _key = engineer_with_key
    old_date = datetime(2024, 1, 1, tzinfo=UTC)

    s = _create_session(db_session, eng, started_at=old_date)
    db_session.add(ToolUsage(session_id=s.id, tool_name="OldTool", call_count=5))
    db_session.flush()

    # Filter to recent dates only
    start = "2025-01-01T00:00:00"
    r = client.get(
        f"/api/v1/analytics/tool-adoption?start_date={start}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    tool_names = [t["tool_name"] for t in data["tool_adoption"]]
    assert "OldTool" not in tool_names


def test_tool_adoption_requires_auth(client):
    """Tool adoption endpoint requires authentication."""
    r = client.get("/api/v1/analytics/tool-adoption")
    assert r.status_code == 401
