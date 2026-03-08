"""Read local session data from all supported AI coding agents."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class LocalSession:
    session_id: str
    transcript_path: str
    facets_path: str | None
    has_facets: bool
    project_path: str | None = None
    agent_type: str = "claude_code"


def get_claude_data_dir() -> Path:
    return Path.home() / ".claude"


def get_usage_data_dir() -> Path:
    return get_claude_data_dir() / "usage-data"


def list_local_sessions() -> list[LocalSession]:
    """Discover all local sessions across all supported agents.

    Aggregates sessions from Claude Code, Codex CLI, Gemini CLI, and Cursor
    using the extractor registry.
    """
    from primer.hook.extractor_registry import get_all_extractors

    results: list[LocalSession] = []
    seen_keys: set[tuple[str, str]] = set()
    for extractor in get_all_extractors():
        try:
            _extend_unique_sessions(results, seen_keys, extractor.discover_sessions())
        except Exception:
            logger.exception(f"Error discovering {extractor.agent_type} sessions")
    return results


def get_local_session_ids() -> set[str]:
    """Get set of all local session IDs."""
    return {s.session_id for s in list_local_sessions()}


def read_local_stats() -> dict:
    """Read local usage stats summary if available."""
    stats_path = get_usage_data_dir() / "stats.json"
    if not stats_path.exists():
        return {}
    try:
        with open(stats_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _extend_unique_sessions(
    results: list[LocalSession],
    seen_keys: set[tuple[str, str]],
    sessions: list[LocalSession],
) -> None:
    # Preserve the first discovered session for a given agent/session key.
    for session in sessions:
        key = (session.agent_type, session.session_id)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        results.append(session)
