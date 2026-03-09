"""primer sync — sync local session history to the server."""

import os
import time

import click


@click.command("sync")
@click.option("--watch", is_flag=True, help="Continuously sync on an interval.")
@click.option("--interval", default=60, type=int, help="Seconds between sync checks (--watch).")
def sync(watch: bool, interval: int) -> None:
    """Sync local AI coding sessions to the Primer server."""
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

    if watch:
        console.info(f"Watching for new sessions every {interval}s (Ctrl+C to stop)...")
        try:
            while True:
                _run_sync(console, server_url, api_key, sync_sessions, exit_on_fatal=False)
                time.sleep(interval)
        except KeyboardInterrupt:
            console.info("Watch stopped.")
    else:
        _run_sync(console, server_url, api_key, sync_sessions, exit_on_fatal=True)


def _run_sync(console, server_url: str, api_key: str, sync_fn, *, exit_on_fatal: bool) -> None:
    """Execute a single sync cycle and print results."""
    console.info("Syncing sessions...")
    result = sync_fn(server_url, api_key)

    if result.get("fatal_error"):
        message = result.get("error_message") or "Sync failed before upload."
        if exit_on_fatal:
            raise click.ClickException(message)
        console.error(message)
        return

    console.kvp("Local sessions", str(result.get("local_count", 0)))
    console.kvp("Already synced", str(result.get("already_synced", 0)))
    console.kvp("Newly synced", str(result.get("synced", 0)))

    errors = result.get("errors", 0)
    if errors:
        console.warn(f"{errors} session(s) failed to sync.")
    else:
        console.success("Sync complete.")
