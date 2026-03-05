import pytest

from primer.common.pricing import get_cost_tier
from primer.common.tool_classification import (
    classify_tool,
    classify_tools,
    compute_agent_team_score,
    compute_effectiveness_score,
    compute_leverage_score,
    compute_model_diversity,
)

# --- classify_tool ---


def test_classify_core_tools():
    for name in ("Read", "Write", "Edit", "Bash", "NotebookEdit"):
        assert classify_tool(name) == "core"


def test_classify_search_tools():
    for name in ("Glob", "Grep", "WebSearch", "WebFetch"):
        assert classify_tool(name) == "search"


def test_classify_orchestration():
    assert classify_tool("Task") == "orchestration"
    assert classify_tool("Task:explore") == "orchestration"
    assert classify_tool("Task:python-pro") == "orchestration"
    assert classify_tool("EnterPlanMode") == "orchestration"
    assert classify_tool("ExitPlanMode") == "orchestration"
    assert classify_tool("AskUserQuestion") == "orchestration"


def test_classify_team_tools_as_orchestration():
    assert classify_tool("TeamCreate") == "orchestration"
    assert classify_tool("SendMessage") == "orchestration"
    assert classify_tool("TeamDelete") == "orchestration"
    assert classify_tool("EnterWorktree") == "orchestration"


def test_classify_skills():
    assert classify_tool("Skill") == "skill"
    assert classify_tool("Skill:commit") == "skill"
    assert classify_tool("Skill:review-pr") == "skill"


def test_classify_mcp_tools():
    assert classify_tool("unknown_tool") == "mcp"
    assert classify_tool("my_custom_tool") == "mcp"


def test_classify_tools_groups():
    counts = {"Read": 10, "Glob": 5, "Task:explore": 3, "Skill:commit": 2, "custom": 1}
    result = classify_tools(counts)
    assert result["core"] == {"Read": 10}
    assert result["search"] == {"Glob": 5}
    assert result["orchestration"] == {"Task:explore": 3}
    assert result["skill"] == {"Skill:commit": 2}
    assert result["mcp"] == {"custom": 1}


# --- get_cost_tier ---


def test_cost_tier_economy():
    assert get_cost_tier("gemini-2.0-flash") == "economy"
    assert get_cost_tier("gpt-4.1-nano") == "economy"


def test_cost_tier_standard():
    assert get_cost_tier("claude-haiku-4-5") == "standard"
    assert get_cost_tier("gemini-2.5-pro") == "standard"


def test_cost_tier_premium():
    assert get_cost_tier("claude-opus-4-5") == "premium"
    assert get_cost_tier("claude-opus-4-6") == "premium"


def test_cost_tier_flagship():
    assert get_cost_tier("claude-opus-4") == "flagship"
    assert get_cost_tier("o1") == "flagship"


# --- compute_model_diversity ---


def test_model_diversity_empty():
    assert compute_model_diversity({}) == 0.0


def test_model_diversity_single_model():
    score = compute_model_diversity(
        {"claude-sonnet-4": 1000},
        {"standard": 1000},
    )
    # 0 entropy + 1/4 tier coverage = 0.125
    assert score == pytest.approx(0.125, abs=0.01)


def test_model_diversity_multi_model_multi_tier():
    score = compute_model_diversity(
        {"claude-haiku-4-5": 500, "claude-sonnet-4": 300, "claude-opus-4-5": 200},
        {"economy": 500, "standard": 300, "premium": 200},
    )
    assert score > 0.6


def test_model_diversity_same_tier():
    score = compute_model_diversity(
        {"claude-sonnet-4": 500, "claude-sonnet-3.5": 500},
        {"standard": 1000},
    )
    assert 0.3 < score < 0.7


# --- compute_agent_team_score ---


def test_agent_team_no_teams():
    assert compute_agent_team_score({"Read": 10, "Write": 5}) == 0.0


def test_agent_team_basic_delegation():
    assert compute_agent_team_score({"Read": 10, "SendMessage": 2}) == 0.3


def test_agent_team_with_agent():
    assert compute_agent_team_score({"Read": 10, "Agent": 3}) == 0.3


def test_agent_team_create():
    assert compute_agent_team_score({"TeamCreate": 1, "Read": 10}) == 0.6


def test_agent_team_full_orchestration():
    score = compute_agent_team_score({"TeamCreate": 1, "SendMessage": 4, "Agent": 2, "Read": 10})
    assert score == 1.0


def test_agent_team_insufficient_calls():
    score = compute_agent_team_score({"TeamCreate": 1, "SendMessage": 1, "Read": 10})
    assert score == 0.6


# --- compute_leverage_score ---


def test_leverage_score_empty():
    score, breakdown = compute_leverage_score({})
    assert score == 0.0
    assert breakdown == {}


def test_leverage_score_returns_tuple():
    result = compute_leverage_score({"Read": 10})
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], float)
    assert isinstance(result[1], dict)


def test_leverage_score_core_only():
    score, _ = compute_leverage_score({"Read": 100, "Write": 50})
    assert 0 < score < 30


