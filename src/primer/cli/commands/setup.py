"""primer setup — register the current user as an engineer."""

import subprocess

import click


@click.command()
@click.option("--name", help="Your display name (default: git config user.name)")
@click.option("--email", help="Your email (default: git config user.email)")
@click.option("--server-url", default=None, help="Primer server URL")
def setup(name: str | None, email: str | None, server_url: str | None) -> None:
    """Register yourself as an engineer and save your API key."""
    import os

    import httpx

    from primer.cli import console
    from primer.cli.config import get_value, set_value

    console.header("Engineer Setup")

    # Resolve name/email from git config if not provided
    if not name:
        result = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
        name = result.stdout.strip() or None
    if not email:
        result = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True)
        email = result.stdout.strip() or None

    if not name:
        name = click.prompt("  Name")
    if not email:
        email = click.prompt("  Email")

    console.info(f"Registering {name} <{email}>")

    url = (
        server_url
        or os.environ.get("PRIMER_SERVER_URL")
        or get_value("server.url")
        or "http://localhost:8000"
    )
    admin_key = os.environ.get("PRIMER_ADMIN_API_KEY") or get_value("auth.admin_api_key") or ""

    try:
        resp = httpx.post(
            f"{url}/api/v1/engineers",
            json={"name": name, "email": email},
            headers={"x-admin-key": admin_key},
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            api_key = data.get("api_key", "")
            eng_id = data.get("engineer", {}).get("id") or data.get("id", "unknown")
            console.success(f"Registered! Engineer ID: {eng_id}")
            if api_key:
                set_value("auth.api_key", api_key)
                console.success("API key saved to config.toml")
                console.info("You can now run: primer hook install")
        else:
            console.error(f"Registration failed ({resp.status_code}): {resp.text}")
    except httpx.RequestError as e:
        console.error(f"Could not reach server: {e}")
        console.info("Is the server running? Try: primer server start")
