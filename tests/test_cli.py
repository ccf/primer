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


# ---------------------------------------------------------------------------
# setup command
# ---------------------------------------------------------------------------


def test_setup_success(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[server]\nurl = "http://localhost:8000"\n')
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)
    monkeypatch.delenv("PRIMER_SERVER_URL", raising=False)
    monkeypatch.delenv("PRIMER_ADMIN_API_KEY", raising=False)

    # Mock git config returning name/email
    import subprocess as _sp

    orig_run = _sp.run

    def fake_git_run(cmd, **kw):
        if cmd == ["git", "config", "user.name"]:
            return type("R", (), {"stdout": "Test User", "returncode": 0})()
        if cmd == ["git", "config", "user.email"]:
            return type("R", (), {"stdout": "test@example.com", "returncode": 0})()
        return orig_run(cmd, **kw)

    monkeypatch.setattr("primer.cli.commands.setup.subprocess.run", fake_git_run)

    # Mock httpx.post to return 200 with api_key
    class FakeResp:
        status_code = 200

        def json(self):
            return {"id": "eng-123", "api_key": "key-abc"}

    monkeypatch.setattr("httpx.post", lambda *a, **kw: FakeResp())

    runner = CliRunner()
    result = runner.invoke(cli, ["setup"])
    assert result.exit_code == 0
    assert "registered" in result.output.lower()
    assert "eng-123" in result.output


def test_setup_with_flags(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[server]\n")
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)
    monkeypatch.delenv("PRIMER_SERVER_URL", raising=False)
    monkeypatch.delenv("PRIMER_ADMIN_API_KEY", raising=False)

    class FakeResp:
        status_code = 200

        def json(self):
            return {"id": "eng-456", "api_key": "key-def"}

    monkeypatch.setattr("httpx.post", lambda *a, **kw: FakeResp())

    runner = CliRunner()
    result = runner.invoke(cli, ["setup", "--name", "Bob", "--email", "bob@test.com"])
    assert result.exit_code == 0
    assert "eng-456" in result.output


def test_setup_server_error(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[server]\n")
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)
    monkeypatch.delenv("PRIMER_SERVER_URL", raising=False)
    monkeypatch.delenv("PRIMER_ADMIN_API_KEY", raising=False)

    class FakeResp:
        status_code = 400
        text = "Bad request"

    monkeypatch.setattr("httpx.post", lambda *a, **kw: FakeResp())

    runner = CliRunner()
    result = runner.invoke(cli, ["setup", "--name", "Bob", "--email", "bob@test.com"])
    assert result.exit_code == 0
    assert "failed" in result.output.lower()


def test_setup_network_error(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[server]\n")
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)
    monkeypatch.delenv("PRIMER_SERVER_URL", raising=False)
    monkeypatch.delenv("PRIMER_ADMIN_API_KEY", raising=False)

    import httpx

    def raise_connect_error(*a, **kw):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr("httpx.post", raise_connect_error)

    runner = CliRunner()
    result = runner.invoke(cli, ["setup", "--name", "Bob", "--email", "bob@test.com"])
    assert result.exit_code == 0
    assert "could not reach" in result.output.lower()


# ---------------------------------------------------------------------------
# server start / stop / logs
# ---------------------------------------------------------------------------


def test_server_start_success(monkeypatch, tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[server]\n")
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)
    monkeypatch.delenv("PRIMER_SERVER_HOST", raising=False)
    monkeypatch.delenv("PRIMER_SERVER_PORT", raising=False)

    monkeypatch.setattr(
        "primer.cli.server_manager.start_server",
        lambda host, port, foreground: (True, "Server started (PID 42)."),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "start"])
    assert result.exit_code == 0
    assert "started" in result.output.lower()


def test_server_start_failure(monkeypatch, tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[server]\n")
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)
    monkeypatch.delenv("PRIMER_SERVER_HOST", raising=False)
    monkeypatch.delenv("PRIMER_SERVER_PORT", raising=False)

    monkeypatch.setattr(
        "primer.cli.server_manager.start_server",
        lambda host, port, foreground: (False, "Already running (PID 10)."),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "start"])
    assert result.exit_code == 1
    assert "already running" in result.output.lower()


def test_server_stop_success(monkeypatch):
    monkeypatch.setattr(
        "primer.cli.server_manager.stop_server",
        lambda: (True, "Server stopped (PID 42)."),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "stop"])
    assert result.exit_code == 0
    assert "stopped" in result.output.lower()


def test_server_stop_warn(monkeypatch):
    monkeypatch.setattr(
        "primer.cli.server_manager.stop_server",
        lambda: (False, "No PID file found."),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "stop"])
    assert result.exit_code == 0
    assert "no pid file" in result.output.lower()


def test_server_logs_missing_file(monkeypatch, tmp_path):
    log_file = tmp_path / "nonexistent.log"
    monkeypatch.setattr("primer.cli.paths.SERVER_LOG", log_file)

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "logs"])
    assert result.exit_code == 0
    assert "not found" in result.output.lower()


def test_server_logs_runs_tail(monkeypatch, tmp_path):
    log_file = tmp_path / "server.log"
    log_file.write_text("line1\nline2\n")
    monkeypatch.setattr("primer.cli.paths.SERVER_LOG", log_file)

    captured_cmd = []

    def fake_run(cmd, **kw):
        captured_cmd.extend(cmd)

    monkeypatch.setattr("primer.cli.commands.server.subprocess.run", fake_run)

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "logs", "-n", "10"])
    assert result.exit_code == 0
    assert "tail" in captured_cmd
    assert str(log_file) in captured_cmd


