import secrets
from types import SimpleNamespace

import bcrypt

from primer.common.models import Engineer, Team
from primer.common.schemas import ManagerReviewPack, ManagerReviewSection
from primer.server.services.manager_review_service import get_weekly_manager_review_pack


def _make_engineer(db_session, team, *, name="Lead", email=None, role="engineer"):
    raw_key = f"primer_{secrets.token_urlsafe(32)}"
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    eng = Engineer(
        name=name,
        email=email or f"{name.lower().replace(' ', '.')}@example.com",
        team_id=team.id,
        api_key_hash=hashed,
        role=role,
    )
    db_session.add(eng)
    db_session.flush()
    return eng, raw_key


def test_weekly_manager_review_pack_builds_sections(monkeypatch, db_session):
    team = Team(name="Platform")
    db_session.add(team)
    db_session.flush()

    overview_calls = {"count": 0}

    def fake_overview(*args, **kwargs):
        overview_calls["count"] += 1
        if overview_calls["count"] == 1:
            return SimpleNamespace(total_sessions=12, success_rate=0.75)
        return SimpleNamespace(total_sessions=8, success_rate=0.6)

    monkeypatch.setattr(
        "primer.server.services.manager_review_service.get_overview",
        fake_overview,
    )

    calls = {"productivity": 0, "quality": 0, "friction": 0}

    def fake_productivity(*args, **kwargs):
        calls["productivity"] += 1
        if calls["productivity"] == 1:
            return SimpleNamespace(cost_per_successful_outcome=2.0)
        return SimpleNamespace(cost_per_successful_outcome=2.5)

    def fake_quality(*args, **kwargs):
        calls["quality"] += 1
        if calls["quality"] == 1:
            return SimpleNamespace(
                overview=SimpleNamespace(total_prs=5, pr_merge_rate=0.8),
                findings_overview=SimpleNamespace(fix_rate=0.75),
            )
        return SimpleNamespace(
            overview=SimpleNamespace(total_prs=4, pr_merge_rate=0.6),
            findings_overview=SimpleNamespace(fix_rate=0.5),
        )

    def fake_friction(*args, **kwargs):
        calls["friction"] += 1
        if calls["friction"] == 1:
            return [
                SimpleNamespace(friction_type="tool_error", count=4),
                SimpleNamespace(friction_type="timeout", count=2),
            ]
        return [SimpleNamespace(friction_type="tool_error", count=1)]

    monkeypatch.setattr(
        "primer.server.services.manager_review_service.get_productivity_metrics",
        fake_productivity,
    )
    monkeypatch.setattr(
        "primer.server.services.manager_review_service.get_quality_metrics",
        fake_quality,
    )
    monkeypatch.setattr(
        "primer.server.services.manager_review_service.get_friction_report",
        fake_friction,
    )
    monkeypatch.setattr(
        "primer.server.services.manager_review_service.get_cost_analytics",
        lambda *args, **kwargs: SimpleNamespace(
            total_estimated_cost=23.5,
            workflow_breakdown=[SimpleNamespace(label="debugging", total_estimated_cost=10.2)],
        ),
    )
    monkeypatch.setattr(
        "primer.server.services.manager_review_service.get_skill_inventory",
        lambda *args, **kwargs: SimpleNamespace(
            total_engineers=4,
            team_skill_gaps=[
                SimpleNamespace(
                    skill="Task",
                    coverage_pct=25.0,
                    engineers_with_skill=1,
                    total_engineers=4,
                )
            ],
        ),
    )
    monkeypatch.setattr(
        "primer.server.services.manager_review_service.get_recommendations",
        lambda *args, **kwargs: [
            SimpleNamespace(
                title="Reduce tool retries",
                description="Adopt the debugging playbook before escalating.",
                narrative=SimpleNamespace(
                    why_this_helps="It cuts the most common failure loop earlier.",
                    expected_impact="Fewer tool-error retries next week.",
                ),
            )
        ],
    )

    pack = get_weekly_manager_review_pack(db_session, team_id=team.id, days=14)

    assert pack.scope == "team"
    assert pack.scope_label == "Platform"
    assert pack.sessions_analyzed == 12
    assert [section.title for section in pack.sections] == [
        "Quality",
        "Friction",
        "Growth",
        "Cost",
    ]
    assert "Merge rate: 80% (up 20% vs prior 14-day window)" in pack.sections[0].bullets
    assert "Reduce tool retries" in pack.recommended_actions[0]
    assert (
        "Why this helps: It cuts the most common failure loop earlier."
        in pack.recommended_actions[0]
    )
    assert "Platform logged 12 sessions" in pack.headline
    assert "prior 14-day window" in pack.headline


def test_manager_review_pack_route_requires_leadership(client, engineer_with_key):
    _eng, key = engineer_with_key

    resp = client.get("/api/v1/analytics/manager-review-pack", headers={"x-api-key": key})

    assert resp.status_code == 403


def test_manager_review_pack_team_lead_is_scoped_to_own_team(client, db_session, monkeypatch):
    team = Team(name="Scoped Team")
    other_team = Team(name="Other Team")
    db_session.add_all([team, other_team])
    db_session.flush()
    _lead, key = _make_engineer(db_session, team, name="Scoped Lead", role="team_lead")

    captured: dict[str, str | None] = {}

    def fake_pack(db, *, team_id=None, start_date=None, end_date=None, days=7):
        captured["team_id"] = team_id
        return ManagerReviewPack(
            scope="team",
            scope_label="Scoped Team",
            period_start="2026-03-20",
            period_end="2026-03-27",
            sessions_analyzed=3,
            headline="Scoped Team logged 3 sessions",
            sections=[ManagerReviewSection(title="Quality", summary="ok", bullets=[])],
            recommended_actions=["Review the top friction item."],
            generated_at="2026-03-27T00:00:00Z",
        )

    monkeypatch.setattr(
        "primer.server.services.manager_review_service.get_weekly_manager_review_pack",
        fake_pack,
    )

    resp = client.get(
        "/api/v1/analytics/manager-review-pack",
        params={"team_id": other_team.id},
        headers={"x-api-key": key},
    )

    assert resp.status_code == 200
    assert captured["team_id"] == team.id
