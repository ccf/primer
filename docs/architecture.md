# Architecture

## System Overview

Primer is a multi-surface platform for agentic engineering intelligence:

```
┌──────────────────────────────┐
│ AI coding agents            │
│ Claude Code / Codex CLI     │
│ Gemini CLI / Cursor         │
└──────────────┬───────────────┘
               │ hooks / sync / import
               ▼
┌──────────────────────────────┐
│ Capture layer               │
│ extractor registry          │
│ local discovery             │
│ transcript + telemetry map  │
└──────────────┬───────────────┘
               │ POST / ingest
               ▼
┌──────────────────────────────┐      ┌──────────────────────────────┐
│ Primer API platform         │◀────▶│ MCP sidecar                  │
│ FastAPI + service layer     │ HTTP │ stats, friction, coaching    │
└──────────────┬───────────────┘      └──────────────────────────────┘
               │
      ┌────────▼────────┐
      │ SQLite /        │
      │ PostgreSQL      │
      └────────┬────────┘
               │
     ┌─────────▼─────────┐
     │ React dashboard   │
     │ org / profile /   │
     │ projects / growth │
     └───────────────────┘

GitHub App + webhooks feed pull requests, commits, review findings, and repository context into the
same platform.
```

Primer is no longer just a session dashboard. The product loop is:

1. Capture work across agent types.
2. Normalize it into comparable workflow and outcome semantics.
3. Surface role-specific views.
4. Turn recommendations into interventions.
5. Measure whether behavior or environment changes improved outcomes.

## Runtime Surfaces

### Capture Layer

Code lives in [`src/primer/hook/`](/Users/ccf/git/primer/src/primer/hook).

- Agent-specific extractors handle Claude Code, Codex CLI, Gemini CLI, and Cursor.
- Claude Code uses a SessionEnd hook.
- Other sources can be discovered and synced through `primer sync`.
- Cursor supports both Primer-managed import bundles and native discovery paths.
- Git metadata can be attached during sync so sessions correlate to repositories and commits.

### API Platform

Code lives in [`src/primer/server/`](/Users/ccf/git/primer/src/primer/server).

- FastAPI app with routers for auth, ingest, sessions, analytics, alerts, interventions, admin,
  explorer, webhooks, and FinOps.
- Service-layer architecture keeps routers thin and business logic in `services/`.
- Role-aware dependencies scope data for engineers, team leads, and admins.
- Measurement-integrity and source-capability logic prevent unsupported telemetry from polluting
  downstream metrics.

### Dashboard

Code lives in [`frontend/src/`](/Users/ccf/git/primer/frontend/src).

- Leadership sees organization, quality, friction, maturity, FinOps, growth, projects, and
  interventions.
- Engineers get profile, sessions, growth, synthesis, and explorer views.
- Project workspaces combine readiness, workflow fingerprints, friction hotspots, quality, cost,
  and enablement recommendations.
- Session detail pages expose evidence like transcripts, execution evidence, change shape,
  recovery paths, and workflow profiles.

### MCP Sidecar

Code lives in [`src/primer/mcp/`](/Users/ccf/git/primer/src/primer/mcp).

- Syncs local sessions to the server.
- Exposes personal stats, team overview, friction reports, recommendations, and coaching.
- Lets insights show up inside the engineer workflow rather than only after the fact.

## Data Model

Primer now uses a broader data model than the original session-only design. The most important
tables are grouped below.

### Organization and Access

- `teams`
- `engineers`
- `refresh_tokens`
- `audit_logs`

### Session Intelligence

- `sessions`
- `session_messages`
- `session_facets`
- `tool_usages`
- `model_usages`
- `daily_stats`
- `ingest_events`

### Derived Workflow Evidence

- `session_execution_evidence`
- `session_change_shapes`
- `session_recovery_paths`
- `session_workflow_profiles`

These tables power health scoring, workflow fingerprints, recovery analysis, and project
workflow summaries.

### Projects and Quality

- `git_repositories`
- `session_commits`
- `pull_requests`
- `review_findings`

These connect session behavior to repository readiness, PR outcomes, and automated review signals.

### Operational and Decision Loops

- `alerts`
- `alert_configs`
- `budgets`
- `narrative_cache`
- `interventions`

These support anomaly detection, cost controls, narrative synthesis, and closed-loop follow-through.

## Source Capability and Trust Model

Primer treats source parity as a first-class architecture concern.

The capability registry in
[`src/primer/common/source_capabilities.py`](/Users/ccf/git/primer/src/primer/common/source_capabilities.py)
declares, per agent type, whether telemetry is:

- `required`
- `optional`
- `unavailable`

for these fields:

- transcript
- tool calls
- model usage
- facets
- native discovery

Analytics and measurement-integrity services use this registry to:

- exclude unsupported sources from coverage penalties
- avoid computing metrics from fields a source cannot provide
- surface parity and coverage explicitly in admin views

This is one of the most important platform decisions in the codebase because it protects the
credibility of cross-agent analytics.

## Key Flows

### Session Ingest

```
Local session discovered
  -> agent extractor normalizes transcript and telemetry
  -> sync attaches git metadata when available
  -> POST /api/v1/ingest/session
  -> ingest service upserts session, facets, messages, tools, models, commits
  -> derived evidence is computed:
       execution evidence
       change shape
       recovery path
       workflow profile
```

### Analytics Query

```
Dashboard requests analytics endpoint
  -> auth dependency resolves engineer / team / admin scope
  -> service applies source-capability gating where needed
  -> metrics aggregate over sessions, repositories, PRs, findings, or interventions
  -> typed response is returned to React via TanStack Query
```

### Project Workspace

```
User opens project workspace
  -> project_workspace_service gathers readiness, repository context, workflow fingerprints,
     friction hotspots, quality, cost, and enablement recommendations
  -> page turns observed bottlenecks into concrete next actions
```

### MCP Coaching

```
Engineer calls MCP tool
  -> sidecar requests scoped analytics from Primer API
  -> coaching service combines overview, maturity, friction, tips, and config optimization
  -> result is returned as a compact in-workflow brief
```

## Auth Model

Primer currently uses three access patterns:

### Engineer API Keys

- Stored as bcrypt hashes on engineers.
- Used for ingest, session sync, and engineer-scoped API access.
- Best fit for hooks, CLI sync, and MCP sidecar access.

### GitHub OAuth + JWT

- Used for dashboard login.
- Supports role-aware browser sessions with refresh tokens.
- Also powers auto-provisioning and GitHub identity matching.

### Admin API Key

- Shared secret via `x-admin-key`.
- Useful for internal deployments, automation, and bootstrap admin access.

Role scoping is enforced in FastAPI dependencies rather than duplicated across routers.

## Implementation Patterns

- SQLAlchemy 2.0 models with `Mapped` / `mapped_column`
- Pydantic v2 schemas shared across API responses and validation boundaries
- Service-layer business logic with thin routers
- Alembic migrations for all schema evolution
- React + TanStack Query on the frontend
- Capability-aware analytics rather than assuming every source has identical telemetry

## Where To Read Next

- [Product Flow](product-flow.md) for the user-facing loop
- [User Journeys](user-journeys.md) for the main personas and decision paths
- [API](api.md) for endpoint-level detail
