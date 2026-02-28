"""primer sync — sync local session history to the server."""

import os

import click


@click.command("sync")
def sync() -> None:
    """Sync local Claude Code sessions to the Primer server."""
    from primer.cli import console
    from primer.cli.config import get_value
    from primer.mcp.sync import sync_sessions

    api_key = os.environ.get("PRIMER_API_KEY") or get_value("auth.api_key") or ""
    server_url = (
        os.environ.get("PRIMER_SERVER_URL") or get_value("server.url") or "http://localhost:8000"
    )

    if not api_key:
        console.error("No API key configured. Run: primer setup")
        return

    console.info("Syncing sessions...")
    result = sync_sessions(server_url, api_key)

    console.kvp("Local sessions", str(result.get("local_count", 0)))
    console.kvp("Already synced", str(result.get("already_synced", 0)))
    console.kvp("Newly synced", str(result.get("synced", 0)))

    errors = result.get("errors", 0)
    if errors:
        console.warn(f"{errors} session(s) failed to sync.")
    else:
        console.success("Sync complete.")
