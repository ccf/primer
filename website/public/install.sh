#!/bin/sh
# Primer installer — https://github.com/ccf/primer
#
# Usage:
#   curl -fsSL https://ccf.github.io/primer/install.sh | sh
#
# Environment variables:
#   PRIMER_REPO_URL       GitHub repo URL for forks (default: https://github.com/ccf/primer.git)
#   PRIMER_VERSION        Git tag or branch to install (default: main)
#   PRIMER_NO_COLOR       Disable colored output (no-color.org)
#   PRIMER_SKIP_FRONTEND  Skip frontend download
#   PRIMER_SERVER_PORT    Override server port (default: 8000)

set -eu

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

_color=1
if [ -n "${PRIMER_NO_COLOR:-}" ] || [ -n "${NO_COLOR:-}" ]; then
  _color=0
elif ! [ -t 1 ]; then
  _color=0
fi

_bold=""   _reset=""  _green=""  _red=""  _yellow=""  _cyan=""  _white=""
if [ "$_color" = 1 ]; then
  _bold='\033[1m'    _reset='\033[0m'
  _green='\033[32m'  _red='\033[31m'  _yellow='\033[33m'  _cyan='\033[36m'  _white='\033[37m'
fi

step_num=0

step() {
  step_num=$((step_num + 1))
  printf "${_bold}${_white}[%2d/10] %s${_reset}\n" "$step_num" "$1"
}

ok()   { printf "  ${_green}✓ %s${_reset}\n" "$1"; }
warn() { printf "  ${_yellow}! %s${_reset}\n" "$1"; }
err()  { printf "  ${_red}✗ %s${_reset}\n" "$1"; }
info() { printf "  ${_cyan}→ %s${_reset}\n" "$1"; }

die() {
  err "$1"
  exit 1
}

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

PRIMER_REPO_URL="${PRIMER_REPO_URL:-https://github.com/ccf/primer.git}"
PRIMER_VERSION="${PRIMER_VERSION:-main}"
PRIMER_SERVER_PORT="${PRIMER_SERVER_PORT:-8000}"
PRIMER_HOME="${HOME}/.primer"

# ---------------------------------------------------------------------------
# 1. Detect environment
# ---------------------------------------------------------------------------

step "Detecting environment"

OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Darwin) os_label="macOS" ;;
  Linux)  os_label="Linux" ;;
  *)      die "Unsupported OS: $OS (Primer supports macOS and Linux)" ;;
esac

ok "$os_label ($ARCH)"

# ---------------------------------------------------------------------------
# 2. Find Python 3.12+
# ---------------------------------------------------------------------------

step "Finding Python 3.12+"

PYTHON=""
for candidate in python3 python python3.13 python3.12; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
      PYTHON="$candidate"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  err "Python 3.12+ not found"
  case "$os_label" in
    macOS)
      info "Install via Homebrew: brew install python@3.13"
      info "Or download from: https://www.python.org/downloads/"
      ;;
    Linux)
      info "Install via your package manager:"
      info "  Ubuntu/Debian: sudo apt install python3.12"
      info "  Fedora:        sudo dnf install python3.12"
      info "  Arch:          sudo pacman -S python"
      info "Or use pyenv:    https://github.com/pyenv/pyenv"
      ;;
  esac
  exit 1
fi

py_version="$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")"
ok "Found $PYTHON ($py_version)"

# ---------------------------------------------------------------------------
# 3. Find installer (pipx or pip)
# ---------------------------------------------------------------------------

step "Finding package installer"

INSTALLER=""
PIPX=""
PIP=""

# Check for pipx
for candidate in pipx "${HOME}/.local/bin/pipx"; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PIPX="$candidate"
    INSTALLER="pipx"
    break
  fi
done