# ---------------------------------------------------------------------------
# sync command
# ---------------------------------------------------------------------------


def test_sync_success_with_counts(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[auth]\napi_key = "test-key"\n')
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)
    monkeypatch.delenv("PRIMER_API_KEY", raising=False)
    monkeypatch.delenv("PRIMER_SERVER_URL", raising=False)

    monkeypatch.setattr(
        "primer.mcp.sync.sync_sessions",
        lambda url, key: {"local_count": 10, "already_synced": 7, "synced": 3, "errors": 0},
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["sync"])
    assert result.exit_code == 0
    assert "10" in result.output
    assert "3" in result.output
    assert "sync complete" in result.output.lower()


def test_sync_with_errors(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[auth]\napi_key = "test-key"\n')
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)
    monkeypatch.delenv("PRIMER_API_KEY", raising=False)
    monkeypatch.delenv("PRIMER_SERVER_URL", raising=False)

    monkeypatch.setattr(
        "primer.mcp.sync.sync_sessions",
        lambda url, key: {"local_count": 5, "already_synced": 2, "synced": 1, "errors": 2},
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["sync"])
    assert result.exit_code == 0
    assert "2" in result.output
    assert "failed" in result.output.lower()


# ---------------------------------------------------------------------------
# doctor command
# ---------------------------------------------------------------------------


def test_doctor_all_checks_pass(tmp_path, monkeypatch):
    primer_home = _patch_primer_home(monkeypatch, tmp_path)
    primer_home.mkdir(parents=True)
    config_file = primer_home / "config.toml"
    db_file = primer_home / "primer.db"

    config_file.write_text(
        '[auth]\nadmin_api_key = "primer-admin-0123456789abcdef"\n'
        'api_key = "primer-key-0123456789ab"\n'
    )
    db_file.touch()
    monkeypatch.delenv("PRIMER_ADMIN_API_KEY", raising=False)
    monkeypatch.delenv("PRIMER_API_KEY", raising=False)
    monkeypatch.delenv("PRIMER_SERVER_URL", raising=False)

    # Mock server status
    monkeypatch.setattr(
        "primer.cli.server_manager.server_status",
        lambda: {"running": True, "pid": 42, "strategy": "pidfile"},
    )

    # Mock server reachable
    class FakeResp:
        status_code = 200

    monkeypatch.setattr("httpx.get", lambda *a, **kw: FakeResp())

    # Mock hook installed
    monkeypatch.setattr(
        "primer.hook.installer.status",
        lambda: (True, "Installed"),
    )

    # Mock MCP registered — patch Path.home so doctor finds claude settings in tmp
    import pathlib

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text('{"mcpServers": {"primer": {}}}')
    monkeypatch.setattr(pathlib.Path, "home", staticmethod(lambda: tmp_path))

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "all checks passed" in result.output.lower()


def test_doctor_server_unreachable(tmp_path, monkeypatch):
    primer_home = _patch_primer_home(monkeypatch, tmp_path)
    primer_home.mkdir(parents=True)
    config_file = primer_home / "config.toml"
    config_file.write_text('[auth]\nadmin_api_key = "primer-admin-0123456789abcdef"\n')
    monkeypatch.delenv("PRIMER_ADMIN_API_KEY", raising=False)
    monkeypatch.delenv("PRIMER_API_KEY", raising=False)
    monkeypatch.delenv("PRIMER_SERVER_URL", raising=False)

    # Mock server status — not running
    monkeypatch.setattr(
        "primer.cli.server_manager.server_status",
        lambda: {"running": False, "pid": None, "strategy": "pidfile"},
    )

    # Mock httpx.get to raise
    import httpx

    def raise_error(*a, **kw):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr("httpx.get", raise_error)

    # Mock hook not installed
    monkeypatch.setattr(
        "primer.hook.installer.status",
        lambda: (False, "Not installed"),
    )

    # No claude settings — patch Path.home so doctor looks in tmp (no settings.json)
    import pathlib

    monkeypatch.setattr(pathlib.Path, "home", staticmethod(lambda: tmp_path))

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "cannot reach" in result.output.lower()


# ---------------------------------------------------------------------------
# configure command — additional coverage
# ---------------------------------------------------------------------------


def test_configure_get_sensitive_key_masked(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[auth]\napi_key = "primer-key-abcdef0123456789"\n')
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)

    runner = CliRunner()
    result = runner.invoke(cli, ["configure", "get", "auth.api_key"])
    assert result.exit_code == 0
    # Value should be truncated with "..."
    assert "..." in result.output
    # Full key should NOT appear
    assert "primer-key-abcdef0123456789" not in result.output


def test_configure_list_empty_config(tmp_path, monkeypatch):
    config_file = tmp_path / "nonexistent.toml"
    monkeypatch.setattr("primer.cli.config.CONFIG_FILE", config_file)

    runner = CliRunner()
    result = runner.invoke(cli, ["configure", "list"])
    assert result.exit_code == 0
    assert "no config" in result.output.lower()


# ---------------------------------------------------------------------------
# init command — migration failure
# ---------------------------------------------------------------------------


def test_init_migration_failure(tmp_path, monkeypatch):
    _patch_primer_home(monkeypatch, tmp_path)

    def failing_upgrade(cfg, rev):
        raise RuntimeError("migration exploded")

    monkeypatch.setattr("alembic.command.upgrade", failing_upgrade)

    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code != 0
    assert "migration failed" in result.output.lower()
