from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_per_token: float
    output_per_token: float
    cache_read_per_token: float
    cache_creation_per_token: float


# Prices per token (derived from published per-MTok pricing)
# Cache conventions: Anthropic cache_read=0.1x input, cache_creation=1.25x input (5m writes)
#                    OpenAI/Google cache_read=0.25x input, cache_creation=1x input
MODEL_PRICING: dict[str, ModelPricing] = {
    # --- Anthropic (Claude Code) ---
    "claude-opus-4-6": ModelPricing(
        input_per_token=5.0 / 1_000_000,
        output_per_token=25.0 / 1_000_000,
        cache_read_per_token=0.50 / 1_000_000,
        cache_creation_per_token=6.25 / 1_000_000,
    ),
    "claude-opus-4-5": ModelPricing(
        input_per_token=5.0 / 1_000_000,
        output_per_token=25.0 / 1_000_000,
        cache_read_per_token=0.50 / 1_000_000,
        cache_creation_per_token=6.25 / 1_000_000,
    ),
    "claude-opus-4": ModelPricing(
        input_per_token=15.0 / 1_000_000,
        output_per_token=75.0 / 1_000_000,
        cache_read_per_token=1.50 / 1_000_000,
        cache_creation_per_token=18.75 / 1_000_000,
    ),
    "claude-sonnet-4": ModelPricing(
        input_per_token=3.0 / 1_000_000,
        output_per_token=15.0 / 1_000_000,
        cache_read_per_token=0.30 / 1_000_000,
        cache_creation_per_token=3.75 / 1_000_000,
    ),
    "claude-sonnet-3.5": ModelPricing(
        input_per_token=3.0 / 1_000_000,
        output_per_token=15.0 / 1_000_000,
        cache_read_per_token=0.30 / 1_000_000,
        cache_creation_per_token=3.75 / 1_000_000,
    ),
    "claude-haiku-4-5": ModelPricing(
        input_per_token=1.0 / 1_000_000,
        output_per_token=5.0 / 1_000_000,
        cache_read_per_token=0.10 / 1_000_000,
        cache_creation_per_token=1.25 / 1_000_000,
    ),
    "claude-haiku-3.5": ModelPricing(
        input_per_token=0.80 / 1_000_000,
        output_per_token=4.0 / 1_000_000,
        cache_read_per_token=0.08 / 1_000_000,
        cache_creation_per_token=1.0 / 1_000_000,
    ),
    # --- OpenAI (Codex CLI) ---
    "gpt-5.3-codex": ModelPricing(
        input_per_token=1.75 / 1_000_000,
        output_per_token=14.0 / 1_000_000,
        cache_read_per_token=0.4375 / 1_000_000,
        cache_creation_per_token=1.75 / 1_000_000,
    ),
    "gpt-5.2": ModelPricing(
        input_per_token=1.75 / 1_000_000,
        output_per_token=14.0 / 1_000_000,
        cache_read_per_token=0.4375 / 1_000_000,
        cache_creation_per_token=1.75 / 1_000_000,
    ),
    "gpt-5-mini": ModelPricing(
        input_per_token=0.25 / 1_000_000,
        output_per_token=2.0 / 1_000_000,
        cache_read_per_token=0.0625 / 1_000_000,
        cache_creation_per_token=0.25 / 1_000_000,
    ),
    "gpt-5": ModelPricing(
        input_per_token=1.25 / 1_000_000,
        output_per_token=10.0 / 1_000_000,
        cache_read_per_token=0.3125 / 1_000_000,
        cache_creation_per_token=1.25 / 1_000_000,
    ),
    "gpt-4o-mini": ModelPricing(
        input_per_token=0.15 / 1_000_000,
        output_per_token=0.60 / 1_000_000,
        cache_read_per_token=0.0375 / 1_000_000,
        cache_creation_per_token=0.15 / 1_000_000,
    ),
    "gpt-4o": ModelPricing(
        input_per_token=2.50 / 1_000_000,
        output_per_token=10.0 / 1_000_000,
        cache_read_per_token=0.625 / 1_000_000,
        cache_creation_per_token=2.50 / 1_000_000,
    ),
    "gpt-4.1": ModelPricing(
        input_per_token=2.0 / 1_000_000,
        output_per_token=8.0 / 1_000_000,
        cache_read_per_token=0.50 / 1_000_000,
        cache_creation_per_token=2.0 / 1_000_000,
    ),
    "gpt-4.1-mini": ModelPricing(
        input_per_token=0.40 / 1_000_000,
        output_per_token=1.60 / 1_000_000,
        cache_read_per_token=0.10 / 1_000_000,
        cache_creation_per_token=0.40 / 1_000_000,
    ),
    "gpt-4.1-nano": ModelPricing(
        input_per_token=0.10 / 1_000_000,
        output_per_token=0.40 / 1_000_000,
        cache_read_per_token=0.025 / 1_000_000,
        cache_creation_per_token=0.10 / 1_000_000,
    ),
    "o3-mini": ModelPricing(
        input_per_token=1.10 / 1_000_000,
        output_per_token=4.40 / 1_000_000,
        cache_read_per_token=0.275 / 1_000_000,
        cache_creation_per_token=1.10 / 1_000_000,
    ),
    "o3": ModelPricing(
        input_per_token=2.0 / 1_000_000,
        output_per_token=8.0 / 1_000_000,
        cache_read_per_token=0.50 / 1_000_000,
        cache_creation_per_token=2.0 / 1_000_000,
    ),
    "o4-mini": ModelPricing(
        input_per_token=1.10 / 1_000_000,
        output_per_token=4.40 / 1_000_000,
        cache_read_per_token=0.275 / 1_000_000,
        cache_creation_per_token=1.10 / 1_000_000,
    ),
    "o1-mini": ModelPricing(
        input_per_token=1.10 / 1_000_000,
        output_per_token=4.40 / 1_000_000,
        cache_read_per_token=0.275 / 1_000_000,
        cache_creation_per_token=1.10 / 1_000_000,
    ),
    "o1": ModelPricing(
        input_per_token=15.0 / 1_000_000,
        output_per_token=60.0 / 1_000_000,
        cache_read_per_token=3.75 / 1_000_000,
        cache_creation_per_token=15.0 / 1_000_000,
    ),
    "codex-mini": ModelPricing(
        input_per_token=1.50 / 1_000_000,
        output_per_token=6.0 / 1_000_000,
        cache_read_per_token=0.375 / 1_000_000,
        cache_creation_per_token=1.50 / 1_000_000,
    ),
    # --- Google (Gemini CLI) ---
    "gemini-3.1-pro": ModelPricing(
        input_per_token=2.0 / 1_000_000,
        output_per_token=12.0 / 1_000_000,
        cache_read_per_token=0.50 / 1_000_000,
        cache_creation_per_token=2.0 / 1_000_000,
    ),
    "gemini-3.0-pro": ModelPricing(
        input_per_token=2.0 / 1_000_000,
        output_per_token=12.0 / 1_000_000,
        cache_read_per_token=0.50 / 1_000_000,
        cache_creation_per_token=2.0 / 1_000_000,
    ),
    "gemini-2.5-pro": ModelPricing(
        input_per_token=1.25 / 1_000_000,
        output_per_token=10.0 / 1_000_000,
        cache_read_per_token=0.3125 / 1_000_000,
        cache_creation_per_token=1.25 / 1_000_000,
    ),
    "gemini-2.5-flash": ModelPricing(
        input_per_token=0.30 / 1_000_000,
        output_per_token=2.50 / 1_000_000,
        cache_read_per_token=0.075 / 1_000_000,
        cache_creation_per_token=0.30 / 1_000_000,
    ),
    "gemini-2.0-flash": ModelPricing(
        input_per_token=0.10 / 1_000_000,
        output_per_token=0.40 / 1_000_000,
        cache_read_per_token=0.025 / 1_000_000,
        cache_creation_per_token=0.10 / 1_000_000,
    ),
    "gemini-1.5-pro": ModelPricing(
        input_per_token=1.25 / 1_000_000,
        output_per_token=5.0 / 1_000_000,
        cache_read_per_token=0.3125 / 1_000_000,
        cache_creation_per_token=1.25 / 1_000_000,
    ),
    "gemini-1.5-flash": ModelPricing(
        input_per_token=0.075 / 1_000_000,
        output_per_token=0.30 / 1_000_000,
        cache_read_per_token=0.01875 / 1_000_000,
        cache_creation_per_token=0.075 / 1_000_000,
    ),
}

