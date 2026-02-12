# Deployment Guide

## Local Development

The fastest way to get started:

```bash
# Install
pip install -e ".[dev]"

# Initialize SQLite database
alembic upgrade head

# Start server
uvicorn primer.server.app:app --reload

# Seed sample data (optional)
python scripts/seed_data.py
```

The server runs at `http://localhost:8000` with an SQLite database (`primer.db`).

## Docker Compose

For a production-like setup with PostgreSQL:

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: primer
      POSTGRES_USER: primer
      POSTGRES_PASSWORD: primer
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  api:
    build: .
    environment:
      PRIMER_DATABASE_URL: postgresql://primer:primer@db:5432/primer
      PRIMER_ADMIN_API_KEY: ${PRIMER_ADMIN_API_KEY:-change-me-in-production}
      PRIMER_SERVER_HOST: "0.0.0.0"
      PRIMER_SERVER_PORT: "8000"
    ports:
      - "8000:8000"
    depends_on:
      - db

volumes:
  pgdata:
```

```bash
docker compose up -d
```

## Production PostgreSQL

For connecting to an existing PostgreSQL instance:

```bash
export PRIMER_DATABASE_URL="postgresql://user:password@host:5432/primer"
export PRIMER_ADMIN_API_KEY="your-secure-admin-key"

# Run migrations
alembic upgrade head

# Start server
uvicorn primer.server.app:app --host 0.0.0.0 --port 8000
```

### Recommended PostgreSQL Settings

- Use a connection pooler (PgBouncer) for high-traffic deployments
- Enable `pg_stat_statements` for query monitoring
- Set `work_mem` appropriately for analytics queries
- Regular `VACUUM ANALYZE` on `sessions` and `session_facets` tables

## Environment Variables

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_DATABASE_URL` | `sqlite:///./primer.db` | Database connection string |
| `PRIMER_ADMIN_API_KEY` | `primer-admin-dev-key` | Admin API key for management endpoints |
| `PRIMER_SERVER_HOST` | `0.0.0.0` | Server bind host |
| `PRIMER_SERVER_PORT` | `8000` | Server bind port |
| `PRIMER_LOG_LEVEL` | `info` | Logging level |

### Hook & MCP Sidecar

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_SERVER_URL` | `http://localhost:8000` | URL of the Primer API server |
| `PRIMER_API_KEY` | — | Engineer API key for authentication |
| `PRIMER_ADMIN_API_KEY` | — | Admin key (MCP sidecar only, for analytics tools) |

## MCP Server Registration

Register the MCP sidecar so Claude Code can access your team's data:

### Claude Code Settings

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "primer": {
      "command": "python",
      "args": ["-m", "primer.mcp.server"],
      "env": {
        "PRIMER_SERVER_URL": "http://localhost:8000",
        "PRIMER_API_KEY": "primer_...",
        "PRIMER_ADMIN_API_KEY": "your-admin-key"
      }
    }
  }
}
```

### Verify

After registering, Claude Code will have access to 5 tools:
- `sync` — Upload local session history
- `my_stats` — Personal usage analytics
- `team_overview` — Team-level analytics
- `friction_report` — Friction point analysis
- `recommendations` — Actionable improvement suggestions

## Hook Installation

Install the SessionEnd hook so sessions are automatically uploaded:

```bash
# Set environment variables
export PRIMER_SERVER_URL=http://your-primer-server:8000
export PRIMER_API_KEY=primer_...

# Install the hook
python scripts/install_hook.py
```

This adds a hook to `~/.claude/settings.json` that runs after every Claude Code session ends. The hook:

1. Reads the session transcript (JSONL file)
2. Extracts metadata (messages, tokens, tools, models)
3. Loads facets if available
4. POSTs to `/api/v1/ingest/session`

### Verify Hook Installation

```bash
# Check that the hook is registered
cat ~/.claude/settings.json | python -m json.tool
```

Look for a `hooks` section with a `SessionEnd` entry.

## Scaling Notes

### Database

- **SQLite**: Good for single-user or small-team development (< 10 engineers)
- **PostgreSQL**: Required for production. Handles concurrent writes from multiple hooks
- Add indexes on `sessions.engineer_id` and `sessions.created_at` for query performance (already included in the migration)

### API Server

- Run behind a reverse proxy (nginx, Caddy) for TLS termination
- Use multiple uvicorn workers: `uvicorn primer.server.app:app --workers 4`
- Consider Gunicorn with uvicorn workers for process management:
  ```bash
  gunicorn primer.server.app:app -w 4 -k uvicorn.workers.UvicornWorker
  ```

### Hook

- The hook runs in-process after each Claude Code session (not a long-running service)
- If the server is unreachable, the hook fails silently — sessions can be synced later via the MCP `sync` tool
- Hook timeout is 10 seconds by default

### MCP Sidecar

- Runs locally alongside Claude Code (one per developer machine)
- Lightweight — makes HTTP calls to the API server on demand
- No persistent state; all data lives in the API server
