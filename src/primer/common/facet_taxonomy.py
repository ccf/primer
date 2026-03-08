"""Shared normalization helpers for session facet taxonomy."""

CANONICAL_OUTCOME_ALIASES = {
    "success": "success",
    "fully_achieved": "success",
    "partial": "partial",
    "mostly_achieved": "partial",
    "partially_achieved": "partial",
    "failure": "failure",
    "not_achieved": "failure",
}
CANONICAL_OUTCOME_VALUES = frozenset(CANONICAL_OUTCOME_ALIASES.values())


def canonical_outcome(value: str | None) -> str | None:
    """Map legacy outcome labels onto the canonical outcome taxonomy."""
    if value is None:
        return None
    return CANONICAL_OUTCOME_ALIASES.get(value, value)


def is_success_outcome(value: str | None) -> bool:
    """Return True when the outcome represents a successful session."""
    return canonical_outcome(value) == "success"


def normalize_goal_categories(value: object) -> list[str] | None:
    """Normalize stored or incoming goal categories to a simple string list."""
    if value is None:
        return None
    if isinstance(value, dict):
        return [key for key in value if isinstance(key, str)]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return None


def validate_inbound_outcome(value: object) -> str | None:
    """Normalize supported inbound outcomes and reject malformed values."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("outcome must be a string")
    if value not in CANONICAL_OUTCOME_ALIASES:
        raise ValueError("outcome must be one of the supported facet taxonomy values")
    return canonical_outcome(value)


def validate_inbound_goal_categories(value: object) -> list[str] | None:
    """Accept only dict or list goal categories on the inbound write path."""
    if value is None:
        return None
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("goal_categories dict keys must be strings")
        return list(value.keys())
    if isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            raise ValueError("goal_categories list items must all be strings")
        return value
    raise ValueError("goal_categories must be a dict or a list of strings")
