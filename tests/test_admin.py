import uuid
from datetime import UTC, datetime

import pytest

from primer.common.models import AuditLog, ModelUsage, SessionFacets, SessionMessage, ToolUsage
from primer.common.models import Session as SessionModel


def _ingest_session(client, api_key, **kwargs):
    session_id = kwargs.pop("session_id", str(uuid.uuid4()))
    payload = {
        "session_id": session_id,
        "api_key": api_key,
        "message_count": 10,
        "user_message_count": 5,
        "assistant_message_count": 5,
        "tool_call_count": 3,
        "input_tokens": 1000,
        "output_tokens": 500,
        "duration_seconds": 120.0,
        **kwargs,
    }
    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 200
    return session_id


def _create_measurement_integrity_session(
    db_session,
    engineer_id,
    *,
    agent_type="claude_code",
    with_messages=False,
    with_tool_usage=False,
    with_model_usage=False,
    outcome=None,
    goal_categories=None,
    confidence_score=None,
):
    session = SessionModel(
        id=str(uuid.uuid4()),
        engineer_id=engineer_id,
        agent_type=agent_type,
        started_at=datetime.now(UTC),
        message_count=1 if with_messages else 0,
        user_message_count=1 if with_messages else 0,
        assistant_message_count=0,
        tool_call_count=1 if with_tool_usage else 0,
        input_tokens=100 if with_model_usage else 0,
        output_tokens=50 if with_model_usage else 0,
        primary_model="claude-sonnet-4-5-20250929" if with_model_usage else None,
        duration_seconds=60.0,
        has_facets=(
            outcome is not None or goal_categories is not None or confidence_score is not None
        ),
    )
    db_session.add(session)
    db_session.flush()

    if with_messages:
        db_session.add(
            SessionMessage(
                session_id=session.id,
                ordinal=0,
                role="human",
                content_text="Investigate measurement integrity coverage",
            )
        )

    if with_tool_usage:
        db_session.add(
            ToolUsage(
                session_id=session.id,
                tool_name="Read",
                call_count=1,
            )
        )

    if with_model_usage:
        db_session.add(
            ModelUsage(
                session_id=session.id,
                model_name="claude-sonnet-4-5-20250929",
                input_tokens=100,
                output_tokens=50,
            )
        )

    if session.has_facets:
        db_session.add(
            SessionFacets(
                session_id=session.id,
                outcome=outcome,
                goal_categories=goal_categories,
                confidence_score=confidence_score,
            )
        )

    db_session.flush()
    return session.id


