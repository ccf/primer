"""Background server process management (launchd / systemd / pidfile)."""

import os
import platform
import signal
import subprocess
import sys
import textwrap
from pathlib import Path

from primer.cli.paths import (
    LAUNCHD_PLIST,
    LOG_DIR,
    PID_FILE,
    SERVER_LOG,
    SYSTEMD_UNIT,
)


def get_strategy() -> str:
    """Determine the best process management strategy for this platform."""
    system = platform.system()
    if system == "Darwin" and LAUNCHD_PLIST is not None:
        return "launchd"
    if system == "Linux" and SYSTEMD_UNIT is not None:
        return "systemd"
    return "pidfile"


def _xml_escape(s: str) -> str:
    """Escape XML special characters in a string."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _server_env() -> dict[str, str]:
    """Build environment dict for the server subprocess, inheriting current env.

    Also loads .env file (if present) so PRIMER_* vars like GitHub OAuth
    and Anthropic API keys are available to the managed server process.
    """
    from dotenv import dotenv_values

    env = os.environ.copy()
    # Load .env file if it exists (doesn't override already-set vars)
    for env_path in [Path(".env"), Path.home() / ".primer" / ".env"]:
        if env_path.exists():
            for key, value in dotenv_values(env_path).items():
                if key not in env:
                    env[key] = value or ""
    return env


def _uvicorn_args(host: str, port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "primer.server.app:app",
        "--host",
        host,
        "--port",
        str(port),
    ]


# ---------------------------------------------------------------------------
# launchd (macOS)
# ---------------------------------------------------------------------------

_PLIST_TEMPLATE = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
      "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
        <key>Label</key>
        <string>com.primer.server</string>
        <key>ProgramArguments</key>
        <array>
            {args_xml}
        </array>
        <key>EnvironmentVariables</key>
        <dict>
            {env_xml}
        </dict>
        <key>RunAtLoad</key>
        <false/>
        <key>KeepAlive</key>
        <false/>
        <key>StandardOutPath</key>
        <string>{log_path}</string>
        <key>StandardErrorPath</key>
        <string>{log_path}</string>
    </dict>
    </plist>
""")


def _write_launchd_plist(host: str, port: int) -> None:
    assert LAUNCHD_PLIST is not None
    args = _uvicorn_args(host, port)
    args_xml = "\n            ".join(f"<string>{_xml_escape(a)}</string>" for a in args)
    env = _server_env()
    env_lines = []
    # Forward all PRIMER_* env vars + PATH so the server picks up full config
    for k, v in sorted(env.items()):
        if k.startswith("PRIMER_") or k == "PATH":
            env_lines.append(f"<key>{k}</key>\n            <string>{_xml_escape(v)}</string>")
    env_xml = "\n            ".join(env_lines)
    content = _PLIST_TEMPLATE.format(
        args_xml=args_xml, env_xml=env_xml, log_path=_xml_escape(str(SERVER_LOG))
    )
    LAUNCHD_PLIST.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHD_PLIST.write_text(content)


def _launchd_start(host: str, port: int) -> tuple[bool, str]:
    _write_launchd_plist(host, port)
    subprocess.run(["launchctl", "load", str(LAUNCHD_PLIST)], check=True)
    subprocess.run(["launchctl", "start", "com.primer.server"], check=True)
    return True, "Server started via launchd."


def _launchd_stop() -> tuple[bool, str]:
    assert LAUNCHD_PLIST is not None
    if not LAUNCHD_PLIST.exists():
        return False, "launchd plist not found. Server may not be managed by launchd."
    subprocess.run(["launchctl", "stop", "com.primer.server"], check=False)
    subprocess.run(["launchctl", "unload", str(LAUNCHD_PLIST)], check=False)
    return True, "Server stopped via launchd."


def _launchd_status() -> dict:
    result = subprocess.run(
        ["launchctl", "list", "com.primer.server"],
        capture_output=True,
        text=True,
    )
    running = result.returncode == 0
    pid = None
    if running:
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 1 and parts[0].isdigit():
                pid = int(parts[0])
                break
    return {"running": running, "pid": pid, "strategy": "launchd"}


# ---------------------------------------------------------------------------
# systemd (Linux)
# ---------------------------------------------------------------------------

_UNIT_TEMPLATE = textwrap.dedent("""\
    [Unit]
    Description=Primer Server
    After=network.target

    [Service]
    Type=simple
    ExecStart={exec_start}
    {env_lines}
    StandardOutput=append:{log_path}
    StandardError=append:{log_path}
    Restart=on-failure

    [Install]
    WantedBy=default.target
""")


