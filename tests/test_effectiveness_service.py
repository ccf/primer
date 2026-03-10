import pytest

from primer.server.services.effectiveness_service import build_effectiveness_score


def test_effectiveness_score_requires_outcome_signal():
    score = build_effectiveness_score(
        success_rate=None,
        cost_per_successful_outcome=2.0,
        benchmark_cost_per_successful_outcome=2.5,
        pr_merge_rate=None,
        findings_fix_rate=None,
        total_sessions=4,
        sessions_with_commits=2,
    )

    assert score.score is None
    assert score.breakdown.success_rate is None
    assert score.breakdown.follow_through == 0.5


def test_effectiveness_score_blends_success_quality_follow_through_and_cost():
    score = build_effectiveness_score(
        success_rate=0.8,
        cost_per_successful_outcome=1.0,
        benchmark_cost_per_successful_outcome=2.0,
        pr_merge_rate=1.0,
        findings_fix_rate=0.5,
        total_sessions=10,
        sessions_with_commits=6,
    )

    assert score.score == pytest.approx(78.8, abs=0.1)
    assert score.breakdown.success_rate == 0.8
    assert score.breakdown.cost_efficiency == 1.0
    assert score.breakdown.quality_outcomes == 0.75
    assert score.breakdown.follow_through == 0.6


def test_effectiveness_score_is_capped_at_100():
    score = build_effectiveness_score(
        success_rate=1.2,
        cost_per_successful_outcome=0.25,
        benchmark_cost_per_successful_outcome=2.0,
        pr_merge_rate=1.0,
        findings_fix_rate=1.0,
        total_sessions=2,
        sessions_with_commits=4,
    )

    assert score.score == 100.0
    assert score.breakdown.success_rate == 1.0
    assert score.breakdown.follow_through == 1.0


def test_effectiveness_score_clamps_follow_through_before_weighting():
    score = build_effectiveness_score(
        success_rate=0.5,
        cost_per_successful_outcome=None,
        benchmark_cost_per_successful_outcome=None,
        pr_merge_rate=None,
        findings_fix_rate=None,
        total_sessions=2,
        sessions_with_commits=4,
    )

    assert score.score == pytest.approx(68.2, abs=0.1)
    assert score.breakdown.success_rate == 0.5
    assert score.breakdown.follow_through == 1.0
