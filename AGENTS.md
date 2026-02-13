# Primer Agents

## tester

Run the test suite and analyze results.

### Instructions

1. Run `pytest -v --tb=short` and capture output
2. If any tests fail, read the failing test file and the source it tests to diagnose the issue
3. Run `pytest -v --cov=primer --cov-report=term-missing` to check coverage
4. Report: total passed/failed, coverage percentage, and any uncovered lines worth testing

### Key files

- `tests/conftest.py` — fixtures (engine, db_session, client, admin_headers, engineer_with_key)
- `tests/test_models.py`, `tests/test_ingest.py`, `tests/test_analytics.py`, `tests/test_hook_extractor.py`, `tests/test_mcp_reader.py`

## reviewer

Run lint and security checks, review code against project conventions.

### Instructions

1. Run `ruff check .` and `ruff format --check .` — report any violations
2. Run `bandit -r src/ -c pyproject.toml` — report any security findings
3. Check that new code follows patterns documented in `CLAUDE.md`:
   - SQLAlchemy 2.0 `Mapped`/`mapped_column` (not legacy `Column()`)
   - Pydantic v2 with `model_config` (not `class Config`)
   - Python 3.12+ union syntax (`str | None`)
   - Service-layer pattern (routers should not contain DB logic)
   - FastAPI dependency injection for auth
4. Verify that new endpoints or services have corresponding tests
5. Report findings grouped by category: lint, security, patterns, test coverage

## migrator

Handle Alembic database migration lifecycle.

### Instructions

1. When asked to create a migration:
   - Run `alembic revision --autogenerate -m "<description>"`
   - Read the generated migration file in `alembic/versions/`
   - Verify the upgrade and downgrade functions are correct
   - Check for any data-loss operations (column drops, type changes)
2. When asked to apply migrations:
   - Run `alembic upgrade head`
   - Verify with `alembic current`
3. When asked to test migrations:
   - Run `alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head`
   - Confirm round-trip succeeds without errors

### Key files

- `alembic/env.py` — migration config, imports models
- `alembic/versions/` — migration scripts
- `src/primer/common/models.py` — SQLAlchemy models (source of truth)
- `src/primer/common/database.py` — engine and session setup

## scaffolder

Generate boilerplate for new API resources.

### Instructions

When asked to scaffold a new resource (e.g., "scaffold projects"):

1. **Schema** — Add to `src/primer/common/schemas.py`:
   - `<Resource>Create(BaseModel)` with input fields
   - `<Resource>Response(BaseModel)` with `model_config = {"from_attributes": True}`

2. **Model** — Add to `src/primer/common/models.py`:
   - SQLAlchemy model with `Mapped`/`mapped_column`
   - UUID string PK, `func.now()` timestamps
   - Foreign keys and relationships as needed

3. **Service** — Create `src/primer/server/services/<resource>_service.py`:
   - CRUD functions accepting `db: Session` as first arg

4. **Router** — Create `src/primer/server/routers/<resource>.py`:
   - FastAPI `APIRouter` with `/api/v1/<resources>` prefix
   - Use `Depends(require_admin)` or `Depends(require_engineer)` for auth
   - Register in `src/primer/server/app.py`

5. **Tests** — Create `tests/test_<resource>.py`:
   - Use fixtures from `conftest.py`
   - Test CRUD operations and auth requirements

6. **Migration** — Run `alembic revision --autogenerate -m "add <resource>"`
