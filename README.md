<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="brand/logo-wordmark-light.svg">
    <source media="(prefers-color-scheme: light)" srcset="brand/logo-wordmark.svg">
    <img src="brand/logo-wordmark.svg" alt="Primer" width="280">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/ccf/primer/actions/workflows/ci.yml"><img src="https://github.com/ccf/primer/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <img src="https://img.shields.io/badge/coverage-92%25-brightgreen.svg" alt="Coverage: 92%">
  <img src="https://img.shields.io/badge/security-bandit-brightgreen.svg" alt="Security: Bandit">
  <img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/node-20+-green.svg" alt="Node 20+">
</p>

<p align="center">Aggregate Claude Code usage insights across an engineering organization.</p>

---

Primer is a self-hosted analytics platform with four components:

1. **REST API Server** — FastAPI service that stores and analyzes session data
2. **Frontend Dashboard** — React + Tailwind CSS dashboard with cost analysis, dark mode, and date filtering
3. **Claude Code Hook** — SessionEnd hook that automatically uploads transcripts after each session
4. **MCP Sidecar** — Model Context Protocol server that lets Claude query your team's usage patterns

## Quickstart

### Local Development

```bash
# Clone and install
git clone <repo-url> && cd insights
pip install -e ".[dev]"

# Initialize the database
alembic upgrade head

# Start the API server
uvicorn primer.server.app:app --reload

# (Optional) Seed sample data
python scripts/seed_data.py
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev        # Vite dev server on :5173
npm run build      # Production build
npm run lint       # ESLint
npx tsc -b --noEmit  # Type check
```

### Docker Compose

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: primer
      POSTGRES_USER: primer
      POSTGRES_PASSWORD: primer
    ports:
      - "5432:5432"

  api:
    build: .
    environment:
      PRIMER_DATABASE_URL: postgresql://primer:primer@db:5432/primer
      PRIMER_ADMIN_API_KEY: your-admin-key-here
    ports:
      - "8000:8000"
    depends_on:
      - db
```

## API Reference

All management and analytics endpoints require authentication. Ingest endpoints authenticate via engineer API keys. Analytics endpoints support optional `start_date` and `end_date` query parameters for date range filtering.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Health check |
| POST | `/api/v1/teams` | Admin | Create a team |
| GET | `/api/v1/teams` | Admin | List all teams |
| POST | `/api/v1/engineers` | Admin | Create an engineer (returns API key) |
| GET | `/api/v1/engineers` | Admin | List all engineers |
| GET | `/api/v1/engineers/{id}/sessions` | Admin | List sessions for an engineer |
| POST | `/api/v1/ingest/session` | API Key | Ingest a single session |
| POST | `/api/v1/ingest/bulk` | API Key | Ingest multiple sessions |
| POST | `/api/v1/ingest/facets/{session_id}` | API Key | Upsert session facets |
| GET | `/api/v1/sessions` | Admin | List sessions (with filters) |
| GET | `/api/v1/sessions/{session_id}` | Admin | Get session details |
| GET | `/api/v1/analytics/overview` | JWT/Admin | Aggregate usage stats (includes estimated cost) |
| GET | `/api/v1/analytics/daily` | JWT/Admin | Daily session/message/tool activity |
| GET | `/api/v1/analytics/friction` | JWT/Admin | Friction point report |
| GET | `/api/v1/analytics/tools` | JWT/Admin | Tool usage rankings |
| GET | `/api/v1/analytics/models` | JWT/Admin | Model usage rankings |
| GET | `/api/v1/analytics/costs` | JWT/Admin | Cost breakdown by model + daily cost trend |
| GET | `/api/v1/analytics/recommendations` | JWT/Admin | Actionable recommendations |
| GET | `/api/v1/auth/github/login` | None | Initiate GitHub OAuth login |
| GET | `/api/v1/auth/github/callback` | None | GitHub OAuth callback |
| GET | `/api/v1/auth/me` | JWT | Get current user info |
| POST | `/api/v1/auth/logout` | JWT | Logout (revoke refresh token) |

See [docs/api.md](docs/api.md) for full request/response schemas and examples.

## Frontend Features

- **Cost Analysis** — Estimated spend per model with daily cost trend charts
- **Date Range Picker** — Filter all analytics by 7d / 30d / 90d / 1y
- **Dark Mode** — Toggle between light, dark, and system themes (persisted in localStorage)
- **Session Deep Links** — Copy-to-clipboard button on session detail pages
- **Keyboard Navigation** — Arrow keys to navigate session tables, Enter to open

## MCP Sidecar Setup

The MCP server lets Claude access your team's usage data during conversations.

```bash
# Required environment variables
export PRIMER_SERVER_URL=http://localhost:8000
export PRIMER_API_KEY=primer_...        # Engineer API key
export PRIMER_ADMIN_API_KEY=your-admin-key

# Run the MCP server
python -m primer.mcp.server
```

### Available Tools

| Tool | Description |
|------|-------------|
| `sync` | Upload local session history to the Primer server |
| `my_stats` | Get your personal usage stats (sessions, tokens, tools, outcomes) |
| `team_overview` | Get team-level analytics overview |
| `friction_report` | Get friction points your team encounters |
| `recommendations` | Get actionable recommendations based on usage patterns |

## Hook Installation

The SessionEnd hook automatically uploads session data after each Claude Code session.

```bash
# Set required environment variables
export PRIMER_SERVER_URL=http://localhost:8000
export PRIMER_API_KEY=primer_...

# Install the hook into Claude Code settings
python scripts/install_hook.py
```

This adds a `SessionEnd` hook to `~/.claude/settings.json` that runs `python -m primer.hook.session_end` after every session.

## Configuration

All settings use the `PRIMER_` environment variable prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_DATABASE_URL` | `sqlite:///./primer.db` | Database connection string |
| `PRIMER_ADMIN_API_KEY` | `primer-admin-dev-key` | Admin API key for management endpoints |
| `PRIMER_SERVER_HOST` | `0.0.0.0` | Server bind host |
| `PRIMER_SERVER_PORT` | `8000` | Server bind port |
| `PRIMER_LOG_LEVEL` | `info` | Logging level |
| `PRIMER_GITHUB_CLIENT_ID` | — | GitHub OAuth app client ID |
| `PRIMER_GITHUB_CLIENT_SECRET` | — | GitHub OAuth app client secret |
| `PRIMER_JWT_SECRET_KEY` | — | Secret key for JWT token signing |

For the hook and MCP sidecar:

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_SERVER_URL` | `http://localhost:8000` | URL of the Primer API server |
| `PRIMER_API_KEY` | — | Engineer API key for authentication |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development guide.

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Lint and format
ruff check .
ruff format .

# Security scan
bandit -r src/ -c pyproject.toml

# Pre-commit hooks
pre-commit install
```

## About the Name

The name comes from Neal Stephenson's *The Diamond Age*, where the Young Lady's Illustrated Primer is an adaptive, AI-driven book that observes its reader, understands her context, and transforms complexity into personalized guidance. Primer brings that same principle to engineering organizations — turning raw AI usage data into the understanding teams need to work effectively.

## License

[MIT](LICENSE)
