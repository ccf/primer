"""Sync local session data from all supported agents to the Primer server."""

import logging
import os
from pathlib import Path

import httpx

from primer.common.source_capabilities import get_capability_for
from primer.hook.extractor import capture_git_info, load_facets
from primer.hook.extractor_registry import get_extractor_for
from primer.mcp.reader import list_local_sessions

logger = logging.getLogger(__name__)

_MAX_PAGES = 200


def get_server_session_ids(server_url: str, api_key: str) -> set[str]:
    """Fetch the set of session IDs already on the server for this engineer."""
    session_ids: set[str] = set()
    limit = 1000
    offset = 0

    for _page in range(_MAX_PAGES):
        try:
            resp = httpx.get(
                f"{server_url}/api/v1/sessions",
                headers={"x-api-key": api_key},
                params={"limit": limit, "offset": offset},
                timeout=30.0,
            )
        except httpx.RequestError as exc:
            logger.warning("Failed to fetch server sessions: %s", exc)
            return session_ids

        if resp.status_code != 200:
            logger.warning(f"Failed to fetch server sessions: {resp.status_code}")
            return session_ids

        payload = resp.json()
        items = payload.get("items", [])
        session_ids.update(item["id"] for item in items if "id" in item)

        total_count = payload.get("total_count")
        if len(items) < limit:
            return session_ids
        if isinstance(total_count, int) and offset + len(items) >= total_count:
            return session_ids

        offset += limit

    logger.warning(
        "Pagination safety limit (%d pages) reached; returning partial results",
        _MAX_PAGES,
    )
    return session_ids


def sync_sessions(server_url: str, api_key: str) -> dict:
    """Compare local sessions vs server, upload missing ones.

    Returns a summary dict with counts.
    """
    local_sessions = list_local_sessions()
    if not local_sessions:
        return {"local_count": 0, "server_count": 0, "synced": 0, "errors": 0}

    server_ids = get_server_session_ids(server_url, api_key)
    missing: list[object] = []
    already_synced = 0
    for local_session in local_sessions:
        matched_server_id = _match_existing_server_session_id(local_session, server_ids)
        if matched_server_id is not None:
            already_synced += 1
            continue
        missing.append(local_session)

    synced = 0
    errors = 0

    for local_session in missing:
        try:
            extractor = get_extractor_for(local_session.agent_type)
            if not extractor:
                errors += 1
                continue
            meta = extractor.extract(local_session.transcript_path)
            meta.session_id = meta.session_id or local_session.session_id
            meta.agent_type = local_session.agent_type

            capability = get_capability_for(local_session.agent_type)

            # Only attach native facet files when the source actually has them.
            # Other agents rely on ingest-time transcript extraction instead.
            facets = (
                load_facets(local_session.session_id, local_session.facets_path)
                if capability and capability.supports_facets and local_session.has_facets
                else None
            )

            # Capture git info from the project directory
            cwd = local_session.project_path
            if cwd and os.path.isdir(cwd):
                if not meta.project_path:
                    meta.project_path = cwd
                    meta.project_name = os.path.basename(cwd)
                git_info = capture_git_info(cwd, meta.started_at)
                if git_info.get("branch") and not meta.git_branch:
                    meta.git_branch = git_info["branch"]
                if git_info.get("remote_url") and not meta.git_remote_url:
                    meta.git_remote_url = git_info["remote_url"]
                if git_info.get("commits") and not meta.commits:
                    meta.commits = git_info["commits"]

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
        "already_synced": already_synced,
    }


def _match_existing_server_session_id(local_session, server_ids: set[str]) -> str | None:
    """Return an already-synced server ID for this local session, if any.

    Codex previously fell back to rollout filename stems when session_meta parsing
    failed. Treat that legacy ID as already-synced so upgraded clients don't
    perpetually re-upload the same session under the alias.
    """
    if local_session.session_id in server_ids:
        return local_session.session_id

    if local_session.agent_type == "codex_cli":
        legacy_rollout_id = Path(local_session.transcript_path).stem
        if legacy_rollout_id in server_ids:
            return legacy_rollout_id

    return None
