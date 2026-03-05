"""Classify Claude Code tools into categories and compute leverage/effectiveness scores."""

import math

CORE_TOOLS = {"Read", "Write", "Edit", "Bash", "NotebookEdit"}
SEARCH_TOOLS = {"Glob", "Grep", "WebSearch", "WebFetch"}
ORCHESTRATION_TOOLS = {"Task", "EnterPlanMode", "ExitPlanMode", "AskUserQuestion"}
TEAM_TOOLS = {"TeamCreate", "TeamDelete", "SendMessage", "EnterWorktree"}
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
    if name in ORCHESTRATION_TOOLS or name in TEAM_TOOLS:
        return "orchestration"
    return "mcp"


def classify_tools(tool_counts: dict[str, int]) -> dict[str, dict[str, int]]:
    """Group tool counts by category."""
    result: dict[str, dict[str, int]] = {cat: {} for cat in CATEGORIES}
    for name, count in tool_counts.items():
        cat = classify_tool(name)
        result[cat][name] = count
    return result


def _shannon_entropy(counts: dict[str, int]) -> float:
    """Compute normalized Shannon entropy (0-1) for a distribution."""
    total = sum(counts.values())
    n = len(counts)
    if n <= 1 or total == 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    max_entropy = math.log2(n)
    return entropy / max_entropy if max_entropy > 0 else 0.0


def compute_model_diversity(
    model_token_counts: dict[str, int],
    model_tier_counts: dict[str, int] | None = None,
) -> float:
    """Compute 0-1 model diversity score.

    50% weight: Shannon entropy of model usage distribution (by tokens)
    50% weight: cost tier coverage (how many of 4 tiers used, normalized)
    """
    if not model_token_counts or sum(model_token_counts.values()) == 0:
        return 0.0

    model_entropy = _shannon_entropy(model_token_counts)

    if model_tier_counts:
        tiers_used = sum(1 for v in model_tier_counts.values() if v > 0)
        tier_diversity = min(tiers_used / 4.0, 1.0)
    else:
        tier_diversity = 0.0

    return 0.5 * model_entropy + 0.5 * tier_diversity


def compute_agent_team_score(tool_counts: dict[str, int]) -> float:
    """Compute 0-1 score for multi-agent team orchestration depth.

    0.0: No team tools used
    0.3: Uses SendMessage or Agent (basic delegation)
    0.6: Uses TeamCreate (team setup)
    1.0: Uses TeamCreate + SendMessage + 5+ total team calls
    """
    team_calls = {
        name: count for name, count in tool_counts.items() if name in TEAM_TOOLS or name == "Agent"
    }
    if not team_calls:
        return 0.0

    has_team_create = "TeamCreate" in team_calls
    has_send_message = "SendMessage" in team_calls
    total_team_calls = sum(team_calls.values())

    if has_team_create and has_send_message and total_team_calls >= 5:
        return 1.0
    if has_team_create:
        return 0.6
    if has_send_message or "Agent" in team_calls:
        return 0.3
    # TeamDelete or EnterWorktree alone aren't meaningful team signals
    return 0.0


def compute_leverage_score(
    tool_counts: dict[str, int],
    cache_hit_rate: float | None = None,
    model_token_counts: dict[str, int] | None = None,
    model_tier_counts: dict[str, int] | None = None,
) -> tuple[float, dict[str, float]]:
    """Compute a 0-100 composite leverage score with sub-score breakdown.

    Three sub-scores (33.3% each):
    - Tool Mastery: tool diversity (entropy) + category spread
    - Orchestration Depth: orch+skill ratio + agent team score (bonus)
    - Efficiency: cache hit rate + model diversity

    Returns (score, breakdown) where breakdown contains all factor values.
    """
    empty: dict[str, float] = {}
    if not tool_counts:
        return 0.0, empty

    total_calls = sum(tool_counts.values())
    if total_calls == 0:
        return 0.0, empty

    # --- Tool Mastery (33.3%) ---
    diversity = _shannon_entropy(tool_counts)

    classified = classify_tools(tool_counts)
    categories_used = sum(1 for cat in CATEGORIES if classified[cat])
    spread = categories_used / len(CATEGORIES)

    tool_mastery = 0.5 * diversity + 0.5 * spread

    # --- Orchestration Depth (33.3%) ---
    orch_skill_calls = sum(classified["orchestration"].values()) + sum(classified["skill"].values())
    orch_ratio = min(orch_skill_calls / total_calls, 1.0)

    agent_team = compute_agent_team_score(tool_counts)

    # Bonus: teams can only help, never hurt. Use max to ensure no penalty.
    blended_orch = 0.5 * orch_ratio + 0.5 * agent_team
    orchestration_depth = max(blended_orch, orch_ratio) if agent_team > 0 else orch_ratio

    # --- Efficiency (33.3%) ---
    cache = cache_hit_rate if cache_hit_rate is not None else 0.0
    model_div = compute_model_diversity(model_token_counts or {}, model_tier_counts)

    # Bonus: model diversity can only help, never hurt. Use max to ensure no penalty.
    blended_eff = 0.5 * cache + 0.5 * model_div
    efficiency = max(blended_eff, cache) if model_token_counts else cache

    score = (100 / 3) * tool_mastery + (100 / 3) * orchestration_depth + (100 / 3) * efficiency
    score = round(min(score, 100.0), 1)

    breakdown = {
        "tool_diversity": round(diversity, 3),
        "category_spread": round(spread, 3),
        "tool_mastery": round(tool_mastery, 3),
        "orch_skill_ratio": round(orch_ratio, 3),
        "agent_team_score": round(agent_team, 3),
        "orchestration_depth": round(orchestration_depth, 3),
        "cache_efficiency": round(cache, 3),
        "model_diversity": round(model_div, 3),
        "efficiency": round(efficiency, 3),
    }

    return score, breakdown


def compute_effectiveness_score(
    success_rate: float | None,
    cost_per_success: float | None,
    team_median_cost_per_success: float | None,
    avg_health_score: float | None,
) -> tuple[float, dict[str, float | None]]:
    """Compute a 0-100 effectiveness score measuring outcomes.

    Weighted components:
    - Success rate (40%)
    - Cost efficiency vs team median (30%)
    - Session health (30%)

    Components with None data are excluded and weights are renormalized.
    """
    components: dict[str, float | None] = {}
    weights: list[tuple[float, float]] = []

    if success_rate is not None:
        components["success_rate"] = round(success_rate, 3)
        weights.append((success_rate, 40))

    if (
        cost_per_success is not None
        and team_median_cost_per_success is not None
        and team_median_cost_per_success > 0
    ):
        ratio = cost_per_success / team_median_cost_per_success
        cost_score = max(0.0, min(1.0, 1.0 - (ratio - 0.5) / 1.5))
        components["cost_efficiency"] = round(cost_score, 3)
        weights.append((cost_score, 30))
    else:
        components["cost_efficiency"] = None

    if avg_health_score is not None:
        health = avg_health_score / 100.0
        components["session_health"] = round(health, 3)
        weights.append((health, 30))
    else:
        components["session_health"] = None

    if not weights:
        return 0.0, components

    total_weight = sum(w for _, w in weights)
    score = sum(s * w for s, w in weights) / total_weight * 100
    score = round(min(score, 100.0), 1)

    return score, components
