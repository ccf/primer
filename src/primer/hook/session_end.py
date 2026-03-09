"""SessionEnd hook entrypoint for AI coding agents.

Reads session info from stdin, extracts metadata from the transcript,
and POSTs it to the Primer server.

Usage:
    This script is invoked by an agent's SessionEnd hook.
    stdin receives JSON: {"session_id": "...", "transcript_path": "...", "cwd": "..."}

    --agent flag selects the extractor (default: claude for backward compatibility).
"""

import argparse
import json
import logging
import os
import sys

import httpx

from primer.hook.extractor import SessionMetadata, capture_git_info, load_facets
from primer.hook.extractor_registry import get_extractor_for

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Maps CLI agent names to extractor registry keys
AGENT_MAP: dict[str, str] = {
    "claude": "claude_code",
    "gemini": "gemini_cli",
}

# Environment variables used to detect billing mode per agent
BILLING_ENV_KEYS: dict[str, list[str]] = {
    "claude": ["ANTHROPIC_API_KEY"],
    "gemini": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
}


def _detect_billing_mode(agent: str) -> str:
    """Detect whether the user is on an API key or subscription billing mode."""
    env_keys = BILLING_ENV_KEYS.get(agent, [])
    for key in env_keys:
        if os.environ.get(key):
            return "api_key"
    return "subscription"


def main() -> None:
    parser = argparse.ArgumentParser(description="Primer SessionEnd hook")
    parser.add_argument(
        "--agent",
        default="claude",
        choices=list(AGENT_MAP.keys()),
        help="Agent type (default: claude)",
    )
    args = parser.parse_args()

    agent = args.agent
    agent_type = AGENT_MAP[agent]

    server_url = os.environ.get("PRIMER_SERVER_URL", "http://localhost:8000")
    api_key = os.environ.get("PRIMER_API_KEY", "")

    if not api_key:
        logger.error("PRIMER_API_KEY not set")
        sys.exit(1)

    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Failed to parse stdin: {e}")
        sys.exit(1)

    session_id = hook_input.get("session_id", "")
    transcript_path = hook_input.get("transcript_path", "")
    cwd = hook_input.get("cwd", "")

    if not session_id:
        logger.error("No session_id in hook input")
        sys.exit(1)

    # Extract metadata from transcript using the appropriate extractor
    extractor = get_extractor_for(agent_type)
    if extractor and transcript_path:
        meta = extractor.extract(transcript_path)
    elif transcript_path:
        # Fallback to Claude Code JSONL parser for backward compatibility
        from primer.hook.extractor import extract_from_jsonl

        meta = extract_from_jsonl(transcript_path)
    else:
        meta = None

    if meta:
        meta.session_id = session_id
        meta.agent_type = agent_type
        if cwd:
            meta.project_path = cwd
            meta.project_name = os.path.basename(cwd)
    else:
        # Minimal payload if no transcript
        meta = SessionMetadata(session_id=session_id, project_path=cwd, agent_type=agent_type)

    # Detect billing mode from environment
    meta.billing_mode = _detect_billing_mode(agent)

    # Capture git info (branch, remote, commits during session)
    if cwd:
        git_info = capture_git_info(cwd, meta.started_at)
        if git_info.get("branch"):
            meta.git_branch = git_info["branch"]
        if git_info.get("remote_url"):
            meta.git_remote_url = git_info["remote_url"]
        if git_info.get("commits"):
            meta.commits = git_info["commits"]

    # Claude exposes native facet files; other agents rely on ingest-time
    # transcript extraction when that feature is enabled on the server.
    facets = None
    if agent == "claude":
        facets = load_facets(session_id)

    # Build and send payload
    payload = meta.to_ingest_payload(api_key=api_key, facets=facets)

    try:
        resp = httpx.post(
            f"{server_url}/api/v1/ingest/session",
            json=payload,
            timeout=10.0,
        )
        if resp.status_code == 200:
            logger.info(f"Session {session_id} ingested successfully ({agent_type})")
        else:
            logger.error(f"Ingest failed ({resp.status_code}): {resp.text}")
    except httpx.RequestError as e:
        logger.error(f"Failed to reach Primer server: {e}")


if __name__ == "__main__":
    main()
