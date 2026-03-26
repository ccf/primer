from datetime import timedelta
from types import SimpleNamespace

from primer.server.services.recap_service import get_personal_recaps


def test_personal_recaps_require_engineer_context(client, admin_headers):
    resp = client.get("/api/v1/analytics/personal-recaps", headers=admin_headers)
    assert resp.status_code == 400
    assert "engineer context" in resp.json()["detail"]


def test_get_personal_recaps_uses_daily_and_weekly_profile_data(monkeypatch):
    daily_profile = SimpleNamespace(
        overview=SimpleNamespace(total_sessions=2, success_rate=0.5, estimated_cost=1.2),
        friction=[SimpleNamespace(friction_type="tool_error", count=2)],
        tool_recommendations=[],
        model_recommendations=[],
        workflow_playbooks=[],
        impact_review=SimpleNamespace(
            strengths=["Closed a tough auth bug quickly."],
            focus_areas=["Reduce tool retries after failures."],
            top_workflows=[SimpleNamespace(archetype="debugging")],
            next_step_title="Reuse the debugging playbook",
            next_step_description="Start with the narrowest regression command first.",
        ),
    )
    weekly_profile = SimpleNamespace(
        overview=SimpleNamespace(total_sessions=7, success_rate=0.86, estimated_cost=5.4),
        friction=[],
        tool_recommendations=[],
        model_recommendations=[],
        workflow_playbooks=[],
        impact_review=SimpleNamespace(
            trajectory_signal="improving",
            strengths=["Success rate is climbing week over week."],
            focus_areas=[],
            top_workflows=[SimpleNamespace(archetype="feature_delivery")],
            next_step_title="Keep the delivery loop tight",
            next_step_description="Stick with the highest-confidence workflow this week.",
        ),
    )

    def fake_get_engineer_profile(db, engineer_id, start_date=None, end_date=None):
        window = (end_date - start_date) if start_date and end_date else timedelta(days=0)
        if window <= timedelta(days=1, minutes=1):
            return daily_profile
        return weekly_profile

    monkeypatch.setattr(
        "primer.server.services.recap_service.get_engineer_profile",
        fake_get_engineer_profile,
    )

    recaps = get_personal_recaps(db=None, engineer_id="eng-123")

    assert recaps.daily.period == "daily"
    assert recaps.daily.sessions_analyzed == 2
    assert recaps.daily.top_workflow == "Debugging"
    assert recaps.daily.wins == ["Closed a tough auth bug quickly."]
    assert recaps.daily.watchouts[0] == "tool_error showed up 2 times."
    assert "Reuse the debugging playbook" in recaps.daily.next_steps[0]

    assert recaps.weekly.period == "weekly"
    assert recaps.weekly.headline == "Your weekly momentum is improving"
    assert recaps.weekly.top_workflow == "Feature Delivery"
    assert recaps.weekly.wins == ["Success rate is climbing week over week."]


def test_get_personal_recaps_handles_no_sessions(monkeypatch):
    empty_profile = SimpleNamespace(
        overview=SimpleNamespace(total_sessions=0, success_rate=None, estimated_cost=None),
        friction=[],
        tool_recommendations=[],
        model_recommendations=[],
        workflow_playbooks=[],
        impact_review=None,
    )
    monkeypatch.setattr(
        "primer.server.services.recap_service.get_engineer_profile",
        lambda *args, **kwargs: empty_profile,
    )

    recaps = get_personal_recaps(db=None, engineer_id="eng-123")

    assert recaps.daily.sessions_analyzed == 0
    assert "No captured sessions" in recaps.daily.headline
    assert recaps.weekly.sessions_analyzed == 0
