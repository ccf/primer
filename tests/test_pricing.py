from primer.common.pricing import (
    MODEL_PRICING,
    estimate_cost,
    get_pricing,
)


def test_exact_prefix_match():
    pricing = get_pricing("claude-opus-4-20250514")
    assert pricing is MODEL_PRICING["claude-opus-4"]


def test_longest_prefix_match():
    pricing = get_pricing("claude-sonnet-4-5-20250929")
    assert pricing is MODEL_PRICING["claude-sonnet-4"]


def test_haiku_match():
    pricing = get_pricing("claude-haiku-3.5-20250929")
    assert pricing is MODEL_PRICING["claude-haiku-3.5"]


def test_fallback_to_sonnet():
    pricing = get_pricing("unknown-model-xyz")
    assert pricing is MODEL_PRICING["claude-sonnet-4"]


def test_opus_4_5_match():
    pricing = get_pricing("claude-opus-4-5-20251101")
    assert pricing is MODEL_PRICING["claude-opus-4-5"]
    assert abs(pricing.input_per_token * 1_000_000 - 5.0) < 0.001


def test_opus_4_6_match():
    pricing = get_pricing("claude-opus-4-6-20260210")
    assert pricing is MODEL_PRICING["claude-opus-4-6"]
    assert abs(pricing.input_per_token * 1_000_000 - 5.0) < 0.001


def test_haiku_4_5_match():
    pricing = get_pricing("claude-haiku-4-5-20260115")
    assert pricing is MODEL_PRICING["claude-haiku-4-5"]
    assert abs(pricing.input_per_token * 1_000_000 - 1.0) < 0.001


def test_gpt5_match():
    pricing = get_pricing("gpt-5-2025")
    assert pricing is MODEL_PRICING["gpt-5"]


def test_gpt5_2_match():
    pricing = get_pricing("gpt-5.2-2025")
    assert pricing is MODEL_PRICING["gpt-5.2"]


def test_gemini_3_1_pro_match():
    pricing = get_pricing("gemini-3.1-pro-preview-0219")
    assert pricing is MODEL_PRICING["gemini-3.1-pro"]


def test_estimate_cost_opus():
    cost = estimate_cost(
        "claude-opus-4-20250514",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    assert abs(cost - 90.0) < 0.01  # $15 input + $75 output


def test_estimate_cost_opus_4_5():
    cost = estimate_cost(
        "claude-opus-4-5-20251101",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    assert abs(cost - 30.0) < 0.01  # $5 input + $25 output


def test_estimate_cost_sonnet():
    cost = estimate_cost(
        "claude-sonnet-4-5-20250929",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    assert abs(cost - 18.0) < 0.01  # $3 input + $15 output


def test_estimate_cost_with_cache():
    cost = estimate_cost(
        "claude-sonnet-4-5-20250929",
        input_tokens=0,
        output_tokens=0,
        cache_read_tokens=1_000_000,
        cache_creation_tokens=1_000_000,
    )
    assert abs(cost - 4.05) < 0.01  # $0.30 read + $3.75 creation


def test_estimate_cost_zero_tokens():
    cost = estimate_cost("claude-opus-4")
    assert cost == 0.0
