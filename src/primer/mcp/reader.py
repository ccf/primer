"""Read Claude Code local data structures from ~/.claude."""

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
    """Discover all local session transcripts and their facets.

    Reads session-meta/*.json to find session IDs and project paths,
    then resolves transcript paths from ~/.claude/projects/<dir>/.
    """
    usage_dir = get_usage_data_dir()
    meta_dir = usage_dir / "session-meta"
    facets_dir = usage_dir / "facets"

    if not meta_dir.exists():
        return []

    results = []
    for meta_file in meta_dir.glob("*.json"):
        session_id = meta_file.stem
        try:
            with open(meta_file) as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        project_path = meta.get("project_path")
        transcript_path = _find_transcript(session_id, project_path)
        if not transcript_path:
            continue

        facets_path = facets_dir / f"{session_id}.json"
        has_facets = facets_path.exists()
        results.append(
            LocalSession(
                session_id=session_id,
                transcript_path=transcript_path,
                facets_path=str(facets_path) if has_facets else None,
                has_facets=has_facets,
                project_path=project_path,
            )
        )
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
