"""primer mcp {install, uninstall, serve} — manage MCP server registration."""

import json
import sys
from pathlib import Path

import click

CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
MCP_SERVER_NAME = "primer"


@click.group("mcp")
def mcp() -> None:
    """Manage the Primer MCP server for Claude Code."""


@mcp.command()
def install() -> None:
    """Register Primer as an MCP server in Claude Code settings."""
    from primer.cli import console

    settings = _load_settings()
    servers = settings.setdefault("mcpServers", {})

    if MCP_SERVER_NAME in servers:
        console.warn("Primer MCP server already registered.")
        return

    servers[MCP_SERVER_NAME] = {
        "command": sys.executable,
        "args": ["-m", "primer.mcp.server"],
    }
    _save_settings(settings)
    console.success(f"Primer MCP server registered in {CLAUDE_SETTINGS}")


@mcp.command()
def uninstall() -> None:
    """Remove Primer MCP server from Claude Code settings."""
    from primer.cli import console

    settings = _load_settings()
    servers = settings.get("mcpServers", {})

    if MCP_SERVER_NAME not in servers:
        console.warn("Primer MCP server not registered (nothing to remove).")
        return

    del servers[MCP_SERVER_NAME]
    _save_settings(settings)
    console.success("Primer MCP server removed.")


@mcp.command()
def serve() -> None:
    """Run the MCP server directly (called by Claude Code)."""
    from primer.mcp.server import mcp as mcp_server

    mcp_server.run()


def _load_settings() -> dict:
    if CLAUDE_SETTINGS.exists():
        with open(CLAUDE_SETTINGS) as f:
            return json.load(f)
    return {}


def _save_settings(settings: dict) -> None:
    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    with open(CLAUDE_SETTINGS, "w") as f:
        json.dump(settings, f, indent=2)