def test_system_stats(client, admin_headers, engineer_with_key):
    _eng, api_key = engineer_with_key
    _ingest_session(client, api_key)

    r = client.get("/api/v1/admin/system-stats", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_engineers"] >= 1
    assert data["active_engineers"] >= 1
    assert data["total_teams"] >= 1
    assert data["total_sessions"] >= 1
    assert data["total_ingest_events"] >= 1
    assert "database_type" in data


def test_system_stats_requires_admin(client, engineer_with_key):
    _eng, api_key = engineer_with_key
    r = client.get("/api/v1/admin/system-stats", headers={"x-api-key": api_key})
    assert r.status_code == 403


def test_ingest_events(client, admin_headers, engineer_with_key):
    _eng, api_key = engineer_with_key
    _ingest_session(client, api_key)

    r = client.get("/api/v1/admin/ingest-events", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()["items"]
    assert len(data) >= 1
    assert data[0]["status"] == "ok"


def test_ingest_events_filter_by_engineer(client, admin_headers, engineer_with_key):
    eng, api_key = engineer_with_key
    _ingest_session(client, api_key)

    r = client.get(f"/api/v1/admin/ingest-events?engineer_id={eng.id}", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()["items"]
    assert all(e["engineer_id"] == eng.id for e in data)


def test_measurement_integrity_stats(client, admin_headers, engineer_with_key, db_session):
    eng, _api_key = engineer_with_key

    _create_measurement_integrity_session(
        db_session,
        eng.id,
        with_messages=True,
        outcome="success",
        goal_categories=["fix_bug"],
        confidence_score=0.92,
    )
    _create_measurement_integrity_session(
        db_session,
        eng.id,
        with_messages=True,
        outcome="mostly_achieved",
        goal_categories={"fix_bug": 1},
        confidence_score=0.4,
    )
    _create_measurement_integrity_session(db_session, eng.id, with_messages=False)

    r = client.get("/api/v1/admin/measurement-integrity", headers=admin_headers)
    assert r.status_code == 200

    data = r.json()
    assert data["total_sessions"] == 3
    assert data["sessions_with_messages"] == 2
    assert data["sessions_with_facets"] == 2
    assert data["facet_coverage_pct"] == pytest.approx(66.7, abs=0.1)
    assert data["transcript_coverage_pct"] == pytest.approx(66.7, abs=0.1)
    assert data["low_confidence_sessions"] == 1
    assert data["missing_confidence_sessions"] == 0
    assert data["legacy_outcome_sessions"] == 1
    assert data["legacy_goal_category_sessions"] == 1
    assert data["remaining_legacy_rows"] == 1


def test_measurement_integrity_stats_include_source_quality_breakdown(
    client, admin_headers, engineer_with_key, db_session
):
    eng, _api_key = engineer_with_key

    _create_measurement_integrity_session(
        db_session,
        eng.id,
        agent_type="claude_code",
        with_messages=True,
        with_tool_usage=True,
        with_model_usage=True,
        outcome="success",
        goal_categories=["fix_bug"],
        confidence_score=0.95,
    )
    _create_measurement_integrity_session(
        db_session,
        eng.id,
        agent_type="cursor",
        with_messages=True,
    )
    _create_measurement_integrity_session(
        db_session,
        eng.id,
        agent_type="cursor",
        with_messages=False,
    )

    response = client.get("/api/v1/admin/measurement-integrity", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["sessions_missing_transcript_telemetry"] == 1
    assert data["sessions_missing_tool_telemetry"] == 0
    assert data["sessions_missing_model_telemetry"] == 0

    source_quality = {entry["agent_type"]: entry for entry in data["source_quality"]}

    assert source_quality["claude_code"] == {
        "agent_type": "claude_code",
        "session_count": 1,
        "transcript_parity": "required",
        "transcript_coverage_pct": 100.0,
        "tool_call_parity": "required",
        "tool_call_coverage_pct": 100.0,
        "model_usage_parity": "required",
        "model_usage_coverage_pct": 100.0,
        "facet_parity": "required",
        "facet_coverage_pct": 100.0,
        "native_discovery_parity": "required",
    }
    assert source_quality["cursor"] == {
        "agent_type": "cursor",
        "session_count": 2,
        "transcript_parity": "required",
        "transcript_coverage_pct": 50.0,
        "tool_call_parity": "unavailable",
        "tool_call_coverage_pct": 0.0,
        "model_usage_parity": "unavailable",
        "model_usage_coverage_pct": 0.0,
        "facet_parity": "unavailable",
        "facet_coverage_pct": 0.0,
        "native_discovery_parity": "unavailable",
    }


def test_measurement_integrity_stats_count_missing_supported_tool_and_model_telemetry(
    client, admin_headers, engineer_with_key, db_session
):
    eng, _api_key = engineer_with_key

    _create_measurement_integrity_session(
        db_session,
        eng.id,
        agent_type="claude_code",
        with_messages=True,
        with_tool_usage=True,
        with_model_usage=True,
        outcome="success",
        confidence_score=0.95,
    )
    _create_measurement_integrity_session(
        db_session,
        eng.id,
        agent_type="claude_code",
        with_messages=True,
        with_tool_usage=False,
        with_model_usage=False,
        outcome="success",
        confidence_score=0.91,
    )
    _create_measurement_integrity_session(
        db_session,
        eng.id,
        agent_type="cursor",
        with_messages=True,
        with_tool_usage=False,
        with_model_usage=False,
    )

    response = client.get("/api/v1/admin/measurement-integrity", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["sessions_missing_tool_telemetry"] == 1
    assert data["sessions_missing_model_telemetry"] == 1

    source_quality = {entry["agent_type"]: entry for entry in data["source_quality"]}
    assert source_quality["claude_code"]["transcript_parity"] == "required"
    assert source_quality["claude_code"]["tool_call_coverage_pct"] == 50.0
    assert source_quality["claude_code"]["model_usage_coverage_pct"] == 50.0
    assert source_quality["cursor"]["transcript_parity"] == "required"
    assert source_quality["cursor"]["tool_call_parity"] == "unavailable"
    assert source_quality["cursor"]["tool_call_coverage_pct"] == 0.0
    assert source_quality["cursor"]["model_usage_coverage_pct"] == 0.0


def test_measurement_integrity_facet_coverage_pct_ignores_unsupported_sources(
    client, admin_headers, engineer_with_key, db_session
):
    eng, _api_key = engineer_with_key

    _create_measurement_integrity_session(
        db_session,
        eng.id,
        agent_type="claude_code",
        with_messages=True,
        outcome=None,
        goal_categories=None,
        confidence_score=None,
    )
    _create_measurement_integrity_session(
        db_session,
        eng.id,
        agent_type="cursor",
        with_messages=True,
        outcome="success",
        goal_categories=["fix_bug"],
        confidence_score=0.95,
    )

    response = client.get("/api/v1/admin/measurement-integrity", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total_sessions"] == 2
    assert data["sessions_with_facets"] == 1
    assert data["facet_coverage_pct"] == 0.0
    source_quality = {entry["agent_type"]: entry for entry in data["source_quality"]}
    assert source_quality["claude_code"]["facet_parity"] == "required"
    assert source_quality["claude_code"]["facet_coverage_pct"] == 0.0
    assert source_quality["cursor"]["facet_parity"] == "unavailable"
    assert source_quality["cursor"]["facet_coverage_pct"] == 0.0


def test_normalize_facets_endpoint_dry_run_and_limit(
    client, admin_headers, engineer_with_key, db_session
):
    eng, _api_key = engineer_with_key
    canonical_session_id = _create_measurement_integrity_session(
        db_session,
        eng.id,
        with_messages=True,
        outcome="success",
        goal_categories=["fix_bug"],
        confidence_score=0.95,
    )
    first_legacy_session_id = _create_measurement_integrity_session(
        db_session,
        eng.id,
        with_messages=True,
        outcome="mostly_achieved",
        goal_categories={"fix_bug": 1},
        confidence_score=0.45,
    )
    second_legacy_session_id = _create_measurement_integrity_session(
        db_session,
        eng.id,
        with_messages=True,
        outcome="fully_achieved",
        goal_categories={"testing": 1},
        confidence_score=0.51,
    )

    dry_run = client.post(
        "/api/v1/admin/normalize-facets?limit=2&dry_run=true",
        headers=admin_headers,
    )
    assert dry_run.status_code == 200
    assert dry_run.json() == {
        "rows_scanned": 2,
        "rows_updated": 0,
        "remaining_legacy_rows": 2,
    }

    canonical_facets = (
        db_session.query(SessionFacets)
        .filter(SessionFacets.session_id == canonical_session_id)
        .one()
    )
    first_facets = (
        db_session.query(SessionFacets)
        .filter(SessionFacets.session_id == first_legacy_session_id)
        .one()
    )
    assert canonical_facets.outcome == "success"
    assert canonical_facets.goal_categories == ["fix_bug"]
    assert first_facets.outcome == "mostly_achieved"
    assert first_facets.goal_categories == {"fix_bug": 1}

    applied = client.post(
        "/api/v1/admin/normalize-facets?limit=1&dry_run=false",
        headers=admin_headers,
    )
    assert applied.status_code == 200
    assert applied.json() == {
        "rows_scanned": 1,
        "rows_updated": 1,
        "remaining_legacy_rows": 1,
    }

    second_applied = client.post(
        "/api/v1/admin/normalize-facets?limit=1&dry_run=false",
        headers=admin_headers,
    )
    assert second_applied.status_code == 200
    assert second_applied.json() == {
        "rows_scanned": 1,
        "rows_updated": 1,
        "remaining_legacy_rows": 0,
    }

    canonical_facets = (
        db_session.query(SessionFacets)
        .filter(SessionFacets.session_id == canonical_session_id)
        .one()
    )
    first_facets = (
        db_session.query(SessionFacets)
        .filter(SessionFacets.session_id == first_legacy_session_id)
        .one()
    )
    second_facets = (
        db_session.query(SessionFacets)
        .filter(SessionFacets.session_id == second_legacy_session_id)
        .one()
    )
    assert canonical_facets.outcome == "success"
    assert canonical_facets.goal_categories == ["fix_bug"]
    assert first_facets.outcome == "partial"
    assert first_facets.goal_categories == ["fix_bug"]
    assert second_facets.outcome == "success"
    assert second_facets.goal_categories == ["testing"]


def test_normalize_facets_endpoint_requires_admin(client):
    r = client.post("/api/v1/admin/normalize-facets")
    assert r.status_code in (401, 403)


def test_normalize_facets_endpoint_audits_non_dry_run(
    client, admin_headers, engineer_with_key, db_session
):
    eng, _api_key = engineer_with_key
    _create_measurement_integrity_session(
        db_session,
        eng.id,
        with_messages=True,
        outcome="mostly_achieved",
        goal_categories={"fix_bug": 1},
        confidence_score=0.45,
    )

    response = client.post(
        "/api/v1/admin/normalize-facets?limit=1&dry_run=false",
        headers=admin_headers,
    )
    assert response.status_code == 200

    audit_log = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "normalize",
            AuditLog.resource_type == "session_facets",
        )
        .one()
    )
    assert audit_log.actor_role == "admin"
    assert audit_log.details == {
        "limit": 1,
        "dry_run": False,
        "rows_scanned": 1,
        "rows_updated": 1,
        "remaining_legacy_rows": 0,
    }


def test_deactivate_engineer(client, admin_headers, engineer_with_key):
    eng, _api_key = engineer_with_key

    r = client.delete(f"/api/v1/engineers/{eng.id}", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["is_active"] is False


def test_deactivate_not_found(client, admin_headers):
    r = client.delete("/api/v1/engineers/nonexistent", headers=admin_headers)
    assert r.status_code == 404


def test_rotate_api_key(client, admin_headers, engineer_with_key):
    eng, old_key = engineer_with_key

    r = client.post(f"/api/v1/engineers/{eng.id}/rotate-key", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "api_key" in data
    assert data["api_key"] != old_key
    assert data["api_key"].startswith("primer_")

    # New key should work for ingest
    r = client.post(
        "/api/v1/ingest/session",
        json={
            "session_id": str(uuid.uuid4()),
            "api_key": data["api_key"],
            "message_count": 1,
        },
    )
    assert r.status_code == 200


def test_update_team_name(client, admin_headers, engineer_with_key):
    eng, _api_key = engineer_with_key

    r = client.patch(
        f"/api/v1/teams/{eng.team_id}",
        json={"name": "Renamed Team"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed Team"


def test_update_team_duplicate_name(client, admin_headers, db_session):
    from primer.common.models import Team

    t1 = Team(name="Team Alpha")
    t2 = Team(name="Team Beta")
    db_session.add_all([t1, t2])
    db_session.flush()

    r = client.patch(
        f"/api/v1/teams/{t2.id}",
        json={"name": "Team Alpha"},
        headers=admin_headers,
    )
    assert r.status_code == 409
