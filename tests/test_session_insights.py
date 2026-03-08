import uuid
from datetime import datetime, timedelta

from primer.common.models import SessionFacets
from primer.server.services.session_insights_service import compute_session_health_score


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


def test_session_insights_empty(client, admin_headers):
    r = client.get("/api/v1/analytics/session-insights", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["sessions_analyzed"] == 0
    assert data["end_reasons"] == []
    assert data["satisfaction"]["total_sessions_with_data"] == 0
    assert data["friction_clusters"] == []
    assert data["cache_efficiency"]["total_cache_read_tokens"] == 0
    assert data["permission_modes"] == []
    assert data["goals"]["session_type_breakdown"] == []
    assert data["primary_success"]["full_count"] == 0


def test_session_insights_end_reasons(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        end_reason="user_exit",
        facets={"outcome": "success"},
    )
    _ingest_session(
        client,
        api_key,
        end_reason="user_exit",
        facets={"outcome": "partial"},
    )
    _ingest_session(
        client,
        api_key,
        end_reason="error",
        facets={"outcome": "failure"},
    )

    r = client.get("/api/v1/analytics/session-insights", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["sessions_analyzed"] == 3

    reasons = {er["end_reason"]: er for er in data["end_reasons"]}
    assert "user_exit" in reasons
    assert reasons["user_exit"]["count"] == 2
    assert reasons["user_exit"]["success_rate"] == 0.5
    assert "error" in reasons
    assert reasons["error"]["count"] == 1
    assert reasons["error"]["success_rate"] == 0.0


def test_session_insights_satisfaction(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        facets={
            "outcome": "success",
            "user_satisfaction_counts": {"satisfied": 3, "neutral": 1, "dissatisfied": 0},
        },
    )
    _ingest_session(
        client,
        api_key,
        facets={
            "outcome": "partial",
            "user_satisfaction_counts": {"satisfied": 1, "neutral": 0, "dissatisfied": 2},
        },
    )

    r = client.get("/api/v1/analytics/session-insights", headers=admin_headers)
    data = r.json()
    sat = data["satisfaction"]
    assert sat["total_sessions_with_data"] == 2
    assert sat["satisfied_count"] == 4
    assert sat["neutral_count"] == 1
    assert sat["dissatisfied_count"] == 2
    assert sat["satisfaction_rate"] is not None
    assert 0 < sat["satisfaction_rate"] < 1


def test_session_insights_friction_clusters(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        facets={
            "outcome": "partial",
            "friction_counts": {"permission_denied": 3, "timeout": 1},
            "friction_detail": "Couldn't access file",
        },
    )
    _ingest_session(
        client,
        api_key,
        facets={
            "outcome": "success",
            "friction_counts": {"permission_denied": 2},
            "friction_detail": "Permission error on /etc",
        },
    )

    r = client.get("/api/v1/analytics/session-insights", headers=admin_headers)
    data = r.json()
    clusters = data["friction_clusters"]
    assert len(clusters) >= 1
    perm_cluster = next(c for c in clusters if c["cluster_label"] == "permission_denied")
    assert perm_cluster["occurrence_count"] == 5
    assert len(perm_cluster["sample_details"]) <= 5


def test_session_insights_cache_efficiency(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        cache_read_tokens=500,
        input_tokens=1000,
        model_usages=[
            {
                "model_name": "claude-sonnet-4-20250514",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_read_tokens": 500,
                "cache_creation_tokens": 200,
            }
        ],
    )

    r = client.get("/api/v1/analytics/session-insights", headers=admin_headers)
    data = r.json()
    cache = data["cache_efficiency"]
    assert cache["total_cache_read_tokens"] == 500
    assert cache["total_input_tokens"] == 1000
    assert cache["cache_hit_rate"] is not None
    # hit_rate = 500 / (500 + 1000) = 0.333
    assert 0.3 <= cache["cache_hit_rate"] <= 0.4
    assert cache["cache_savings_estimate"] is not None
    assert cache["cache_savings_estimate"] > 0


def test_session_insights_permission_modes(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        permission_mode="default",
        facets={"outcome": "success"},
    )
    _ingest_session(
        client,
        api_key,
        permission_mode="default",
        facets={"outcome": "success"},
    )
    _ingest_session(
        client,
        api_key,
        permission_mode="plan",
        facets={"outcome": "failure"},
    )

    r = client.get("/api/v1/analytics/session-insights", headers=admin_headers)
    data = r.json()
    modes = {m["mode"]: m for m in data["permission_modes"]}
    assert "default" in modes
    assert modes["default"]["session_count"] == 2
    assert modes["default"]["success_rate"] == 1.0
    assert "plan" in modes
    assert modes["plan"]["success_rate"] == 0.0


def test_session_insights_health_scores(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    # Good session
    _ingest_session(
        client,
        api_key,
        facets={"outcome": "success", "primary_success": "full"},
    )
    # Bad session
    _ingest_session(
        client,
        api_key,
        facets={
            "outcome": "failure",
            "primary_success": "none",
            "friction_counts": {"error": 3, "timeout": 2},
        },
    )

    r = client.get("/api/v1/analytics/session-insights", headers=admin_headers)
    data = r.json()
    health = data["health_distribution"]
    assert health["avg_score"] > 0
    assert health["median_score"] > 0
    total_buckets = sum(health["buckets"].values())
    assert total_buckets == 2


def test_session_insights_goals(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        facets={
            "outcome": "success",
            "session_type": "feature",
            "goal_categories": ["coding", "testing"],
        },
        model_usages=[
            {
                "model_name": "claude-sonnet-4-20250514",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_read_tokens": 0,
                "cache_creation_tokens": 0,
            }
        ],
    )
    _ingest_session(
        client,
        api_key,
        facets={
            "outcome": "partial",
            "session_type": "debugging",
            "goal_categories": ["coding"],
        },
    )

    r = client.get("/api/v1/analytics/session-insights", headers=admin_headers)
    data = r.json()
    goals = data["goals"]
    types = {t["session_type"]: t for t in goals["session_type_breakdown"]}
    assert "feature" in types
    assert types["feature"]["count"] == 1
    assert types["feature"]["success_rate"] == 1.0

    cats = {c["category"]: c for c in goals["goal_category_breakdown"]}
    assert "coding" in cats
    assert cats["coding"]["count"] == 2


def test_session_insights_goals_accept_legacy_success_outcomes(
    client, engineer_with_key, admin_headers, db_session
):
    _eng, api_key = engineer_with_key
    legacy_sid = _ingest_session(
        client,
        api_key,
        facets={
            "outcome": "success",
            "session_type": "feature",
            "goal_categories": ["coding"],
        },
    )
    _ingest_session(
        client,
        api_key,
        facets={
            "outcome": "failure",
            "session_type": "feature",
            "goal_categories": ["coding"],
        },
    )

    legacy_facets = (
        db_session.query(SessionFacets).filter(SessionFacets.session_id == legacy_sid).one()
    )
    legacy_facets.outcome = "fully_achieved"
    db_session.flush()

    r = client.get("/api/v1/analytics/session-insights", headers=admin_headers)
    data = r.json()
    goals = data["goals"]
    types = {t["session_type"]: t for t in goals["session_type_breakdown"]}
    cats = {c["category"]: c for c in goals["goal_category_breakdown"]}

    assert types["feature"]["success_rate"] == 0.5
    assert cats["coding"]["success_rate"] == 0.5


def test_session_insights_primary_success(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        facets={"session_type": "feature", "primary_success": "full"},
    )
    _ingest_session(
        client,
        api_key,
        facets={"session_type": "feature", "primary_success": "partial"},
    )
    _ingest_session(
        client,
        api_key,
        facets={"session_type": "debugging", "primary_success": "none"},
    )

    r = client.get("/api/v1/analytics/session-insights", headers=admin_headers)
    data = r.json()
    ps = data["primary_success"]
    assert ps["full_count"] == 1
    assert ps["partial_count"] == 1
    assert ps["none_count"] == 1
    assert ps["full_rate"] is not None
    assert "feature" in ps["by_session_type"]
    assert ps["by_session_type"]["feature"]["full"] == 1


def test_session_insights_primary_success_buckets_category_labels(
    client, engineer_with_key, admin_headers
):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        facets={"session_type": "feature", "primary_success": "correct_code_edits"},
    )
    _ingest_session(
        client,
        api_key,
        facets={"session_type": "feature", "primary_success": "multi_file_changes"},
    )
    _ingest_session(
        client,
        api_key,
        facets={"session_type": "debugging", "primary_success": "good_debugging"},
    )
    _ingest_session(
        client,
        api_key,
        facets={"session_type": "debugging", "primary_success": "none"},
    )

    r = client.get("/api/v1/analytics/session-insights", headers=admin_headers)
    data = r.json()
    ps = data["primary_success"]

    assert ps["full_count"] == 3
    assert ps["partial_count"] == 0
    assert ps["none_count"] == 1
    assert ps["unknown_count"] == 0
    assert ps["by_session_type"]["feature"]["full"] == 2
    assert ps["by_session_type"]["debugging"]["full"] == 1
    assert ps["by_session_type"]["debugging"]["none"] == 1


def test_session_insights_date_filtering(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    now = datetime.utcnow()
    old = now - timedelta(days=60)

    _ingest_session(
        client,
        api_key,
        started_at=old.isoformat(),
        ended_at=(old + timedelta(minutes=5)).isoformat(),
        end_reason="old_exit",
        facets={"outcome": "success"},
    )
    _ingest_session(
        client,
        api_key,
        started_at=now.isoformat(),
        ended_at=(now + timedelta(minutes=5)).isoformat(),
        end_reason="new_exit",
        facets={"outcome": "success"},
    )

    # Only recent sessions
    start = (now - timedelta(days=7)).isoformat()
    r = client.get(
        f"/api/v1/analytics/session-insights?start_date={start}",
        headers=admin_headers,
    )
    data = r.json()
    assert data["sessions_analyzed"] == 1
    reasons = [er["end_reason"] for er in data["end_reasons"]]
    assert "new_exit" in reasons
    assert "old_exit" not in reasons


def test_session_insights_team_scoping(client, engineer_with_key, admin_headers, db_session):
    """Team filter only includes team members."""
    import secrets

    import bcrypt

    from primer.common.models import Engineer, Team

    _eng, api_key = engineer_with_key
    team_id = _eng.team_id

    # Create another team + engineer
    other_team = Team(name="Other Team")
    db_session.add(other_team)
    db_session.flush()
    other_key = f"primer_{secrets.token_urlsafe(32)}"
    other_hash = bcrypt.hashpw(other_key.encode(), bcrypt.gensalt()).decode()
    other_eng = Engineer(
        name="Other Engineer",
        email="other@example.com",
        team_id=other_team.id,
        api_key_hash=other_hash,
    )
    db_session.add(other_eng)
    db_session.flush()

    _ingest_session(client, api_key, end_reason="team1", facets={"outcome": "success"})
    _ingest_session(client, other_key, end_reason="team2", facets={"outcome": "success"})

    r = client.get(
        f"/api/v1/analytics/session-insights?team_id={team_id}",
        headers=admin_headers,
    )
    data = r.json()
    assert data["sessions_analyzed"] == 1
    reasons = [er["end_reason"] for er in data["end_reasons"]]
    assert "team1" in reasons
    assert "team2" not in reasons


def test_overview_enrichment(client, engineer_with_key, admin_headers):
    _eng, api_key = engineer_with_key
    _ingest_session(
        client,
        api_key,
        end_reason="user_exit",
        cache_read_tokens=500,
        input_tokens=1000,
        model_usages=[
            {
                "model_name": "claude-sonnet-4-20250514",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_read_tokens": 500,
                "cache_creation_tokens": 0,
            }
        ],
        facets={"outcome": "success", "primary_success": "full"},
    )

    r = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "end_reason_counts" in data
    assert data["end_reason_counts"].get("user_exit") == 1
    assert "cache_hit_rate" in data
    assert data["cache_hit_rate"] is not None
    assert "avg_health_score" in data
    assert data["avg_health_score"] is not None


def test_health_score_computation():
    # Perfect session
    score = compute_session_health_score(
        outcome="success",
        friction_counts=None,
        duration_seconds=100,
        median_duration=100,
        satisfaction_counts={"satisfied": 5, "neutral": 0, "dissatisfied": 0},
        primary_success="full",
    )
    assert score == 100.0  # 100 + 5(sat) + 5(primary) = 110 clamped to 100

    # Terrible session
    score = compute_session_health_score(
        outcome="failure",
        friction_counts={"a": 1, "b": 1, "c": 1, "d": 1},
        duration_seconds=300,
        median_duration=100,
        satisfaction_counts={"satisfied": 0, "neutral": 0, "dissatisfied": 5},
        primary_success="failure",
    )
    # 100 - 40(failure) - 30(4 friction types capped 30) - 10(3x duration)
    # - 15(all dissatisfied) - 5(negative primary_success)
    assert score == 0.0

    # Missing outcome
    score = compute_session_health_score(
        outcome=None,
        friction_counts=None,
        duration_seconds=None,
        median_duration=None,
        satisfaction_counts=None,
        primary_success=None,
    )
    assert score == 90.0  # 100 - 10(missing outcome)


def test_health_score_uses_canonical_outcomes_and_primary_success_semantics():
    score = compute_session_health_score(
        outcome="not_achieved",
        friction_counts=None,
        duration_seconds=100,
        median_duration=100,
        satisfaction_counts=None,
        primary_success=None,
    )
    assert score == 60.0

    score = compute_session_health_score(
        outcome="partial",
        friction_counts=None,
        duration_seconds=100,
        median_duration=100,
        satisfaction_counts=None,
        primary_success="correct_code_edits",
    )
    assert score == 85.0

    score = compute_session_health_score(
        outcome="partial",
        friction_counts=None,
        duration_seconds=100,
        median_duration=100,
        satisfaction_counts=None,
        primary_success="some_new_positive_label",
    )
    assert score == 85.0

    score = compute_session_health_score(
        outcome="partial",
        friction_counts=None,
        duration_seconds=100,
        median_duration=100,
        satisfaction_counts=None,
        primary_success="failure",
    )
    assert score == 75.0
