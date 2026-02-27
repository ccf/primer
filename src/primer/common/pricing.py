from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_per_token: float
    output_per_token: float
    cache_read_per_token: float
    cache_creation_per_token: float


# Prices per token (derived from published per-MTok pricing)
MODEL_PRICING: dict[str, ModelPricing] = {
    # --- Anthropic (Claude Code) ---
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
    "claude-haiku-3.5": ModelPricing(
        input_per_token=0.80 / 1_000_000,
        output_per_token=4.0 / 1_000_000,
        cache_read_per_token=0.08 / 1_000_000,
        cache_creation_per_token=1.0 / 1_000_000,
    ),
    # --- OpenAI (Codex CLI) ---
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
    "codex-mini": ModelPricing(
        input_per_token=1.50 / 1_000_000,
        output_per_token=6.0 / 1_000_000,
        cache_read_per_token=0.375 / 1_000_000,
        cache_creation_per_token=1.50 / 1_000_000,
    ),
    # --- Google (Gemini CLI) ---
    "gemini-2.5-pro": ModelPricing(
        input_per_token=1.25 / 1_000_000,
        output_per_token=10.0 / 1_000_000,
        cache_read_per_token=0.3125 / 1_000_000,
        cache_creation_per_token=1.25 / 1_000_000,
    ),
    "gemini-2.5-flash": ModelPricing(
        input_per_token=0.15 / 1_000_000,
        output_per_token=0.60 / 1_000_000,
        cache_read_per_token=0.0375 / 1_000_000,
        cache_creation_per_token=0.15 / 1_000_000,
    ),
    "gemini-2.0-flash": ModelPricing(
        input_per_token=0.10 / 1_000_000,
        output_per_token=0.40 / 1_000_000,
        cache_read_per_token=0.025 / 1_000_000,
        cache_creation_per_token=0.10 / 1_000_000,
    ),
}

_DEFAULT_PRICING_KEY = "claude-sonnet-4"


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
