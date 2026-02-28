"""Tests for primer.cli.server_manager — process management strategies."""

import os
import signal
from unittest.mock import MagicMock

from primer.cli import server_manager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_pidfile_paths(monkeypatch, tmp_path):
    """Redirect PID_FILE, LOG_DIR, SERVER_LOG to tmp_path."""
    pid_file = tmp_path / "server.pid"
    log_dir = tmp_path / "logs"
    server_log = log_dir / "server.log"
    monkeypatch.setattr("primer.cli.server_manager.PID_FILE", pid_file)
    monkeypatch.setattr("primer.cli.server_manager.LOG_DIR", log_dir)
    monkeypatch.setattr("primer.cli.server_manager.SERVER_LOG", server_log)
    return pid_file, log_dir, server_log


# ---------------------------------------------------------------------------
# _pid_alive
# ---------------------------------------------------------------------------


def test_pid_alive_true(monkeypatch):
    monkeypatch.setattr(os, "kill", lambda pid, sig: None)
    assert server_manager._pid_alive(1234) is True


def test_pid_alive_false(monkeypatch):
    def _raise(pid, sig):
        raise OSError("No such process")

    monkeypatch.setattr(os, "kill", _raise)
    assert server_manager._pid_alive(1234) is False


# ---------------------------------------------------------------------------
# _pidfile_start
# ---------------------------------------------------------------------------


def test_pidfile_start_success(monkeypatch, tmp_path):
    pid_file, _log_dir, _server_log = _patch_pidfile_paths(monkeypatch, tmp_path)

    mock_proc = MagicMock()
    mock_proc.pid = 42

    monkeypatch.setattr(
        "primer.cli.server_manager.subprocess.Popen",
        lambda *a, **kw: mock_proc,
    )

    ok, msg = server_manager._pidfile_start("127.0.0.1", 8000)
    assert ok is True
    assert "42" in msg
    assert pid_file.exists()
    assert pid_file.read_text() == "42"


def test_pidfile_start_already_running(monkeypatch, tmp_path):
    pid_file, _, _ = _patch_pidfile_paths(monkeypatch, tmp_path)
    pid_file.write_text("99")
    monkeypatch.setattr("primer.cli.server_manager._pid_alive", lambda pid: True)

    ok, msg = server_manager._pidfile_start("127.0.0.1", 8000)
    assert ok is False
    assert "already running" in msg.lower()


def test_pidfile_start_stale_pid_restarts(monkeypatch, tmp_path):
    """If PID file exists but process is dead, a new server starts."""
    pid_file, _log_dir, _server_log = _patch_pidfile_paths(monkeypatch, tmp_path)
    pid_file.write_text("99")
    monkeypatch.setattr("primer.cli.server_manager._pid_alive", lambda pid: False)

    mock_proc = MagicMock()
    mock_proc.pid = 200
    monkeypatch.setattr(
        "primer.cli.server_manager.subprocess.Popen",
        lambda *a, **kw: mock_proc,
    )

    ok, msg = server_manager._pidfile_start("127.0.0.1", 8000)
    assert ok is True
    assert "200" in msg


# ---------------------------------------------------------------------------
# _pidfile_stop
# ---------------------------------------------------------------------------


def test_pidfile_stop_success(monkeypatch, tmp_path):
    pid_file, _, _ = _patch_pidfile_paths(monkeypatch, tmp_path)
    pid_file.write_text("42")

    monkeypatch.setattr("primer.cli.server_manager._pid_alive", lambda pid: True)
    killed = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append((pid, sig)))

    ok, msg = server_manager._pidfile_stop()
    assert ok is True
    assert "42" in msg
    assert killed == [(42, signal.SIGTERM)]
    assert not pid_file.exists()


def test_pidfile_stop_no_pidfile(monkeypatch, tmp_path):
    _patch_pidfile_paths(monkeypatch, tmp_path)
    ok, msg = server_manager._pidfile_stop()
    assert ok is False
    assert "no pid file" in msg.lower()


def test_pidfile_stop_stale_pid(monkeypatch, tmp_path):
    pid_file, _, _ = _patch_pidfile_paths(monkeypatch, tmp_path)
    pid_file.write_text("99")
    monkeypatch.setattr("primer.cli.server_manager._pid_alive", lambda pid: False)

    ok, msg = server_manager._pidfile_stop()
    assert ok is False
    assert "not running" in msg.lower()
    assert not pid_file.exists()


