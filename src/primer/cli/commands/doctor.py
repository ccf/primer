"""primer doctor — run diagnostic checks."""

import os

import click


@click.command()
def doctor() -> None:
    """Check that Primer is correctly set up."""
    from primer.cli import console
    from primer.cli.config import get_value, read_config
    from primer.cli.paths import CONFIG_FILE, DATABASE_FILE, PRIMER_HOME

    console.header("Primer Doctor")
    all_ok = True

    # 1. Data directory
    if PRIMER_HOME.exists():
        console.success(f"Data directory: {PRIMER_HOME}")
    else:
        console.error(f"Data directory missing: {PRIMER_HOME}")
        console.info("Run: primer init")
        all_ok = False

    # 2. Config file
    if CONFIG_FILE.exists():
        console.success(f"Config file: {CONFIG_FILE}")
    else:
        console.error(f"Config file missing: {CONFIG_FILE}")
        all_ok = False

    # 3. Database
    cfg = read_config()
    db_url = cfg.get("database", {}).get("url", "")
    if db_url and "sqlite" in db_url:
        db_path = db_url.replace("sqlite:///", "")
        from pathlib import Path

        if Path(db_path).exists():
            console.success(f"Database: {db_path}")
        else:
            console.error(f"Database file missing: {db_path}")
            all_ok = False
    elif DATABASE_FILE.exists():
        console.success(f"Database: {DATABASE_FILE}")
    else:
        console.warn("Database not found (may be using non-SQLite backend)")

    # 4. Admin API key
    admin_key = os.environ.get("PRIMER_ADMIN_API_KEY") or get_value("auth.admin_api_key") or ""
    if admin_key:
        masked = admin_key[:12] + "..." if len(admin_key) > 12 else "***"
        console.success(f"Admin API key: {masked}")
    else:
        console.error("Admin API key not configured")
        all_ok = False

    # 5. Engineer API key
    api_key = os.environ.get("PRIMER_API_KEY") or get_value("auth.api_key") or ""
    if api_key:
        masked = api_key[:12] + "..." if len(api_key) > 12 else "***"
        console.success(f"API key: {masked}")
    else:
        console.warn("API key not set (run: primer setup)")

    # 6. Server running
    from primer.cli.server_manager import server_status

    status = server_status()
    if status["running"]:
        console.success(f"Server running (PID {status['pid']}, {status['strategy']})")
    else:
        console.warn("Server not running (run: primer server start)")

    # 7. Server reachable
    server_url = (
        os.environ.get("PRIMER_SERVER_URL") or get_value("server.url") or "http://localhost:8000"
    )
    try:
        import httpx

        resp = httpx.get(f"{server_url}/health", timeout=3.0)
        if resp.status_code == 200:
            console.success(f"Server reachable: {server_url}")
        else:
            console.warn(f"Server responded with {resp.status_code}")
    except Exception:
        console.warn(f"Cannot reach server at {server_url}")

    # 8. Hook installed
    from primer.hook.installer import status as hook_status

    installed, _msg = hook_status()
    if installed:
        console.success("Claude Code hook installed")
    else:
        console.warn("Claude Code hook not installed (run: primer hook install)")

    # 9. MCP registered
    from pathlib import Path

    claude_settings = Path.home() / ".claude" / "settings.json"
    if claude_settings.exists():
        import json

        with open(claude_settings) as f:
            cs = json.load(f)
        if "primer" in cs.get("mcpServers", {}):
            console.success("MCP server registered")
        else:
            console.warn("MCP server not registered (run: primer mcp install)")
    else:
        console.warn("Claude Code settings not found")

    # Summary
    if all_ok:
        console.header("All checks passed!")
    else:
        console.header("Some checks failed. See above for details.")
