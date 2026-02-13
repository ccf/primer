"""SessionEnd hook entrypoint for Claude Code.

Reads session info from stdin, extracts metadata from the JSONL transcript,
and POSTs it to the Primer server.

Usage:
    This script is invoked by Claude Code's SessionEnd hook.
    stdin receives JSON: {"session_id": "...", "transcript_path": "...", "cwd": "..."}
"""

import json
import logging
import os
import sys

import httpx

from primer.hook.extractor import extract_from_jsonl, load_facets

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
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

    # Extract metadata from transcript
    meta = extract_from_jsonl(transcript_path) if transcript_path else None
    if meta:
        meta.session_id = session_id
        if cwd:
            meta.project_path = cwd
            meta.project_name = os.path.basename(cwd)
    else:
        # Minimal payload if no transcript
        from primer.hook.extractor import SessionMetadata

        meta = SessionMetadata(session_id=session_id, project_path=cwd)

    # Check for facets
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
            logger.info(f"Session {session_id} ingested successfully")
        else:
            logger.error(f"Ingest failed ({resp.status_code}): {resp.text}")
    except httpx.RequestError as e:
        logger.error(f"Failed to reach Primer server: {e}")


if __name__ == "__main__":
    main()
