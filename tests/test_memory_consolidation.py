"""Tests for the memory consolidation engine (Plan 2b)."""

from primer.common.config import settings


def test_consolidation_settings_present():
    assert settings.memory_consolidation_enabled is True
    assert settings.memory_consolidation_interval_hours == 24
    assert settings.memory_min_corroboration == 2
    assert settings.memory_dedup_similarity == 0.85
    assert settings.memory_judge_max_calls_per_pass == 200
    assert settings.memory_judge_model  # non-empty
    assert settings.memory_embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.memory_embedding_dim == 384
