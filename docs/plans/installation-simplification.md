# Installation Simplification Plan

## Context
Primer currently requires ~8 manual steps across Python, Node.js, and shell. This plan introduces a `primer` CLI, a `curl | sh` installer for personal use, and enhanced Docker/Helm for enterprise.

## Current Pain Points
- No single entry point or CLI — everything is `python -m`, `python scripts/`, or raw curl
- No `[project.scripts]` in pyproject.toml
- No daemonization (server runs in foreground terminal)
- Frontend requires Node.js + separate dev server
- Docker Compose is minimal (no frontend, no health checks)
- No Helm chart
- MCP registration and API key distribution are manual

## 1. Unified `primer` CLI

### Entry Point
```toml
# pyproject.toml
[project.scripts]
primer = "primer.cli:main"
```

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
primer version                 # Show version
primer configure [set|get]     # View/edit config
```

### Config Precedence
1. CLI flags → 2. Environment variables → 3. `~/.primer/config.toml` → 4. PrimerSettings defaults

### Data Directory
```
~/.primer/
  config.toml          # API keys, server URL, port
  primer.db            # SQLite database
  frontend-dist/       # Pre-built React app
  logs/server.log      # Server output
  server.pid           # PID file for background server
```

### Server Management
- macOS: launchd plist at `~/Library/LaunchAgents/dev.primer.server.plist`
- Linux: systemd user unit at `~/.config/systemd/user/primer.service`
- Fallback: `nohup` + PID file

## 2. Personal Use: `curl | sh` Installer

```bash
curl -fsSL https://primer.dev/install.sh | sh
```

### Steps
1. **Detect environment**: OS, arch, Python 3.12+, pipx
2. **Install package**: `pipx install primer` (or `pip install --user`)
3. **Initialize**: `primer init` — creates ~/.primer/, runs Alembic, generates keys
4. **Setup identity**: `primer setup --auto` — reads name/email from `git config`
5. **Install hook**: `primer hook install` — writes to `~/.claude/settings.json`
6. **Register MCP**: `primer mcp install` — adds MCP sidecar entry
7. **Download frontend**: Pre-built tarball from GitHub release → `~/.primer/frontend-dist/`
8. **Start server**: Create launchd plist or systemd unit, start service
9. **Verify**: Health check + print summary with URLs and key location

### Config File
```toml
[server]
host = "127.0.0.1"
port = 8000
database_url = "sqlite:///~/.primer/primer.db"
admin_api_key = "primer-admin-xxxxxxxx"

[identity]
api_key = "primer_xxxxxxxx"
name = "Your Name"
email = "you@example.com"
```

## 3. Enterprise: Docker Compose

### New `Dockerfile.frontend`
Multi-stage: `node:20-alpine` build → `nginx:alpine` serve

### Enhanced `docker-compose.yml`
- PostgreSQL with health check
- Server with health check + required env var validation (`${VAR:?message}`)
- Frontend container (nginx)
- `.env.docker.example` template

### Enterprise Setup Script
```bash
curl -fsSL https://primer.dev/enterprise-setup.sh | sh
```
Checks Docker, prompts for PostgreSQL, generates keys, writes .env, runs `docker compose up -d`.

## 4. Enterprise: Kubernetes / Helm

### Chart Structure
```
deploy/helm/primer/
  Chart.yaml, values.yaml
  templates/
    deployment-server.yaml    # With HPA
    deployment-frontend.yaml
    service-*.yaml
    ingress.yaml              # With TLS
    configmap.yaml, secret.yaml
    migration-job.yaml        # Helm pre-install/pre-upgrade hook
    hpa.yaml, pdb.yaml
```

### Key values.yaml
- Server: 2 replicas, autoscaling 2-10 at 70% CPU
- External PostgreSQL recommended (with `existingSecret` support)
- Ingress with TLS
- Migration job runs before server starts

## 5. Code Changes Required

### `pyproject.toml`
- Add `[project.scripts]` entry
- Use `tomllib` (stdlib in 3.12+) for config parsing

### `src/primer/common/config.py`
- Read `~/.primer/config.toml` as fallback
- Add `data_dir` property

### `src/primer/server/app.py`
- Check `~/.primer/frontend-dist/` as fallback for static files
- Log configuration on startup

### `scripts/install_hook.py`
- Refactor core logic into `src/primer/hook/installer.py`
- Script becomes thin wrapper

### `Dockerfile.server`
- Add `HEALTHCHECK`
- Use `primer server start --fg` as entry point

## Implementation Sequence

| Phase | Work |
|---|---|
| **1** | `primer` CLI core — init, setup, server, hook, mcp, sync, doctor |
| **2** | `install.sh` script — OS detection, pipx install, launchd/systemd |
| **3** | Docker improvements — frontend Dockerfile, compose health checks, .env |
| **4** | Helm chart — deployments, ingress, migration job, HPA |
| **5** | Documentation — getting-started, deployment, CLI reference |

## Risks
- PyPI publication needed for `pipx install primer`
- Pre-built frontend requires CI release pipeline
- Port 8000 conflicts — auto-detect free port
- Python 3.12+ requirement — document pyenv/brew install
- Database migrations on upgrade — `primer server start` should auto-migrate
