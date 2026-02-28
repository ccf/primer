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


def _coerce_value(value: str) -> object:
    """Attempt to parse a string value as its natural TOML type."""
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def set_value(dotted_key: str, value: str, path: Path | None = None) -> None:
    """Set a value in config.toml using dotted notation.

    Performs line-level replacement to preserve comments and formatting.
    Falls back to full rewrite if the key isn't found in the existing file.
    """
    path = path or CONFIG_FILE
    coerced = _coerce_value(value)
    parts = dotted_key.split(".")

    # Try line-level replacement first to preserve comments
    if path.exists():
        text = path.read_text()
        if len(parts) == 2:
            section, key = parts
            new_text = _replace_in_section(text, section, key, coerced)
            if new_text is not None:
                path.write_text(new_text)
                return

    # Fallback: full rewrite (loses comments)
    cfg = read_config(path)
    node = cfg
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = coerced
    _write_toml(cfg, path)


def _replace_in_section(text: str, section: str, key: str, value: object) -> str | None:
    """Replace a key's value within a TOML section, preserving all other lines.

    Returns the modified text, or None if the key wasn't found.
    """
    import re

    lines = text.split("\n")
    in_section = False
    section_header = re.compile(rf"^\[{re.escape(section)}\]\s*$")
    key_pattern = re.compile(rf"^({re.escape(key)}\s*=\s*).*$")

    for i, line in enumerate(lines):
        stripped = line.strip()
        if section_header.match(stripped):
            in_section = True
            continue
        if stripped.startswith("[") and in_section:
            break  # entered another section
        if in_section and key_pattern.match(stripped):
            m = key_pattern.match(stripped)
            assert m is not None
            leading = line[: len(line) - len(line.lstrip())]
            lines[i] = leading + m.group(1) + _toml_value(value)
            return "\n".join(lines)
    return None


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