_DEFAULT_PRICING_KEY = "claude-sonnet-4"

# Claude subscription plan tiers for cost modeling
PLAN_TIERS = [
    {"name": "api_key", "label": "API Key", "monthly_cost": 0.0},
    {"name": "pro", "label": "Claude Pro", "monthly_cost": 20.0},
    {"name": "max_5x", "label": "Claude Max (5x)", "monthly_cost": 100.0},
    {"name": "max_20x", "label": "Claude Max (20x)", "monthly_cost": 200.0},
]


def get_pricing(model_name: str) -> ModelPricing:
    """Return pricing for a model using longest prefix match, falling back to Sonnet 4."""
    best_key = ""
    for prefix in MODEL_PRICING:
        if model_name.startswith(prefix) and len(prefix) > len(best_key):
            best_key = prefix
    return MODEL_PRICING[best_key] if best_key else MODEL_PRICING[_DEFAULT_PRICING_KEY]


def estimate_cost(
    model_name: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    """Estimate USD cost for the given token counts and model."""
    pricing = get_pricing(model_name)
    return (
        input_tokens * pricing.input_per_token
        + output_tokens * pricing.output_per_token
        + cache_read_tokens * pricing.cache_read_per_token
        + cache_creation_tokens * pricing.cache_creation_per_token
    )
