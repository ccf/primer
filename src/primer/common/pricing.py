from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_per_token: float
    output_per_token: float
    cache_read_per_token: float
    cache_creation_per_token: float


# Prices per token (derived from Anthropic published per-MTok pricing)
MODEL_PRICING: dict[str, ModelPricing] = {
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
