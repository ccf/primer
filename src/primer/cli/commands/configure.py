"""primer configure {get, set, list} — manage config.toml values."""

import click

SENSITIVE_KEYS = {"auth.admin_api_key", "auth.api_key"}


@click.group("configure")
def configure() -> None:
    """Read and write Primer configuration."""


@configure.command("get")
@click.argument("key")
def config_get(key: str) -> None:
    """Get a config value (e.g. primer configure get server.port)."""
    from primer.cli import console
    from primer.cli.config import get_value

    value = get_value(key)
    if value is None:
        console.warn(f"{key} is not set")
    elif key in SENSITIVE_KEYS:
        console.kvp(key, value[:12] + "..." if len(value) > 12 else value)
    else:
        console.kvp(key, value)


@configure.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a config value (e.g. primer configure set server.port 9000)."""
    from primer.cli import console
    from primer.cli.config import set_value

    set_value(key, value)
    console.success(f"{key} = {value}")


@configure.command("list")
def config_list() -> None:
    """Show all configuration values."""
    from primer.cli import console
    from primer.cli.config import read_config

    cfg = read_config()
    if not cfg:
        console.warn("No config file found. Run: primer init")
        return

    for section, values in cfg.items():
        if isinstance(values, dict):
            console.header(f"[{section}]")
            for k, v in values.items():
                dotted = f"{section}.{k}"
                display = str(v)
                if dotted in SENSITIVE_KEYS and len(display) > 12:
                    display = display[:12] + "..."
                console.kvp(f"  {k}", display)
        else:
            console.kvp(section, str(values))
