# Contributing to Primer

## Development Setup

### Prerequisites

- Python 3.12+
- pip or uv

### Installation

```bash
# Clone the repository
git clone <repo-url> && cd insights

# Install with dev dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install

# Initialize the database
alembic upgrade head
```

## Coding Standards

### Linting & Formatting

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check .          # Lint
ruff check . --fix    # Lint with auto-fix
ruff format .         # Format
ruff format --check . # Check formatting
```

Configuration is in `pyproject.toml`. Key settings:
- Line length: 100
- Target: Python 3.12
- Rules: E, W, F, I, N, UP, B, A, S, T20, SIM, TCH, RUF

### Security

We use [bandit](https://bandit.readthedocs.io/) for security scanning:

```bash
bandit -r src/ -c pyproject.toml
```

### SQLAlchemy Patterns

Use SQLAlchemy 2.0 declarative style:

```python
class MyModel(Base):
    __tablename__ = "my_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

### Pydantic Patterns

Use Pydantic v2 with `model_config`:

```python
class MyResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

### pydantic-settings

All configuration uses `pydantic-settings` with the `PRIMER_` env prefix. See `src/primer/common/config.py`.

### FastAPI Dependency Injection

Use `Depends()` for auth and DB sessions:

```python
@router.get("/api/v1/resource")
def list_resources(
    admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ...
```

## Project Structure

```
src/primer/
├── common/          # Shared: models, schemas, config, database
├── server/
│   ├── app.py       # FastAPI app factory
│   ├── deps.py      # Auth dependencies
│   ├── routers/     # API endpoints
│   └── services/    # Business logic
├── hook/            # Claude Code SessionEnd hook
└── mcp/             # MCP sidecar server
tests/               # pytest test suite
scripts/             # Dev utilities
alembic/             # Database migrations
```

## Testing

### Running Tests

```bash
pytest -v                                          # Run all tests
pytest -v --cov=primer --cov-report=term-missing   # With coverage
pytest tests/test_ingest.py -v                     # Single file
pytest tests/test_analytics.py::test_overview -v   # Single test
```

### Test Patterns

- Use the `client` fixture from `conftest.py` for API tests (FastAPI `TestClient`)
- Use `db_session` for direct database tests (auto-rollback per test)
- Use `admin_headers` for endpoints requiring admin auth
- Use `engineer_with_key` to get an engineer and raw API key for ingest tests
- Tests run against SQLite in-memory — no external database required

```python
def test_create_team(client, admin_headers):
    resp = client.post("/api/v1/teams", json={"name": "Backend"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Backend"
```

## PR Process

1. Branch from `develop` (or `main` if no develop branch exists)
2. Make your changes following the coding standards above
3. Add or update tests for any new functionality
4. Ensure all checks pass:
   ```bash
   ruff check .
   ruff format --check .
   bandit -r src/ -c pyproject.toml
   pytest -v
   ```
5. Open a PR with a clear description of what changed and why
6. Update documentation if adding endpoints, models, or configuration

## Database Migrations

### Creating a Migration

```bash
# After modifying models in src/primer/common/models.py
alembic revision --autogenerate -m "add projects table"
```

### Reviewing a Migration

Always review the generated file in `alembic/versions/`:
- Verify `upgrade()` creates the correct tables/columns
- Verify `downgrade()` reverses everything cleanly
- Check for data-loss operations (column drops, type changes)

### Applying Migrations

```bash
alembic upgrade head      # Apply all pending migrations
alembic downgrade -1      # Roll back one migration
alembic current           # Show current revision
alembic history           # Show migration history
```
