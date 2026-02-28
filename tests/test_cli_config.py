"""Tests for primer.cli.config — TOML read/write and env var bridge."""

import os

from primer.cli.config import (
    _toml_value,
    get_value,
    load_config_into_env,
    read_config,
    set_value,
    write_config,
)


def test_read_config_missing_file(tmp_path):
    result = read_config(tmp_path / "nonexistent.toml")
    assert result == {}


def test_write_and_read_config(tmp_path):
    path = tmp_path / "config.toml"
    write_config('[server]\nport = 9000\nhost = "127.0.0.1"\n', path)
    cfg = read_config(path)
    assert cfg["server"]["port"] == 9000
    assert cfg["server"]["host"] == "127.0.0.1"


def test_get_value(tmp_path):
    path = tmp_path / "config.toml"
    write_config('[server]\nport = 9000\n[auth]\napi_key = "abc123"\n', path)
    assert get_value("server.port", path) == "9000"
    assert get_value("auth.api_key", path) == "abc123"
    assert get_value("missing.key", path) is None


def test_set_value_creates_section(tmp_path):
    path = tmp_path / "config.toml"
    write_config("[server]\nport = 8000\n", path)
    set_value("auth.api_key", "new-key", path)
    assert get_value("auth.api_key", path) == "new-key"
    # Existing values preserved
    assert get_value("server.port", path) == "8000"


def test_set_value_overwrites(tmp_path):
    path = tmp_path / "config.toml"
    write_config('[server]\nport = 8000\nhost = "0.0.0.0"\n', path)
    set_value("server.port", "9000", path)
    assert get_value("server.port", path) == "9000"


def test_load_config_into_env(tmp_path, monkeypatch):
    path = tmp_path / "config.toml"
    write_config(
        '[server]\nhost = "10.0.0.1"\nport = 3000\n[auth]\nadmin_api_key = "secret"\n',
        path,
    )

    # Clear relevant env vars
    for var in ("PRIMER_SERVER_HOST", "PRIMER_SERVER_PORT", "PRIMER_ADMIN_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    load_config_into_env(path)

    assert os.environ["PRIMER_SERVER_HOST"] == "10.0.0.1"
    assert os.environ["PRIMER_SERVER_PORT"] == "3000"
    assert os.environ["PRIMER_ADMIN_API_KEY"] == "secret"


def test_load_config_env_precedence(tmp_path, monkeypatch):
    """Env vars already set should NOT be overwritten by config.toml."""
    path = tmp_path / "config.toml"
    write_config('[server]\nhost = "from-config"\n', path)

    monkeypatch.setenv("PRIMER_SERVER_HOST", "from-env")
    load_config_into_env(path)

    assert os.environ["PRIMER_SERVER_HOST"] == "from-env"


# ---------------------------------------------------------------------------
# _toml_value serialization
# ---------------------------------------------------------------------------


def test_toml_value_bool():
    assert _toml_value(True) == "true"
    assert _toml_value(False) == "false"


def test_toml_value_int():
    assert _toml_value(42) == "42"
    assert _toml_value(0) == "0"


def test_toml_value_float():
    assert _toml_value(3.14) == "3.14"


def test_toml_value_string():
    assert _toml_value("hello") == '"hello"'
    assert _toml_value("") == '""'