# Fall back to pip
if [ -z "$INSTALLER" ]; then
  for candidate in pip3 pip; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PIP="$candidate"
      INSTALLER="pip"
      break
    fi
  done
  # Try python -m pip
  if [ -z "$PIP" ] && "$PYTHON" -m pip --version >/dev/null 2>&1; then
    PIP="$PYTHON -m pip"
    INSTALLER="pip"
  fi
  # Last resort: ensurepip
  if [ -z "$PIP" ]; then
    info "Bootstrapping pip via ensurepip..."
    if "$PYTHON" -m ensurepip --upgrade >/dev/null 2>&1; then
      PIP="$PYTHON -m pip"
      INSTALLER="pip"
    fi
  fi
fi

if [ -z "$INSTALLER" ]; then
  die "No package installer found. Install pipx (recommended) or pip."
fi

ok "Using $INSTALLER"

# ---------------------------------------------------------------------------
# 4. Install primer
# ---------------------------------------------------------------------------

step "Installing primer"

pkg_spec="git+${PRIMER_REPO_URL}@${PRIMER_VERSION}"

if [ "$INSTALLER" = "pipx" ]; then
  if "$PIPX" list 2>/dev/null | grep -q "primer"; then
    info "primer already installed via pipx, upgrading..."
    "$PIPX" upgrade primer >/dev/null 2>&1 || "$PIPX" install "$pkg_spec" --force >/dev/null 2>&1
  else
    "$PIPX" install "$pkg_spec" >/dev/null 2>&1
  fi
else
  # Detect --break-system-packages requirement (PEP 668)
  pip_extra=""
  if $PIP install --help 2>/dev/null | grep -q "break-system-packages"; then
    pip_extra="--break-system-packages"
  fi
  # shellcheck disable=SC2086
  $PIP install --user $pip_extra "$pkg_spec" >/dev/null 2>&1
fi

# Verify primer on PATH
if ! command -v primer >/dev/null 2>&1; then
  # Try adding ~/.local/bin to PATH
  if [ -x "${HOME}/.local/bin/primer" ]; then
    export PATH="${HOME}/.local/bin:${PATH}"
    warn "Added ~/.local/bin to PATH (add to your shell profile for persistence)"
  else
    die "primer not found on PATH after install. Check your Python scripts directory."
  fi
fi

primer_version="$(primer --version 2>/dev/null || printf 'unknown')"
ok "primer installed ($primer_version)"

# ---------------------------------------------------------------------------
# 5. Initialize
# ---------------------------------------------------------------------------

step "Initializing Primer"

primer init 2>/dev/null || true

if [ -f "${PRIMER_HOME}/config.toml" ] && [ -f "${PRIMER_HOME}/primer.db" ]; then
  ok "Config and database ready"
else
  warn "Initialization may be incomplete — run 'primer init' manually"
fi

# ---------------------------------------------------------------------------
# 6. Download frontend
# ---------------------------------------------------------------------------

step "Downloading frontend"

if [ -n "${PRIMER_SKIP_FRONTEND:-}" ]; then
  info "Skipping frontend download (PRIMER_SKIP_FRONTEND set)"
else
  frontend_dir="${PRIMER_HOME}/frontend-dist"
  tarball_url="https://github.com/ccf/primer/releases/download/${PRIMER_VERSION}/frontend-dist.tar.gz"

  _fetch=""
  if command -v curl >/dev/null 2>&1; then
    _fetch="curl"
  elif command -v wget >/dev/null 2>&1; then
    _fetch="wget"
  fi

  downloaded=0
  if [ -n "$_fetch" ]; then
    mkdir -p "$frontend_dir"
    if [ "$_fetch" = "curl" ]; then
      if curl -fsSL "$tarball_url" 2>/dev/null | tar xz -C "$frontend_dir" 2>/dev/null; then
        downloaded=1
      fi
    else
      if wget -qO- "$tarball_url" 2>/dev/null | tar xz -C "$frontend_dir" 2>/dev/null; then
        downloaded=1
      fi
    fi
  fi

  if [ "$downloaded" = 1 ]; then
    export PRIMER_FRONTEND_DIST="$frontend_dir"
    ok "Frontend extracted to $frontend_dir"
  else
    warn "Frontend tarball not available (release may not exist yet)"
    info "The server will start without the dashboard UI"
    info "You can build it later: cd frontend && npm run build"
  fi
