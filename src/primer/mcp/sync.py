"""Sync local Claude Code session data to the Primer server."""

import logging

import httpx

from primer.hook.extractor import extract_from_jsonl, load_facets
from primer.mcp.reader import list_local_sessions

logger = logging.getLogger(__name__)


def get_server_session_ids(server_url: str, api_key: str) -> set[str]:
    """Fetch the set of session IDs already on the server for this engineer."""
    resp = httpx.get(
        f"{server_url}/api/v1/sessions",
        headers={"x-api-key": api_key, "x-admin-key": api_key},
        params={"limit": 10000},
        timeout=30.0,
    )
    if resp.status_code != 200:
        logger.warning(f"Failed to fetch server sessions: {resp.status_code}")
        return set()
    return {s["id"] for s in resp.json()}


def sync_sessions(server_url: str, api_key: str) -> dict:
    """Compare local sessions vs server, upload missing ones.

    Returns a summary dict with counts.
    """
    local_sessions = list_local_sessions()
    if not local_sessions:
        return {"local_count": 0, "server_count": 0, "synced": 0, "errors": 0}

    server_ids = get_server_session_ids(server_url, api_key)
    missing = [s for s in local_sessions if s.session_id not in server_ids]

    synced = 0
    errors = 0

    for local_session in missing:
        try:
            meta = extract_from_jsonl(local_session.transcript_path)
            meta.session_id = local_session.session_id
            facets = load_facets(local_session.session_id)
            payload = meta.to_ingest_payload(api_key=api_key, facets=facets)

            resp = httpx.post(
                f"{server_url}/api/v1/ingest/session",
                json=payload,
                timeout=10.0,
            )
            if resp.status_code == 200:
                synced += 1
            else:
                errors += 1
                logger.warning(f"Failed to sync {local_session.session_id}: {resp.status_code}")
        except Exception as e:
            errors += 1
            logger.error(f"Error syncing {local_session.session_id}: {e}")

    return {
        "local_count": len(local_sessions),
        "server_count": len(server_ids),
        "synced": synced,
        "errors": errors,
        "already_synced": len(local_sessions) - len(missing),
    }
