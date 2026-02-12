# Primer

Aggregate Claude Code usage insights across an engineering organization.

## Key Paths

| Path | Purpose |
|------|---------|
| `src/primer/common/` | Shared models, schemas, config, database setup |
| `src/primer/server/` | FastAPI application, routers, services |
| `src/primer/server/routers/` | API endpoint definitions (health, teams, engineers, sessions, ingest, analytics) |
| `src/primer/server/services/` | Business logic (ingest, analytics, synthesis) |
| `src/primer/hook/` | Claude Code SessionEnd hook (extractor, installer) |
| `src/primer/mcp/` | MCP sidecar server (5 tools: sync, my_stats, team_overview, friction_report, recommendations) |
| `tests/` | pytest test suite (30 tests) |
| `scripts/` | Dev utilities (seed_data.py, install_hook.py) |
| `alembic/` | Database migrations |

## Commands

```bash
# Tests
pytest -v
pytest -v --cov=primer --cov-report=term-missing

# Linting & formatting
ruff check .
ruff check . --fix
ruff format .
ruff format --check .

# Security scan
bandit -r src/ -c pyproject.toml

# Run server
uvicorn primer.server.app:app --reload

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Seed dev data
python scripts/seed_data.py

# Install Claude Code hook
python scripts/install_hook.py

# Run MCP server
python -m primer.mcp.server
```

## Architecture Patterns

- **Config**: `pydantic-settings` with `PRIMER_` env prefix (`src/primer/common/config.py`)
- **ORM**: SQLAlchemy 2.0 declarative with `Mapped`/`mapped_column` (`src/primer/common/models.py`)
- **API**: FastAPI with dependency injection for auth and DB sessions
- **Auth**: bcrypt-hashed API keys for engineers, plain admin key via header
- **Services**: Service-layer pattern — routers call services, services own DB logic
- **MCP**: `FastMCP` server with `httpx` calls back to the REST API

## Conventions

- Python 3.12+ union syntax (`str | None` not `Optional[str]`)
- Line length 100 (ruff)
- UUID string primary keys (`String(36)`, generated via `uuid.uuid4()`)
- Server-side timestamps via `func.now()`
- All API routes under `/api/v1/` prefix
- Pydantic v2 with `model_config = {"from_attributes": True}` for ORM serialization
- Tests use SQLite in-memory with transaction rollback per test

## Common Tasks

### Adding a new endpoint

1. Create or edit a router in `src/primer/server/routers/`
2. Add service functions in `src/primer/server/services/` if needed
3. Add Pydantic schemas to `src/primer/common/schemas.py`
4. Register router in `src/primer/server/app.py` if new file
5. Add tests in `tests/`

### Adding a new model

1. Add SQLAlchemy model to `src/primer/common/models.py`
2. Import in `alembic/env.py` if not already covered
3. Run `alembic revision --autogenerate -m "add <table>"`
4. Review and apply: `alembic upgrade head`

### Adding an MCP tool

1. Add tool function in `src/primer/mcp/tools.py`
2. Register with `@mcp.tool()` decorator in `src/primer/mcp/server.py`
3. Add tests in `tests/`
