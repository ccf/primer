# Installation Simplification Plan

## Context
Primer currently requires ~8 manual steps across Python, Node.js, and shell. This plan introduces a `primer` CLI, a `curl | sh` installer for personal use, and enhanced Docker/Helm for enterprise.

## Current Pain Points
- ~~No single entry point or CLI — everything is `python -m`, `python scripts/`, or raw curl~~
- ~~No `[project.scripts]` in pyproject.toml~~
- ~~No daemonization (server runs in foreground terminal)~~
- ~~Frontend requires Node.js + separate dev server~~
- ~~Docker Compose is minimal (no frontend, no health checks)~~
- ~~No Helm chart~~
- ~~MCP registration and API key distribution are manual~~

## 1. Unified `primer` CLI ✅

**Implemented** in `src/primer/cli/`. Entry point: `primer = "primer.cli.main:cli"` in pyproject.toml.

### Command Tree
```
primer init                    # Create ~/.primer/, run migrations, generate config
primer setup                   # Create identity (name, email from git config)
primer server start [--fg]     # Start server (background default, foreground for Docker)
primer server stop             # Stop background server
primer server status           # Show running state, port, uptime
primer server logs             # Tail server logs
primer hook install            # Install SessionEnd hook in Claude Code
primer hook uninstall          # Remove hook
primer hook status             # Check hook configuration
primer mcp install             # Register MCP sidecar
primer mcp uninstall           # Remove MCP registration
primer mcp serve               # Run MCP server (used by the registration)
primer sync                    # Sync local sessions to server
primer doctor                  # Diagnose issues (connectivity, hook, MCP)
primer --version               # Show version
primer configure get KEY       # Get a config value
primer configure set KEY VAL   # Set a config value
primer configure list          # Show all config values
```

### Key files
- `src/primer/cli/main.py` — Click group, registers all commands
- `src/primer/cli/config.py` — Config management (load_config_into_env, read/write config.toml)
- `src/primer/cli/server_manager.py` — Platform-specific process management (launchd/systemd/pidfile)
- `src/primer/cli/console.py` — Colored output helpers
- `src/primer/cli/commands/` — Individual command modules
- `src/primer/hook/installer.py` — Hook install/uninstall logic (refactored from scripts/)

### Config Precedence
1. CLI flags → 2. Environment variables → 3. `~/.primer/config.toml` → 4. PrimerSettings defaults

### Data Directory
```
~/.primer/
  config.toml          # API keys, server URL, port
  primer.db            # SQLite database
  logs/server.log      # Server output
  server.pid           # PID file for pidfile fallback
```

### Server Management
- macOS: launchd plist at `~/Library/LaunchAgents/com.primer.server.plist`
- Linux: systemd user unit at `~/.config/systemd/user/primer-server.service`
- Fallback: Popen + PID file

## 2. Personal Use: `curl | sh` Installer ✅

**Implemented**: POSIX sh installer at `website/public/install.sh`, served at `https://ccf.github.io/primer/install.sh`.

```bash
curl -fsSL https://ccf.github.io/primer/install.sh | sh
```

### Configurable env vars
- `PRIMER_REPO_URL` — GitHub repo URL for forks
- `PRIMER_VERSION` — git tag/branch (default: `main`)
- `PRIMER_NO_COLOR` — disable colored output
- `PRIMER_SKIP_FRONTEND` — skip frontend download
- `PRIMER_SERVER_PORT` — override port (default: 8000)

### 10-step sequence
1. **Detect environment** — OS (macOS/Linux) + arch via `uname`
2. **Find Python 3.12+** — tries `python3`, `python`, `python3.13`, `python3.12` with version check
3. **Find installer** — prefers pipx, falls back to pip with ensurepip bootstrap
4. **Install primer** — `pipx install` or `pip install --user` (idempotent via upgrade fallback)
5. **Initialize** — `primer init` (creates `~/.primer/`, config.toml, runs migrations)
6. **Download frontend** — tarball from GitHub Releases → `~/.primer/frontend-dist/`; graceful skip
7. **Start server** — `primer server start` with `/health` polling (30s timeout, curl/urllib fallback)
8. **Register engineer** — pre-checks git config to avoid interactive prompts; `primer setup`
9. **Install hook + MCP** — `primer hook install` + `primer mcp install` (idempotent)
10. **Verify + summary** — `primer doctor`, prints server URL, config paths, MCP tools, uninstall steps

### Key design decisions
- POSIX sh (`#!/bin/sh`) for maximum compatibility
- `printf` (not `echo`) for portable escape handling
- Colors gated on TTY check + `NO_COLOR`/`PRIMER_NO_COLOR`
- Frontend downloaded before server start so `PRIMER_FRONTEND_DIST` is set in service config
- Non-critical steps use `|| true` so `set -eu` doesn't abort
- `--break-system-packages` auto-detected for PEP 668 systems

## 3. Enterprise: Docker Compose ✅

**Implemented**: Unified multi-stage `Dockerfile` (frontend build + Python runtime), rewritten `docker-compose.yml` with PostgreSQL health checks, health probes, `PRIMER_FRONTEND_DIST` env var support, and `.env.docker.example` template. Single `make up` to start everything.

Key files:
- `Dockerfile` — unified multi-stage build (frontend + backend in one image)
- `docker-compose.yml` — postgres + primer services with health checks
- `.env.docker.example` — minimal env template
- `.dockerignore` — optimized build context
- `Makefile` — `make up`, `make down`, `make dev`, etc.

## 4. Enterprise: Kubernetes / Helm ✅

**Implemented**: Production-ready Helm chart at `deploy/helm/primer/` with separate server/frontend deployments, HPA, PDB, Ingress, ConfigMap/Secret, and pre-install/pre-upgrade migration Job. Separate `Dockerfile.frontend` (nginx) for Kubernetes deployments.

Key files:
- `deploy/helm/primer/` — full Helm chart (Chart.yaml, values.yaml, 14 templates)
- `Dockerfile.frontend` — nginx-based frontend for K8s
- `deploy/nginx/default.conf.template` — nginx config with API proxy + SPA fallback

### Key values.yaml
- Server: 2 replicas, autoscaling 2-10 at 70% CPU
- Frontend: 2 replicas, autoscaling 2-5 at 70% CPU
- PodDisruptionBudgets for both components
- External PostgreSQL recommended
- Ingress with TLS support
- Migration job runs before server starts

## 5. Documentation

Getting-started guide, deployment guide, and CLI reference for the docs website.

## Implementation Sequence

| Phase | Status | Work |
|-------|--------|------|
| **1** | ✅ | `primer` CLI — init, setup, server, hook, mcp, sync, doctor, configure |
| **2** | ✅ | `install.sh` — OS detection, pipx/pip install, auto-setup |
| **3** | ✅ | Docker — unified Dockerfile, compose health checks, Makefile |
| **4** | ✅ | Helm chart — deployments, ingress, migration job, HPA, PDB |
| **5** |    | Documentation — getting-started, deployment, CLI reference |

## Risks
- PyPI publication needed for `pipx install primer`
- Pre-built frontend requires CI release pipeline
- Port 8000 conflicts — `primer init` could auto-detect free port
- Python 3.12+ requirement — installer should document pyenv/brew
- Database migrations on upgrade — `primer server start` should auto-migrate
