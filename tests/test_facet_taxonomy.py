"""Tests for shared facet taxonomy helpers."""

from primer.common.facet_taxonomy import (
    canonical_outcome,
    is_success_outcome,
    normalize_goal_categories,
)


def test_canonical_outcome_maps_legacy_values():
    assert canonical_outcome("fully_achieved") == "success"
    assert canonical_outcome("mostly_achieved") == "partial"
    assert canonical_outcome("partially_achieved") == "partial"
    assert canonical_outcome("not_achieved") == "failure"


def test_canonical_outcome_preserves_current_values():
    assert canonical_outcome("success") == "success"
    assert canonical_outcome("partial") == "partial"
    assert canonical_outcome("failure") == "failure"


def test_normalize_goal_categories_accepts_dict_and_list():
    assert normalize_goal_categories({"fix_bug": 2, "refactor": 1}) == ["fix_bug", "refactor"]
    assert normalize_goal_categories(["fix_bug", "refactor"]) == ["fix_bug", "refactor"]


def test_is_success_outcome_uses_canonical_mapping():
    assert is_success_outcome("fully_achieved") is True
    assert is_success_outcome("success") is True
    assert is_success_outcome("not_achieved") is False
