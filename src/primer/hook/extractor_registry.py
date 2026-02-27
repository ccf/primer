"""Registry of all available session extractors.

Provides discovery and lookup of extractors for each supported agent type.
"""

from __future__ import annotations

import logging

from primer.hook.codex_extractor import CodexExtractor
from primer.hook.extractor import ClaudeCodeExtractor, SessionExtractor
from primer.hook.gemini_extractor import GeminiExtractor

logger = logging.getLogger(__name__)

EXTRACTORS: dict[str, type] = {
    "claude_code": ClaudeCodeExtractor,
    "codex_cli": CodexExtractor,
    "gemini_cli": GeminiExtractor,
}


def get_all_extractors() -> list[SessionExtractor]:
    """Return an instance of every registered extractor."""
    return [cls() for cls in EXTRACTORS.values()]


def get_extractor_for(agent_type: str) -> SessionExtractor | None:
    """Return an extractor instance for the given agent type, or None."""
    cls = EXTRACTORS.get(agent_type)
    if cls is None:
        logger.warning(f"No extractor registered for agent_type={agent_type}")
        return None
    return cls()
