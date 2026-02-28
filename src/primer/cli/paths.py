"""Path constants for Primer CLI (~/.primer/ layout)."""

import platform
from pathlib import Path

PRIMER_HOME = Path.home() / ".primer"
CONFIG_FILE = PRIMER_HOME / "config.toml"
DATABASE_FILE = PRIMER_HOME / "primer.db"
LOG_DIR = PRIMER_HOME / "logs"
SERVER_LOG = LOG_DIR / "server.log"
PID_FILE = PRIMER_HOME / "server.pid"

# Platform-specific service paths
_system = platform.system()
if _system == "Darwin":
    LAUNCHD_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.primer.server.plist"
    SYSTEMD_UNIT = None
elif _system == "Linux":
    LAUNCHD_PLIST = None
    SYSTEMD_UNIT = Path.home() / ".config" / "systemd" / "user" / "primer-server.service"
else:
    LAUNCHD_PLIST = None
    SYSTEMD_UNIT = None


def ensure_dirs() -> None:
    """Create ~/.primer/ and subdirectories if they don't exist."""
    PRIMER_HOME.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
