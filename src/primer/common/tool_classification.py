"""Classify Claude Code tools into categories and compute leverage scores."""

import math

CORE_TOOLS = {"Read", "Write", "Edit", "Bash", "NotebookEdit"}
SEARCH_TOOLS = {"Glob", "Grep", "WebSearch", "WebFetch"}
ORCHESTRATION_TOOLS = {"Task", "EnterPlanMode", "ExitPlanMode", "AskUserQuestion"}
SKILL_PREFIX = "Skill:"
TASK_PREFIX = "Task:"

CATEGORIES = ("core", "search", "orchestration", "skill", "mcp")


def classify_tool(name: str) -> str:
    """Classify a single tool name into a category."""
    if name.startswith(TASK_PREFIX):
        return "orchestration"
    if name == "Skill" or name.startswith(SKILL_PREFIX):
        return "skill"
    if name in CORE_TOOLS:
        return "core"
    if name in SEARCH_TOOLS:
        return "search"
    if name in ORCHESTRATION_TOOLS:
        return "orchestration"
    return "mcp"


def classify_tools(tool_counts: dict[str, int]) -> dict[str, dict[str, int]]:
    """Group tool counts by category."""
    result: dict[str, dict[str, int]] = {cat: {} for cat in CATEGORIES}
    for name, count in tool_counts.items():
        cat = classify_tool(name)
        result[cat][name] = count
    return result


def compute_leverage_score(
    tool_counts: dict[str, int], cache_hit_rate: float | None = None
) -> float:
    """Compute a 0-100 composite leverage score.

    Components (25% each):
    - Tool diversity (Shannon entropy normalized)
    - Category spread (how many of 5 categories used)
    - Orchestration + skill ratio
    - Cache efficiency
    """
    if not tool_counts:
        return 0.0

    total_calls = sum(tool_counts.values())
    if total_calls == 0:
        return 0.0

    # 1. Tool diversity — Shannon entropy normalized to 0-1
    n_tools = len(tool_counts)
    if n_tools <= 1:
        diversity = 0.0
    else:
        entropy = 0.0
        for count in tool_counts.values():
            p = count / total_calls
            if p > 0:
                entropy -= p * math.log2(p)
        max_entropy = math.log2(n_tools)
        diversity = entropy / max_entropy if max_entropy > 0 else 0.0

    # 2. Category spread — proportion of 5 categories used
    classified = classify_tools(tool_counts)
    categories_used = sum(1 for cat in CATEGORIES if classified[cat])
    spread = categories_used / len(CATEGORIES)

    # 3. Orchestration + skill ratio
    orch_skill_calls = sum(classified["orchestration"].values()) + sum(classified["skill"].values())
    orch_ratio = min(orch_skill_calls / total_calls, 1.0)

    # 4. Cache efficiency
    cache = cache_hit_rate if cache_hit_rate is not None else 0.0

    score = 25 * diversity + 25 * spread + 25 * orch_ratio + 25 * cache
    return round(min(score, 100.0), 1)
