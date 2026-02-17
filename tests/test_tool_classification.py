from primer.common.tool_classification import (
    classify_tool,
    classify_tools,
    compute_leverage_score,
)


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


def test_leverage_score_empty():
    assert compute_leverage_score({}) == 0.0


def test_leverage_score_core_only():
    score = compute_leverage_score({"Read": 100, "Write": 50})
    # 1 category out of 5 = 20% spread, some diversity, no orchestration, no cache
    assert 0 < score < 30


def test_leverage_score_diverse():
    score = compute_leverage_score(
        {
            "Read": 10,
            "Glob": 5,
            "Task:explore": 8,
            "Skill:commit": 4,
            "custom_mcp": 3,
        },
        cache_hit_rate=0.6,
    )
    # All 5 categories, good diversity, orchestration+skill ratio, cache
    assert score > 50


def test_leverage_score_max_100():
    score = compute_leverage_score(
        {
            "Read": 1,
            "Glob": 1,
            "Task:explore": 1,
            "Skill:commit": 1,
            "custom": 1,
        },
        cache_hit_rate=1.0,
    )
    assert score <= 100.0
