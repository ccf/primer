import uuid
from datetime import UTC, datetime, timedelta

from primer.common.models import Session, SessionFacets, SessionMessage, ToolUsage


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


def test_bottlenecks_empty(client, admin_headers):
    """Empty state returns zeroed response."""
    r = client.get("/api/v1/analytics/bottlenecks", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_sessions_analyzed"] == 0
    assert data["sessions_with_any_friction"] == 0
    assert data["overall_friction_rate"] == 0.0
    assert data["friction_impacts"] == []
    assert data["project_friction"] == []
    assert data["friction_trends"] == []
    assert data["root_cause_clusters"] == []


def test_bottlenecks_with_friction(client, db_session, engineer_with_key, admin_headers):
    """Sessions with friction data produce correct aggregation."""
    eng, _key = engineer_with_key
    now = datetime.now(UTC)

    # Session 1: with friction, success
    s1 = _create_session(
        db_session,
        eng,
        started_at=now - timedelta(hours=2),
        project_name="project-a",
    )
    f1 = SessionFacets(
        session_id=s1.id,
        outcome="success",
        friction_counts={"permission_denied": 3, "timeout": 1},
        friction_detail="Permission was denied on file write",
    )
    db_session.add(f1)
    db_session.add(ToolUsage(session_id=s1.id, tool_name="Bash", call_count=2))
    db_session.add(
        SessionMessage(
            session_id=s1.id,
            ordinal=1,
            role="human",
            content_text="Please run the verification command and fix the issue.",
        )
    )

    # Session 2: with friction, failure
    s2 = _create_session(
        db_session,
        eng,
        started_at=now - timedelta(hours=1),
        project_name="project-a",
    )
    f2 = SessionFacets(
        session_id=s2.id,
        outcome="failure",
        friction_counts={"permission_denied": 2},
        friction_detail="Could not access directory",
    )
    db_session.add(f2)
    db_session.add(ToolUsage(session_id=s2.id, tool_name="Bash", call_count=1))
    db_session.add(ToolUsage(session_id=s2.id, tool_name="Edit", call_count=1))
    db_session.add(
        SessionMessage(
            session_id=s2.id,
            ordinal=1,
            role="human",
            content_text="Permission errors keep blocking the command.",
        )
    )

    # Session 3: no friction, success
    s3 = _create_session(
        db_session,
        eng,
        started_at=now,
        project_name="project-b",
    )
    f3 = SessionFacets(
        session_id=s3.id,
        outcome="success",
        friction_counts=None,
    )
    db_session.add(f3)

    db_session.flush()

    r = client.get("/api/v1/analytics/bottlenecks", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()

    assert data["total_sessions_analyzed"] == 3
    assert data["sessions_with_any_friction"] == 2
    assert data["overall_friction_rate"] > 0

    # Friction impacts
    impacts = data["friction_impacts"]
    assert len(impacts) >= 1
    perm_impact = next((i for i in impacts if i["friction_type"] == "permission_denied"), None)
    assert perm_impact is not None
    assert perm_impact["occurrence_count"] == 5  # 3 + 2
    assert perm_impact["sessions_affected"] == 2
    assert perm_impact["success_rate_with"] is not None
    assert len(perm_impact["sample_details"]) > 0

    # Project friction
    projects = data["project_friction"]
    assert len(projects) >= 1
    proj_a = next((p for p in projects if p["project_name"] == "project-a"), None)
    assert proj_a is not None
    assert proj_a["sessions_with_friction"] == 2
    assert proj_a["total_sessions"] == 2
    assert "permission_denied" in proj_a["top_friction_types"]

    clusters = data["root_cause_clusters"]
    assert len(clusters) >= 1
    permission_cluster = next(
        (cluster for cluster in clusters if cluster["cause_category"] == "permission_boundary"),
        None,
    )
    assert permission_cluster is not None
    assert permission_cluster["workflow_stage"] == "execute"
    assert permission_cluster["session_count"] == 2
    assert permission_cluster["occurrence_count"] == 6
    assert "permission_denied" in permission_cluster["top_friction_types"]
    assert "Bash" in permission_cluster["common_tools"]
    assert "permission" in permission_cluster["transcript_cues"]
    assert "Permission was denied on file write" in permission_cluster["sample_details"]

    # Friction trends
    assert len(data["friction_trends"]) > 0


def test_bottlenecks_date_filtering(client, db_session, engineer_with_key, admin_headers):
    """Date filtering restricts results."""
    eng, _key = engineer_with_key
    old_date = datetime(2024, 1, 1, tzinfo=UTC)

    s = _create_session(db_session, eng, started_at=old_date, project_name="old-proj")
    f = SessionFacets(
        session_id=s.id,
        outcome="success",
        friction_counts={"compile_error": 5},
    )
    db_session.add(f)
    db_session.flush()

    # Filter to recent dates only — should not include the old session
    start = "2025-01-01T00:00:00"
    r = client.get(
        f"/api/v1/analytics/bottlenecks?start_date={start}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    # The old session should be excluded
    for p in data["project_friction"]:
        assert p["project_name"] != "old-proj"


def test_bottlenecks_requires_auth(client):
    """Bottlenecks endpoint requires authentication."""
    r = client.get("/api/v1/analytics/bottlenecks")
    assert r.status_code == 401