def test_leverage_score_diverse():
    score, _ = compute_leverage_score(
        {
            "Read": 10,
            "Glob": 5,
            "Task:explore": 8,
            "Skill:commit": 4,
            "custom_mcp": 3,
        },
        cache_hit_rate=0.6,
    )
    assert score > 50


def test_leverage_score_max_100():
    score, _ = compute_leverage_score(
        {"Read": 1, "Glob": 1, "Task:explore": 1, "Skill:commit": 1, "custom": 1},
        cache_hit_rate=1.0,
    )
    assert score <= 100.0


def test_leverage_breakdown_keys():
    _, breakdown = compute_leverage_score(
        {"Read": 10, "Task:explore": 5},
        cache_hit_rate=0.3,
    )
    expected_keys = {
        "tool_diversity",
        "category_spread",
        "tool_mastery",
        "orch_skill_ratio",
        "agent_team_score",
        "orchestration_depth",
        "cache_efficiency",
        "model_diversity",
        "efficiency",
    }
    assert set(breakdown.keys()) == expected_keys


def test_leverage_backward_compat_no_model_data():
    score, bd = compute_leverage_score(
        {"Read": 10, "Glob": 5, "Task:explore": 3},
        cache_hit_rate=0.5,
    )
    assert 0 < score <= 100
    assert bd["model_diversity"] == 0.0
    assert bd["cache_efficiency"] == 0.5
    assert bd["efficiency"] == 0.5  # cache only when no model data


def test_leverage_with_model_diversity():
    _, bd_no_model = compute_leverage_score(
        {"Read": 10, "Glob": 5},
        cache_hit_rate=0.3,
    )
    _, bd_with_model = compute_leverage_score(
        {"Read": 10, "Glob": 5},
        cache_hit_rate=0.3,
        model_token_counts={"claude-haiku-4-5": 500, "claude-opus-4-5": 500},
        model_tier_counts={"economy": 500, "premium": 500},
    )
    assert bd_with_model["model_diversity"] > 0
    assert bd_with_model["efficiency"] != bd_no_model["efficiency"]


def test_leverage_with_teams_bonus():
    score_no_team, _ = compute_leverage_score({"Read": 10, "Task:explore": 5})
    score_with_team, bd = compute_leverage_score(
        {"Read": 10, "Task:explore": 5, "TeamCreate": 1, "SendMessage": 5, "Agent": 2}
    )
    assert bd["agent_team_score"] == 1.0
    assert score_with_team >= score_no_team


def test_teams_never_penalize():
    """Low agent_team score should not reduce orchestration_depth below orch_ratio."""
    # High orch ratio (50% of calls are orchestration)
    _, bd_no_team = compute_leverage_score({"Read": 5, "Task:explore": 5})
    # Add SendMessage (agent_team=0.3) which is below orch_ratio
    _, bd_with_team = compute_leverage_score({"Read": 5, "Task:explore": 5, "SendMessage": 1})
    assert bd_with_team["orchestration_depth"] >= bd_no_team["orchestration_depth"]


def test_model_diversity_never_penalizes():
    """Low model diversity should not reduce efficiency below cache-only."""
    _, bd_no_model = compute_leverage_score({"Read": 10}, cache_hit_rate=0.6)
    # Single model = low diversity, but should not hurt
    _, bd_with_model = compute_leverage_score(
        {"Read": 10},
        cache_hit_rate=0.6,
        model_token_counts={"claude-sonnet-4": 1000},
        model_tier_counts={"standard": 1000},
    )
    assert bd_with_model["efficiency"] >= bd_no_model["efficiency"]


# --- compute_effectiveness_score ---


def test_effectiveness_no_data():
    score, _breakdown = compute_effectiveness_score(None, None, None, None)
    assert score == 0.0


def test_effectiveness_success_only():
    score, breakdown = compute_effectiveness_score(
        success_rate=0.8,
        cost_per_success=None,
        team_median_cost_per_success=None,
        avg_health_score=None,
    )
    assert score == pytest.approx(80.0, abs=0.1)
    assert breakdown["success_rate"] == 0.8


def test_effectiveness_with_cost():
    score, breakdown = compute_effectiveness_score(
        success_rate=0.7,
        cost_per_success=1.50,
        team_median_cost_per_success=2.00,
        avg_health_score=None,
    )
    assert score > 60.0
    assert breakdown["cost_efficiency"] is not None


def test_effectiveness_expensive_vs_cheap():
    score_cheap, _ = compute_effectiveness_score(
        success_rate=0.7,
        cost_per_success=0.50,
        team_median_cost_per_success=2.00,
        avg_health_score=None,
    )
    score_expensive, _ = compute_effectiveness_score(
        success_rate=0.7,
        cost_per_success=4.00,
        team_median_cost_per_success=2.00,
        avg_health_score=None,
    )
    assert score_cheap > score_expensive


def test_effectiveness_with_health():
    score, breakdown = compute_effectiveness_score(
        success_rate=0.7,
        cost_per_success=None,
        team_median_cost_per_success=None,
        avg_health_score=80.0,
    )
    assert score > 0
    assert breakdown["session_health"] == 0.8
