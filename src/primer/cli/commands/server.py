"""primer server {start, stop, status, logs} — manage the Primer server."""

import contextlib
import os
import subprocess
import sys

import click


@click.group()
def server() -> None:
    """Manage the Primer API server."""


@server.command()
@click.option("--host", default=None, help="Bind host (default: from config)")
@click.option("--port", default=None, type=int, help="Bind port (default: from config)")
@click.option("--fg", "foreground", is_flag=True, help="Run in foreground (blocking)")
def start(host: str | None, port: int | None, foreground: bool) -> None:
    """Start the Primer server."""
    from primer.cli import console
    from primer.cli.config import get_value
    from primer.cli.server_manager import start_server

    host = host or os.environ.get("PRIMER_SERVER_HOST") or get_value("server.host") or "127.0.0.1"
    port_str = os.environ.get("PRIMER_SERVER_PORT") or get_value("server.port")
    port = port or (int(port_str) if port_str else 8000)

    console.info(f"Starting server on {host}:{port}" + (" (foreground)" if foreground else ""))
    ok, msg = start_server(host=host, port=port, foreground=foreground)
    if ok:
        console.success(msg)
    else:
        console.error(msg)
        sys.exit(1)


@server.command()
def stop() -> None:
    """Stop the Primer server."""
    from primer.cli import console
    from primer.cli.server_manager import stop_server

    ok, msg = stop_server()
    if ok:
        console.success(msg)
    else:
        console.warn(msg)


@server.command()
def status() -> None:
    """Show server status."""
    from primer.cli import console
    from primer.cli.server_manager import server_status

    info = server_status()
    if info["running"]:
        console.success(f"Server is running (PID {info['pid']}, via {info['strategy']})")
    else:
        console.warn(f"Server is not running (strategy: {info['strategy']})")


@server.command()
@click.option("-f", "--follow", is_flag=True, help="Follow log output")
@click.option("-n", "--lines", default=50, help="Number of lines to show")
def logs(follow: bool, lines: int) -> None:
    """Tail the server log file."""
    from primer.cli import console
    from primer.cli.paths import SERVER_LOG

    if not SERVER_LOG.exists():
        console.warn(f"Log file not found: {SERVER_LOG}")
        return

    cmd = ["tail", f"-n{lines}"]
    if follow:
        cmd.append("-f")
    cmd.append(str(SERVER_LOG))

    with contextlib.suppress(KeyboardInterrupt):
        subprocess.run(cmd)
