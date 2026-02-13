"""Read Claude Code local data structures from ~/.claude."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LocalSession:
    session_id: str
    transcript_path: str
    facets_path: str | None
    has_facets: bool


def get_claude_data_dir() -> Path:
    return Path.home() / ".claude"


def get_usage_data_dir() -> Path:
    return get_claude_data_dir() / "usage-data"


def list_local_sessions() -> list[LocalSession]:
    """Discover all local session transcripts and their facets."""
    usage_dir = get_usage_data_dir()
    sessions_dir = usage_dir / "sessions"
    facets_dir = usage_dir / "facets"

    if not sessions_dir.exists():
        return []

    results = []
    for transcript in sessions_dir.glob("*.jsonl"):
        session_id = transcript.stem
        facets_path = facets_dir / f"{session_id}.json"
        has_facets = facets_path.exists()
        results.append(
            LocalSession(
                session_id=session_id,
                transcript_path=str(transcript),
                facets_path=str(facets_path) if has_facets else None,
                has_facets=has_facets,
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