# ---------------------------------------------------------------------------
# _pidfile_status
# ---------------------------------------------------------------------------


def test_pidfile_status_alive(monkeypatch, tmp_path):
    pid_file, _, _ = _patch_pidfile_paths(monkeypatch, tmp_path)
    pid_file.write_text("42")
    monkeypatch.setattr("primer.cli.server_manager._pid_alive", lambda pid: True)

    status = server_manager._pidfile_status()
    assert status["running"] is True
    assert status["pid"] == 42
    assert status["strategy"] == "pidfile"


def test_pidfile_status_not_alive(monkeypatch, tmp_path):
    pid_file, _, _ = _patch_pidfile_paths(monkeypatch, tmp_path)
    pid_file.write_text("99")
    monkeypatch.setattr("primer.cli.server_manager._pid_alive", lambda pid: False)

    status = server_manager._pidfile_status()
    assert status["running"] is False
    assert status["pid"] is None
    # Stale PID file cleaned up
    assert not pid_file.exists()


def test_pidfile_status_no_pidfile(monkeypatch, tmp_path):
    _patch_pidfile_paths(monkeypatch, tmp_path)
    status = server_manager._pidfile_status()
    assert status == {"running": False, "pid": None, "strategy": "pidfile"}


# ---------------------------------------------------------------------------
# start_server foreground
# ---------------------------------------------------------------------------


def test_start_server_foreground(monkeypatch):
    called = {}

    def fake_uvicorn_run(app, host, port):
        called["app"] = app
        called["host"] = host
        called["port"] = port

    monkeypatch.setattr("uvicorn.run", fake_uvicorn_run)
    ok, _msg = server_manager.start_server(host="0.0.0.0", port=9000, foreground=True)
    assert ok is True
    assert called["host"] == "0.0.0.0"
    assert called["port"] == 9000


# ---------------------------------------------------------------------------
# Public API routing (start_server / stop_server / server_status)
# ---------------------------------------------------------------------------


def test_start_server_routes_to_pidfile(monkeypatch, tmp_path):
    _patch_pidfile_paths(monkeypatch, tmp_path)
    monkeypatch.setattr("primer.cli.server_manager.get_strategy", lambda: "pidfile")

    mock_proc = MagicMock()
    mock_proc.pid = 77
    monkeypatch.setattr(
        "primer.cli.server_manager.subprocess.Popen",
        lambda *a, **kw: mock_proc,
    )

    ok, msg = server_manager.start_server(host="127.0.0.1", port=8000)
    assert ok is True
    assert "77" in msg


def test_stop_server_routes_to_pidfile(monkeypatch, tmp_path):
    _patch_pidfile_paths(monkeypatch, tmp_path)
    monkeypatch.setattr("primer.cli.server_manager.get_strategy", lambda: "pidfile")
    # No PID file → returns False
    ok, _msg = server_manager.stop_server()
    assert ok is False


def test_server_status_routes_to_pidfile(monkeypatch, tmp_path):
    _patch_pidfile_paths(monkeypatch, tmp_path)
    monkeypatch.setattr("primer.cli.server_manager.get_strategy", lambda: "pidfile")
    status = server_manager.server_status()
    assert status["strategy"] == "pidfile"


# ---------------------------------------------------------------------------
# _write_launchd_plist
# ---------------------------------------------------------------------------


def test_write_launchd_plist(monkeypatch, tmp_path):
    plist_path = tmp_path / "com.primer.server.plist"
    monkeypatch.setattr("primer.cli.server_manager.LAUNCHD_PLIST", plist_path)
    monkeypatch.setattr("primer.cli.server_manager.SERVER_LOG", tmp_path / "server.log")

    server_manager._write_launchd_plist("127.0.0.1", 8000)

    content = plist_path.read_text()
    assert "com.primer.server" in content
    assert "127.0.0.1" in content  # host in args
    assert "8000" in content  # port in args
    assert "<plist" in content
    assert "uvicorn" in content


# ---------------------------------------------------------------------------
# _write_systemd_unit
# ---------------------------------------------------------------------------