def _write_systemd_unit(host: str, port: int) -> None:
    assert SYSTEMD_UNIT is not None
    args = _uvicorn_args(host, port)
    exec_start = " ".join(args)
    env = _server_env()
    env_lines = []
    # Forward all PRIMER_* env vars so the server picks up full config
    for k, v in sorted(env.items()):
        if k.startswith("PRIMER_"):
            env_lines.append(f"Environment={k}={v}")
    content = _UNIT_TEMPLATE.format(
        exec_start=exec_start,
        env_lines="\n".join(env_lines),
        log_path=str(SERVER_LOG),
    )
    SYSTEMD_UNIT.parent.mkdir(parents=True, exist_ok=True)
    SYSTEMD_UNIT.write_text(content)


def _systemd_start(host: str, port: int) -> tuple[bool, str]:
    _write_systemd_unit(host, port)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "start", "primer-server"], check=True)
    return True, "Server started via systemd."


def _systemd_stop() -> tuple[bool, str]:
    result = subprocess.run(
        ["systemctl", "--user", "stop", "primer-server"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, "Server may not be running (systemd stop failed)."
    return True, "Server stopped via systemd."


def _systemd_status() -> dict:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "primer-server"],
        capture_output=True,
        text=True,
    )
    running = result.stdout.strip() == "active"
    pid = None
    if running:
        pid_result = subprocess.run(
            ["systemctl", "--user", "show", "primer-server", "--property=MainPID"],
            capture_output=True,
            text=True,
        )
        for line in pid_result.stdout.splitlines():
            if line.startswith("MainPID="):
                pid = int(line.split("=")[1])
                break
    return {"running": running, "pid": pid, "strategy": "systemd"}


# ---------------------------------------------------------------------------
# pidfile fallback
# ---------------------------------------------------------------------------


def _pidfile_start(host: str, port: int) -> tuple[bool, str]:
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        if _pid_alive(pid):
            return False, f"Server already running (PID {pid})."

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = open(SERVER_LOG, "a")  # noqa: SIM115
    proc = subprocess.Popen(
        _uvicorn_args(host, port),
        env=_server_env(),
        stdout=log_file,
        stderr=log_file,
        start_new_session=True,
    )
    log_file.close()
    PID_FILE.write_text(str(proc.pid))
    return True, f"Server started (PID {proc.pid}). Logs: {SERVER_LOG}"


def _pidfile_stop() -> tuple[bool, str]:
    if not PID_FILE.exists():
        return False, "No PID file found. Server may not be running."
    pid = int(PID_FILE.read_text().strip())
    if not _pid_alive(pid):
        PID_FILE.unlink(missing_ok=True)
        return False, f"PID {pid} not running. Cleaned up stale PID file."
    os.kill(pid, signal.SIGTERM)
    PID_FILE.unlink(missing_ok=True)
    return True, f"Server stopped (PID {pid})."


def _pidfile_status() -> dict:
    if not PID_FILE.exists():
        return {"running": False, "pid": None, "strategy": "pidfile"}
    pid = int(PID_FILE.read_text().strip())
    running = _pid_alive(pid)
    if not running:
        PID_FILE.unlink(missing_ok=True)
    return {"running": running, "pid": pid if running else None, "strategy": "pidfile"}


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def start_server(
    host: str = "127.0.0.1", port: int = 8000, foreground: bool = False
) -> tuple[bool, str]:
    """Start the Primer server."""
    if foreground:
        # Run in foreground (blocking) — used for Docker / development
        import uvicorn

        uvicorn.run("primer.server.app:app", host=host, port=port)
        return True, "Server exited."

    strategy = get_strategy()
    if strategy == "launchd":
        return _launchd_start(host, port)
    if strategy == "systemd":
        return _systemd_start(host, port)
    return _pidfile_start(host, port)


def stop_server() -> tuple[bool, str]:
    """Stop the Primer server."""
    strategy = get_strategy()
    if strategy == "launchd":
        return _launchd_stop()
    if strategy == "systemd":
        return _systemd_stop()
    return _pidfile_stop()


def server_status() -> dict:
    """Return server status: {running, pid, strategy}."""
    strategy = get_strategy()
    if strategy == "launchd":
        return _launchd_status()
    if strategy == "systemd":
        return _systemd_status()
    return _pidfile_status()
