"""Integration tests for the Primer CLI using Click's CliRunner."""

import json

from click.testing import CliRunner

from primer.cli.main import cli


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "server" in result.output
    assert "hook" in result.output
    assert "doctor" in result.output


def _patch_primer_home(monkeypatch, tmp_path):
    """Redirect all primer.cli.paths constants to tmp_path."""
    primer_home = tmp_path / ".primer"
    monkeypatch.setattr("primer.cli.paths.PRIMER_HOME", primer_home)
    monkeypatch.setattr("primer.cli.paths.CONFIG_FILE", primer_home / "config.toml")
    monkeypatch.setattr("primer.cli.paths.DATABASE_FILE", primer_home / "primer.db")
    monkeypatch.setattr("primer.cli.paths.LOG_DIR", primer_home / "logs")
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", primer_home / "config.toml")
    return primer_home


def test_init_creates_config(tmp_path, monkeypatch):
    primer_home = _patch_primer_home(monkeypatch, tmp_path)
    config_file = primer_home / "config.toml"

    # Patch alembic to avoid real migrations
    monkeypatch.setattr("alembic.command.upgrade", lambda cfg, rev: None)

    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert config_file.exists()
    content = config_file.read_text()
    assert "admin_api_key" in content
    assert "primer-admin-" in content


def test_init_skips_existing_config(tmp_path, monkeypatch):
    primer_home = _patch_primer_home(monkeypatch, tmp_path)
    config_file = primer_home / "config.toml"
    primer_home.mkdir(parents=True)
    config_file.write_text("[server]\nport = 9999\n")

    monkeypatch.setattr("alembic.command.upgrade", lambda cfg, rev: None)

    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "already exists" in result.output
    # Original content preserved
    assert "9999" in config_file.read_text()


def test_hook_install_and_status(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr("primer.hook.installer.SETTINGS_PATH", settings_path)

    runner = CliRunner()

    # Install
    result = runner.invoke(cli, ["hook", "install"])
    assert result.exit_code == 0
    assert "installed" in result.output.lower()

    # Status
    result = runner.invoke(cli, ["hook", "status"])
    assert result.exit_code == 0
    assert "installed" in result.output.lower()

    # Uninstall
    result = runner.invoke(cli, ["hook", "uninstall"])
    assert result.exit_code == 0
    assert "removed" in result.output.lower()

    # Status after uninstall
    result = runner.invoke(cli, ["hook", "status"])
    assert result.exit_code == 0
    assert "not installed" in result.output.lower()


def test_configure_set_get_list(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[server]\nport = 8000\nhost = "localhost"\n')

    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)

    runner = CliRunner()

    # Get
    result = runner.invoke(cli, ["configure", "get", "server.port"])
    assert result.exit_code == 0
    assert "8000" in result.output

    # Set
    result = runner.invoke(cli, ["configure", "set", "server.port", "9000"])
    assert result.exit_code == 0
    assert "9000" in result.output

    # Verify set
    result = runner.invoke(cli, ["configure", "get", "server.port"])
    assert result.exit_code == 0
    assert "9000" in result.output

    # List
    result = runner.invoke(cli, ["configure", "list"])
    assert result.exit_code == 0
    assert "server" in result.output.lower()


def test_configure_get_missing_key(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[server]\nport = 8000\n")
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)

    runner = CliRunner()
    result = runner.invoke(cli, ["configure", "get", "nonexistent.key"])
    assert result.exit_code == 0
    assert "not set" in result.output.lower()


def test_server_subcommands_exist():
    runner = CliRunner()
    result = runner.invoke(cli, ["server", "--help"])
    assert result.exit_code == 0
    assert "start" in result.output
    assert "stop" in result.output
    assert "status" in result.output
    assert "logs" in result.output


def test_mcp_subcommands_exist():
    runner = CliRunner()
    result = runner.invoke(cli, ["mcp", "--help"])
    assert result.exit_code == 0
    assert "install" in result.output
    assert "uninstall" in result.output
    assert "serve" in result.output


def test_mcp_install_and_uninstall(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr("primer.cli.commands.mcp_cmd.CLAUDE_SETTINGS", settings_path)

    runner = CliRunner()

    # Install
    result = runner.invoke(cli, ["mcp", "install"])
    assert result.exit_code == 0
    assert "registered" in result.output.lower()

    data = json.loads(settings_path.read_text())
    assert "primer" in data["mcpServers"]

    # Install again (idempotent)
    result = runner.invoke(cli, ["mcp", "install"])
    assert result.exit_code == 0
    assert "already" in result.output.lower()

    # Uninstall
    result = runner.invoke(cli, ["mcp", "uninstall"])
    assert result.exit_code == 0
    assert "removed" in result.output.lower()

    data = json.loads(settings_path.read_text())
    assert "primer" not in data.get("mcpServers", {})


def test_sync_no_api_key(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[server]\nport = 8000\n")
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)
    monkeypatch.delenv("PRIMER_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["sync"])
    assert result.exit_code == 0
    assert "no api key" in result.output.lower()


def test_doctor_missing_home(tmp_path, monkeypatch):
    primer_home = tmp_path / ".primer-nonexistent"
    monkeypatch.setattr("primer.cli.paths.PRIMER_HOME", primer_home)
    monkeypatch.setattr("primer.cli.paths.CONFIG_FILE", primer_home / "config.toml")
    monkeypatch.setattr("primer.cli.paths.DATABASE_FILE", primer_home / "primer.db")
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", primer_home / "config.toml")

    # Mock server_status to avoid real process checks
    monkeypatch.setattr("primer.cli.server_manager.get_strategy", lambda: "pidfile")
    monkeypatch.setattr(
        "primer.cli.paths.PID_FILE",
        type("FakePath", (), {"exists": lambda self: False})(),
    )

    # Mock hook status to avoid real file access
    monkeypatch.setattr(
        "primer.hook.installer.SETTINGS_PATH",
        tmp_path / "nonexistent-settings.json",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "missing" in result.output.lower()


def test_server_status_not_running(monkeypatch):
    monkeypatch.setattr("primer.cli.server_manager.get_strategy", lambda: "pidfile")
    monkeypatch.setattr(
        "primer.cli.paths.PID_FILE",
        type("FakePath", (), {"exists": lambda self: False})(),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "status"])
    assert result.exit_code == 0
    assert "not running" in result.output.lower()
