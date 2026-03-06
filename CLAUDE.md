# Primer

Aggregate AI coding agent usage insights across an engineering organization.

## Key Paths

### Backend

| Path | Purpose |
|------|---------|
| `src/primer/common/` | Shared models, schemas, config, database setup |
| `src/primer/common/models.py` | SQLAlchemy 2.0 models (Team, Engineer, Session, ModelUsage, ToolUsage, SessionFacets, Alert, AlertConfig, AuditLog, Budget, PullRequest, ReviewFinding, NarrativeCache, etc.) |
| `src/primer/common/schemas.py` | 100+ Pydantic v2 DTOs for all API request/response types |
| `src/primer/common/pricing.py` | Model pricing config + cost estimation (longest-prefix match) |
| `src/primer/common/config.py` | `pydantic-settings` with `PRIMER_` env prefix |
| `src/primer/common/database.py` | SQLAlchemy engine + session factory |
| `src/primer/server/app.py` | FastAPI app with 14 routers, CORS, rate limiting, lifespan hooks |
| `src/primer/server/deps.py` | Auth dependency injection (`AuthContext` with role/team_id/engineer_id) |
| `src/primer/server/middleware.py` | Rate limiting via slowapi (key function, limiter instance) |
| `src/primer/server/routers/` | API endpoint definitions (see Routers table below) |
| `src/primer/server/services/` | Business logic (see Services table below) |
| `src/primer/hook/` | SessionEnd hook: multi-agent extractor registry (Claude Code, Codex CLI, Gemini CLI) |
| `src/primer/mcp/` | MCP sidecar server (5 tools: sync, my_stats, team_overview, friction_report, recommendations) |
| `alembic/` | Database migrations |
| `tests/` | pytest test suite (~50 files, 491+ tests) |
| `scripts/` | Dev utilities: seed_data.py, install_hook.py, verify_github.py, provision_user.py |

### Frontend

| Path | Purpose |
|------|---------|
| `frontend/src/pages/` | Route pages (dashboard, sessions, engineers, engineer-profile, teams, team-detail, maturity, explorer, narrative, finops, admin, login, profile) |
| `frontend/src/components/dashboard-v2/` | Main dashboard tabs (overview, sessions, engineers, projects, quality, insights) |
| `frontend/src/components/finops/` | FinOps tabs (overview, cache, modeling, forecast, budgets) |
| `frontend/src/components/engineer-profile/` | Engineer profile views (trajectory, strengths, friction, quality, narrative) |
| `frontend/src/components/session-insights/` | Session analytics charts (health, cache, satisfaction, goals, friction) |
| `frontend/src/components/sessions/` | Session browser, search, filters, transcript viewer, cost/tool charts |
| `frontend/src/components/maturity/` | AI maturity scoring (leverage, tool categories, project readiness) |
| `frontend/src/components/growth/` | Onboarding acceleration (cohorts, ramp-up, learning paths, patterns) |
| `frontend/src/components/quality/` | Code quality metrics, Claude PR comparison, review findings, GitHub integration |
| `frontend/src/components/explorer/` | Conversational data explorer (floating chat, SSE streaming) |
| `frontend/src/components/narrative/` | AI-generated narrative insights |
| `frontend/src/components/admin/` | Admin UI tabs (alerts, audit log, engineers, teams, notifications, system) |
| `frontend/src/components/layout/` | App shell, sidebar, header, date-range-picker, alert bell |
| `frontend/src/components/shared/` | Reusable: empty-state, loading-skeleton, login-gate, page-header |
| `frontend/src/components/ui/` | Primitives: button, card, badge, skeleton, separator, page-tabs |
| `frontend/src/components/charts/` | Shared chart tooltip |
| `frontend/src/hooks/` | TanStack Query hooks (use-api-queries, use-api-mutations, use-explorer-stream, use-keyboard-navigation) |
| `frontend/src/lib/` | Utilities: api client, auth-context, theme-context, chart-colors, csv-export, pdf-export, role-utils, utils |
| `frontend/src/types/api.ts` | TypeScript interfaces for all API responses (1000+ lines) |