def test_write_systemd_unit(monkeypatch, tmp_path):
    unit_path = tmp_path / "primer-server.service"
    monkeypatch.setattr("primer.cli.server_manager.SYSTEMD_UNIT", unit_path)
    monkeypatch.setattr("primer.cli.server_manager.SERVER_LOG", tmp_path / "server.log")

    server_manager._write_systemd_unit("0.0.0.0", 9000)

    content = unit_path.read_text()
    assert "Primer Server" in content
    assert "0.0.0.0" in content
    assert "9000" in content
    assert "[Unit]" in content
    assert "uvicorn" in content


# ---------------------------------------------------------------------------
# get_strategy
# ---------------------------------------------------------------------------


def test_get_strategy_darwin(monkeypatch):
    monkeypatch.setattr("primer.cli.server_manager.platform.system", lambda: "Darwin")
    monkeypatch.setattr("primer.cli.server_manager.LAUNCHD_PLIST", "/fake/path")
    assert server_manager.get_strategy() == "launchd"


def test_get_strategy_linux(monkeypatch):
    monkeypatch.setattr("primer.cli.server_manager.platform.system", lambda: "Linux")
    monkeypatch.setattr("primer.cli.server_manager.LAUNCHD_PLIST", None)
    monkeypatch.setattr("primer.cli.server_manager.SYSTEMD_UNIT", "/fake/path")
    assert server_manager.get_strategy() == "systemd"


def test_get_strategy_fallback(monkeypatch):
    monkeypatch.setattr("primer.cli.server_manager.platform.system", lambda: "Windows")
    monkeypatch.setattr("primer.cli.server_manager.LAUNCHD_PLIST", None)
    monkeypatch.setattr("primer.cli.server_manager.SYSTEMD_UNIT", None)
    assert server_manager.get_strategy() == "pidfile"


def test_get_strategy_darwin_no_plist(monkeypatch):
    monkeypatch.setattr("primer.cli.server_manager.platform.system", lambda: "Darwin")
    monkeypatch.setattr("primer.cli.server_manager.LAUNCHD_PLIST", None)
    assert server_manager.get_strategy() == "pidfile"


# ---------------------------------------------------------------------------
# launchd strategy
# ---------------------------------------------------------------------------


def test_launchd_start(monkeypatch, tmp_path):
    plist_path = tmp_path / "com.primer.server.plist"
    monkeypatch.setattr("primer.cli.server_manager.LAUNCHD_PLIST", plist_path)
    monkeypatch.setattr("primer.cli.server_manager.SERVER_LOG", tmp_path / "server.log")

    cmds_run = []

    def fake_run(cmd, **kw):
        cmds_run.append(cmd)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr("primer.cli.server_manager.subprocess.run", fake_run)

    ok, msg = server_manager._launchd_start("127.0.0.1", 8000)
    assert ok is True
    assert "launchd" in msg.lower()
    assert plist_path.exists()
    assert any("launchctl" in c[0] for c in cmds_run)


def test_launchd_stop_success(monkeypatch, tmp_path):
    plist_path = tmp_path / "com.primer.server.plist"
    plist_path.write_text("<plist/>")
    monkeypatch.setattr("primer.cli.server_manager.LAUNCHD_PLIST", plist_path)

    monkeypatch.setattr(
        "primer.cli.server_manager.subprocess.run",
        lambda cmd, **kw: type("R", (), {"returncode": 0})(),
    )

    ok, msg = server_manager._launchd_stop()
    assert ok is True
    assert "launchd" in msg.lower()


def test_launchd_stop_no_plist(monkeypatch, tmp_path):
    plist_path = tmp_path / "nonexistent.plist"
    monkeypatch.setattr("primer.cli.server_manager.LAUNCHD_PLIST", plist_path)

    ok, msg = server_manager._launchd_stop()
    assert ok is False
    assert "not found" in msg.lower()


def test_launchd_status_running(monkeypatch):
    monkeypatch.setattr(
        "primer.cli.server_manager.subprocess.run",
        lambda cmd, **kw: type(
            "R", (), {"returncode": 0, "stdout": "42\t0\tcom.primer.server\n"}
        )(),
    )

    status = server_manager._launchd_status()
    assert status["running"] is True
    assert status["pid"] == 42
    assert status["strategy"] == "launchd"


