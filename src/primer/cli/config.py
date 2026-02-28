"""Config.toml ↔ environment variable bridge.

Precedence: CLI flags → env vars → config.toml → PrimerSettings defaults.
"""

import os
import tomllib
from pathlib import Path

from primer.cli.paths import CONFIG_FILE

# Keys that map from config.toml sections/keys to PRIMER_* env vars.
# Format: (toml_section, toml_key, env_var_name)
_CONFIG_MAP: list[tuple[str, str, str]] = [
    ("server", "host", "PRIMER_SERVER_HOST"),
    ("server", "port", "PRIMER_SERVER_PORT"),
    ("server", "url", "PRIMER_SERVER_URL"),
    ("database", "url", "PRIMER_DATABASE_URL"),
    ("auth", "admin_api_key", "PRIMER_ADMIN_API_KEY"),
    ("auth", "api_key", "PRIMER_API_KEY"),
    ("log", "level", "PRIMER_LOG_LEVEL"),
]

DEFAULT_CONFIG = """\
# Primer configuration
# Values here are loaded as PRIMER_* environment variables.
# Environment variables and CLI flags take precedence.

[server]
host = "127.0.0.1"
port = 8000
url = "http://localhost:8000"

[database]
# url = "sqlite:///~/.primer/primer.db"

[auth]
# admin_api_key = "generated-on-init"
# api_key = "set-after-primer-setup"

[log]
level = "info"
"""


def read_config(path: Path | None = None) -> dict:
    """Parse config.toml and return as nested dict."""
    path = path or CONFIG_FILE
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_config_into_env(path: Path | None = None) -> None:
    """Set PRIMER_* env vars from config.toml (only if not already set)."""
    cfg = read_config(path)
    if not cfg:
        return
    for section, key, env_var in _CONFIG_MAP:
        if env_var not in os.environ:
            value = cfg.get(section, {}).get(key)
            if value is not None:
                os.environ[env_var] = str(value)


def get_value(dotted_key: str, path: Path | None = None) -> str | None:
    """Get a value from config.toml using dotted notation (e.g. 'server.port')."""
    cfg = read_config(path)
    parts = dotted_key.split(".")
    node = cfg
    for part in parts:
        if isinstance(node, dict):
            node = node.get(part)
        else:
            return None
    return str(node) if node is not None else None


def set_value(dotted_key: str, value: str, path: Path | None = None) -> None:
    """Set a value in config.toml using dotted notation."""
    path = path or CONFIG_FILE
    cfg = read_config(path)
    parts = dotted_key.split(".")
    node = cfg
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value
    _write_toml(cfg, path)


def write_config(content: str, path: Path | None = None) -> None:
    """Write raw string content to config.toml."""
    path = path or CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _write_toml(data: dict, path: Path) -> None:
    """Write a dict as TOML to a file (simple serializer for flat/one-level nesting)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    # Write top-level non-dict values first
    for k, v in data.items():
        if not isinstance(v, dict):
            lines.append(f"{k} = {_toml_value(v)}")
    if lines:
        lines.append("")
    # Write sections
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"[{k}]")
            for sk, sv in v.items():
                lines.append(f"{sk} = {_toml_value(sv)}")
            lines.append("")
    path.write_text("\n".join(lines))


def _toml_value(v: object) -> str:
    """Format a Python value as a TOML literal."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return str(v)
    s = str(v).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'