### Routers

| Router | Endpoints |
|--------|-----------|
| `health.py` | `GET /health` |
| `auth.py` | GitHub OAuth login/callback, JWT token exchange, refresh, logout |
| `teams.py` | Team CRUD |
| `engineers.py` | Engineer CRUD, API key generation/rotation, profile |
| `sessions.py` | Session list/detail with filters (engineer, team, project, outcome, model, date range) |
| `ingest.py` | Session ingestion from hooks (single + bulk) |
| `analytics.py` | Overview stats, friction, benchmarks, cost analysis, tool adoption, daily stats, insights, maturity, quality, review findings, explorer, narrative |
| `alerts.py` | Alert list/detail, acknowledge/dismiss, anomaly detection trigger |
| `alert_configs.py` | Alert threshold CRUD per team |
| `notifications.py` | Slack webhook config and test |
| `webhooks.py` | GitHub webhook receiver for PR/commit tracking |
| `explorer.py` | SSE streaming conversational data explorer |
| `admin.py` | System stats, audit logs, engineer/team/alert management |
| `finops.py` | Cache analytics, cost modeling, forecasting, budget CRUD |

### Services

| Service | Purpose |
|---------|---------|
| `ingest_service.py` | Session ingestion, repository upsert, event tracking |
| `auth_service.py` | GitHub OAuth flow, JWT generation, engineer lookup |
| `analytics_service.py` | Overview stats, friction reports, benchmarks, cost analysis, tool adoption, heatmaps, daily stats |
| `insights_service.py` | Productivity metrics, bottleneck detection, pattern sharing, learning paths, skill inventory, config optimization |
| `session_insights_service.py` | Session-level insights: end reasons, satisfaction, friction clusters, cache efficiency, health scoring, goals |
| `engineer_profile_service.py` | Engineer trajectory, strengths, friction, quality aggregation |
| `narrative_service.py` | Claude API-powered narrative insights with caching and auto-refresh |
| `synthesis_service.py` | AI synthesis of recommendations |
| `facet_extraction_service.py` | LLM-powered session facet extraction (goal, friction, satisfaction) |
| `explorer_service.py` | Conversational data explorer (tool-use chat with Anthropic API) |
| `quality_service.py` | Code quality metrics, Claude PR comparison, review findings aggregation, GitHub integration |
| `maturity_service.py` | Tool leverage scoring, AI readiness per project |
| `github_service.py` | GitHub PR/commit fetching, PR comment fetching, AI readiness detection |
| `review_finding_service.py` | Extensible parser registry for automated review findings (BugBot, etc.) |
| `alerting_service.py` | Anomaly detection (friction spikes, cost spikes, success rate drops) |
| `alert_config_service.py` | Alert threshold CRUD and resolution (team > global > defaults) |
| `audit_service.py` | Audit log recording for admin actions |
| `slack_service.py` | Slack webhook posting |
| `finops_service.py` | Cache analytics, cost modeling (API vs subscription), forecasting (linear regression), budget tracking |

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

