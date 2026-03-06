"""Tests for the coaching brief endpoint."""

import uuid
from datetime import UTC, datetime

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
