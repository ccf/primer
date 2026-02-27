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


def _project_path_to_dir_name(project_path: str) -> str:
    """Convert a project path to its Claude project directory name.

    e.g. /Users/ccf/git/insights → -Users-ccf-git-insights
    """
    return project_path.replace("/", "-")


def _find_transcript(session_id: str, project_path: str | None) -> str | None:
    """Locate the .jsonl transcript for a session.

    Claude Code stores transcripts in ~/.claude/projects/<dir>/<session_id>.jsonl
    """
    projects_dir = get_claude_data_dir() / "projects"

    if project_path:
        dir_name = _project_path_to_dir_name(project_path)
        candidate = projects_dir / dir_name / f"{session_id}.jsonl"
        if candidate.exists():
            return str(candidate)

    # Fallback: search all project directories
    if projects_dir.exists():
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            candidate = project_dir / f"{session_id}.jsonl"
            if candidate.exists():
                return str(candidate)

    return None


def list_local_sessions() -> list[LocalSession]:
    """Discover all local sessions across all supported agents.

    Aggregates sessions from Claude Code, Codex CLI, and Gemini CLI
    using the extractor registry.
    """
    from primer.hook.extractor_registry import get_all_extractors

    results: list[LocalSession] = []
    for extractor in get_all_extractors():
        try:
            sessions = extractor.discover_sessions()
            results.extend(sessions)
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