def test_launchd_status_not_running(monkeypatch):
    monkeypatch.setattr(
        "primer.cli.server_manager.subprocess.run",
        lambda cmd, **kw: type("R", (), {"returncode": 1, "stdout": ""})(),
    )

    status = server_manager._launchd_status()
    assert status["running"] is False
    assert status["pid"] is None


# ---------------------------------------------------------------------------
# systemd strategy
# ---------------------------------------------------------------------------


def test_systemd_start(monkeypatch, tmp_path):
    unit_path = tmp_path / "primer-server.service"
    monkeypatch.setattr("primer.cli.server_manager.SYSTEMD_UNIT", unit_path)
    monkeypatch.setattr("primer.cli.server_manager.SERVER_LOG", tmp_path / "server.log")

    cmds_run = []

    def fake_run(cmd, **kw):
        cmds_run.append(cmd)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr("primer.cli.server_manager.subprocess.run", fake_run)

    ok, msg = server_manager._systemd_start("0.0.0.0", 9000)
    assert ok is True
    assert "systemd" in msg.lower()
    assert unit_path.exists()
    assert any("systemctl" in c[0] for c in cmds_run)


def test_systemd_stop(monkeypatch):
    monkeypatch.setattr(
        "primer.cli.server_manager.subprocess.run",
        lambda cmd, **kw: type("R", (), {"returncode": 0})(),
    )

    ok, msg = server_manager._systemd_stop()
    assert ok is True
    assert "systemd" in msg.lower()


def test_systemd_status_active(monkeypatch):
    call_count = [0]

    def fake_run(cmd, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            # is-active
            return type("R", (), {"returncode": 0, "stdout": "active\n"})()
        # show MainPID
        return type("R", (), {"returncode": 0, "stdout": "MainPID=99\n"})()

    monkeypatch.setattr("primer.cli.server_manager.subprocess.run", fake_run)

    status = server_manager._systemd_status()
    assert status["running"] is True
    assert status["pid"] == 99
    assert status["strategy"] == "systemd"


def test_systemd_status_inactive(monkeypatch):
    monkeypatch.setattr(
        "primer.cli.server_manager.subprocess.run",
        lambda cmd, **kw: type("R", (), {"returncode": 0, "stdout": "inactive\n"})(),
    )

    status = server_manager._systemd_status()
    assert status["running"] is False
    assert status["pid"] is None


# ---------------------------------------------------------------------------
# Public API routing to launchd / systemd
# ---------------------------------------------------------------------------


def test_start_server_routes_to_launchd(monkeypatch, tmp_path):
    monkeypatch.setattr("primer.cli.server_manager.get_strategy", lambda: "launchd")
    plist_path = tmp_path / "com.primer.server.plist"
    monkeypatch.setattr("primer.cli.server_manager.LAUNCHD_PLIST", plist_path)
    monkeypatch.setattr("primer.cli.server_manager.SERVER_LOG", tmp_path / "server.log")
    monkeypatch.setattr(
        "primer.cli.server_manager.subprocess.run",
        lambda cmd, **kw: type("R", (), {"returncode": 0})(),
    )

    ok, msg = server_manager.start_server(host="127.0.0.1", port=8000)
    assert ok is True
    assert "launchd" in msg.lower()


def test_stop_server_routes_to_systemd(monkeypatch):
    monkeypatch.setattr("primer.cli.server_manager.get_strategy", lambda: "systemd")
    monkeypatch.setattr(
        "primer.cli.server_manager.subprocess.run",
        lambda cmd, **kw: type("R", (), {"returncode": 0})(),
    )

    ok, msg = server_manager.stop_server()
    assert ok is True
    assert "systemd" in msg.lower()


def test_server_status_routes_to_launchd(monkeypatch):
    monkeypatch.setattr("primer.cli.server_manager.get_strategy", lambda: "launchd")
    monkeypatch.setattr(
        "primer.cli.server_manager.subprocess.run",
        lambda cmd, **kw: type("R", (), {"returncode": 1, "stdout": ""})(),
    )

    status = server_manager.server_status()
    assert status["strategy"] == "launchd"