# Frontend
cd frontend && npm run dev          # Dev server
cd frontend && npm run build        # Production build
cd frontend && npm run lint         # ESLint
cd frontend && npx tsc -b --noEmit  # Type check
```

## Architecture Patterns

- **Config**: `pydantic-settings` with `PRIMER_` env prefix; keys for DB, auth, GitHub OAuth/App, CORS, Anthropic API, Slack, rate limits, productivity params
- **ORM**: SQLAlchemy 2.0 declarative with `Mapped`/`mapped_column` (`src/primer/common/models.py`)
- **API**: FastAPI with dependency injection for auth (`AuthContext`) and DB sessions
- **Auth**: bcrypt-hashed API keys for engineers, GitHub OAuth + JWT (access + refresh) for dashboard, plain admin key via `x-admin-key` header
- **Services**: Service-layer pattern — routers call services, services own DB logic
- **MCP**: `FastMCP` server with `httpx` calls back to the REST API
- **Hook**: Multi-agent extractor registry (Claude Code, Codex CLI, Gemini CLI) with SessionEnd hook
- **Pricing**: `src/primer/common/pricing.py` — longest-prefix match on model name, falls back to Sonnet 4 pricing
- **Theming**: CSS custom properties in `index.css`, `.dark` class toggle, localStorage-persisted preference
- **Rate Limiting**: slowapi middleware with per-route limits; key function uses API key prefix or client IP
- **Alert Thresholds**: `AlertConfig` model with team > global > config defaults priority chain
- **Audit Trail**: `AuditLog` model records admin mutations with actor, action, resource, details, IP
- **Narrative Cache**: `NarrativeCache` model with TTL-based expiry and optional auto-refresh via lifespan task
- **Facet Extraction**: LLM-powered (Anthropic API) session classification into goals, friction, satisfaction
- **Explorer**: SSE-streamed conversational analytics using Anthropic tool-use API
- **GitHub Integration**: App-based PR/commit fetching, AI readiness scoring (CLAUDE.md, AGENTS.md detection)
- **Review Findings**: Extensible parser registry (`@register_parser` decorator) for automated review bot comments (BugBot); fetches issue comments, PR review comments, and review bodies; upsert with unique constraint deduplication
- **FinOps**: Cache savings via per-model pricing deltas, cost modeling (API vs subscription tiers), linear regression forecasting, budget burn-rate tracking

## Conventions

- Python 3.12+ union syntax (`str | None` not `Optional[str]`)
- Line length 100 (ruff)
- UUID string primary keys (`String(36)`, generated via `uuid.uuid4()`)
- Server-side timestamps via `func.now()`
- All API routes under `/api/v1/` prefix
- All analytics endpoints accept optional `start_date`/`end_date` query params
- Pydantic v2 with `model_config = {"from_attributes": True}` for ORM serialization
- Tests use SQLite in-memory with transaction rollback per test
- Frontend uses TanStack Query with `buildParams()` helper for query string construction
- Frontend chart colors via `CHART_COLORS` / `CHART_PALETTE` from `frontend/src/lib/chart-colors.ts`
- Frontend formatting utilities: `formatCost`, `formatPercent`, `formatTokens`, `formatDuration` from `frontend/src/lib/utils.ts`
- CSV and PDF export utilities in `frontend/src/lib/csv-export.ts` and `frontend/src/lib/pdf-export.ts`

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

### Adding a frontend page

1. Create page component in `frontend/src/pages/`
2. Add route in `frontend/src/App.tsx`
3. Add sidebar entry in `frontend/src/components/layout/sidebar.tsx`
4. Add query hooks in `frontend/src/hooks/use-api-queries.ts`
5. Add TypeScript types in `frontend/src/types/api.ts`

### Adding an analytics tab

1. Create tab component in the relevant `frontend/src/components/<feature>/` directory
2. Add query hook in `frontend/src/hooks/use-api-queries.ts` if new endpoint
3. Add TypeScript types in `frontend/src/types/api.ts`
4. Wire into parent page's tab navigation

### Adding an MCP tool

1. Add tool function in `src/primer/mcp/tools.py`
2. Register with `@mcp.tool()` decorator in `src/primer/mcp/server.py`
3. Add tests in `tests/`

### Updating model pricing

1. Edit `MODEL_PRICING` dict in `src/primer/common/pricing.py`
2. Prices are per-token (divide published per-MTok prices by 1,000,000)
3. New model families need a new prefix key (e.g., `"claude-opus-5"`)
4. Also update `MODEL_PRICING` in `frontend/src/lib/utils.ts` for client-side cost display
5. Run `pytest tests/test_pricing.py` to verify