fi

# ---------------------------------------------------------------------------
# 7. Start server
# ---------------------------------------------------------------------------

step "Starting server"

# Export frontend dist path so the service config picks it up
if [ -n "${PRIMER_FRONTEND_DIST:-}" ]; then
  export PRIMER_FRONTEND_DIST
fi

if [ "$PRIMER_SERVER_PORT" != "8000" ]; then
  export PRIMER_SERVER_PORT
fi

primer server start 2>/dev/null || true

# Health check: poll /health for up to 30 seconds
server_url="http://localhost:${PRIMER_SERVER_PORT}"
healthy=0
attempts=0

_health_check() {
  if command -v curl >/dev/null 2>&1; then
    curl -sf "${server_url}/health" >/dev/null 2>&1
  else
    "$PYTHON" -c "
import urllib.request, sys
try:
    urllib.request.urlopen('${server_url}/health', timeout=2)
except Exception:
    sys.exit(1)
" 2>/dev/null
  fi
}

while [ "$attempts" -lt 15 ]; do
  if _health_check; then
    healthy=1
    break
  fi
  sleep 2
  attempts=$((attempts + 1))
done

if [ "$healthy" = 1 ]; then
  ok "Server running at $server_url"
else
  warn "Server not responding (may still be starting)"
  info "Check status: primer server status"
  info "View logs:    primer server logs"
fi

# ---------------------------------------------------------------------------
# 8. Register engineer
# ---------------------------------------------------------------------------

step "Registering engineer"

git_name="$(git config user.name 2>/dev/null || true)"
git_email="$(git config user.email 2>/dev/null || true)"

if [ -z "$git_name" ] || [ -z "$git_email" ]; then
  warn "Git user.name or user.email not configured — skipping registration"
  info "Set them and run: primer setup"
elif [ "$healthy" != 1 ]; then
  warn "Server not reachable — skipping registration"
  info "Start the server and run: primer setup"
else
  if primer setup 2>/dev/null; then
    ok "Engineer registered"
  else
    warn "Registration failed — run 'primer setup' manually"
  fi
fi

# ---------------------------------------------------------------------------
# 9. Install hook + MCP
# ---------------------------------------------------------------------------

step "Installing Claude Code integrations"

primer hook install 2>/dev/null || true
primer mcp install 2>/dev/null || true

ok "Hook and MCP server configured"

# ---------------------------------------------------------------------------
# 10. Verify + summary
# ---------------------------------------------------------------------------

step "Verifying installation"

printf "\n"
primer doctor 2>/dev/null || true

printf "\n"
printf "${_bold}${_white}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${_reset}\n"
printf "${_bold}${_green}  Primer is ready!${_reset}\n"
printf "${_bold}${_white}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${_reset}\n"
printf "\n"
printf "  ${_cyan}Dashboard:${_reset}    %s\n" "$server_url"
printf "  ${_cyan}Config:${_reset}       %s\n" "${PRIMER_HOME}/config.toml"
printf "  ${_cyan}Database:${_reset}     %s\n" "${PRIMER_HOME}/primer.db"
printf "  ${_cyan}Logs:${_reset}         %s\n" "${PRIMER_HOME}/logs/server.log"
printf "\n"
printf "  ${_white}MCP tools:${_reset}    sync, my_stats, team_overview, friction_report, recommendations\n"
printf "\n"
printf "  ${_white}Useful commands:${_reset}\n"
printf "    primer server status   — check server state\n"
printf "    primer server logs     — tail server logs\n"
printf "    primer doctor          — run diagnostics\n"
printf "    primer sync            — manually sync sessions\n"
printf "\n"
printf "  ${_white}To uninstall:${_reset}\n"
printf "    primer server stop\n"
printf "    primer hook uninstall\n"
printf "    primer mcp uninstall\n"
if [ "$INSTALLER" = "pipx" ]; then
  printf "    pipx uninstall primer\n"
else
  printf "    pip uninstall primer\n"
fi
printf "    rm -rf %s\n" "$PRIMER_HOME"
printf "\n"
