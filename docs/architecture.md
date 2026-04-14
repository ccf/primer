# Architecture

## System Overview

Primer is a multi-surface harness intelligence platform for agentic engineering:

```
┌──────────────────────────────┐
│ AI coding agents            │
│ Claude Code / Cursor        │
│ Codex CLI / Gemini CLI      │
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
│ FastAPI + service layer     │ HTTP │ stats, coaching, sync        │
└──────────────┬───────────────┘      └──────────────────────────────┘
               │
      ┌────────▼────────┐
      │ SQLite /        │
      │ PostgreSQL      │
      └────────┬────────┘
               │
     ┌─────────▼─────────┐
     │ React dashboard   │
     │ org / project /   │
     │ growth / maturity │
     └───────────────────┘

GitHub OAuth, App sync, and webhooks feed pull requests, review findings, commits, and repository
context into the same platform.
```

Primer is no longer just a session dashboard. The platform loop is:

1. Capture work across agent types and projects.
2. Normalize it into trustworthy workflow and customization semantics.
3. Surface those signals by persona.
4. Turn recommendations into interventions and experiments.
5. Measure whether behavior or environment changes improved outcomes.

## Runtime Surfaces

### Capture Layer

Code lives in `src/primer/hook/`.

- Agent-specific extractors handle Claude Code, Cursor, Codex CLI, and Gemini CLI.
- Claude Code uses a SessionEnd hook.
- Other sources can be discovered and synced through `primer sync`.
- Git metadata can be attached during sync so sessions correlate to repositories, commits, and PRs.
- Capture is intentionally source-aware: the platform records what each source can and cannot
  provide before analytics are computed.

### API Platform

Code lives in `src/primer/server/`.

- FastAPI app with routers for auth, ingest, sessions, analytics, alerts, interventions, admin,
  explorer, and webhooks.
- Service-layer architecture keeps routers thin and business logic in `services/`.
- Role-aware dependencies scope data for engineers, team leads, and admins.
- Measurement-integrity and source-capability logic prevent unsupported telemetry from polluting
  downstream metrics.

### Dashboard

Code lives in `frontend/src/`.

- Leadership sees organization, quality, friction, maturity, FinOps, growth, projects, and
  intervention surfaces.
- Engineers get profile, sessions, growth, synthesis, and explorer views.
- Project workspaces combine readiness, workflow fingerprints, friction hotspots, quality, cost,
  and enablement recommendations.
- Session detail pages expose evidence like transcripts, execution evidence, change shape,
  recovery paths, workflow profiles, delegation graphs, and customization state.

### MCP Sidecar

Code lives in `src/primer/mcp/`.

- Syncs local sessions to the server.
- Exposes personal stats, team overview, friction reports, recommendations, and coaching.
- Lets insights show up inside the engineer workflow rather than only after the fact.

## Semantic Layer

Primer's architecture is built around a derived semantic layer rather than raw transcripts alone.
The most important normalized concepts are:

- **Workflow profiles**: archetypes and fingerprints that describe how work was approached
- **Recovery paths**: what engineers tried after failure and what recovered
- **Change shape**: how a session translated into editing, execution, verification, and fixes
- **Customization snapshots**: MCPs, skills, commands, templates, and subagents by provenance and state
- **Delegation graphs**: who delegated to which agent or subagent and how coordination happened
- **Reusable assets**: prompts, skills, commands, and templates that spread across teams
- **Interventions and experiments**: structured actions taken in response to evidence

This semantic layer is what lets Primer connect workflow -> quality -> cost -> coaching, which is
the core product advantage.

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

### Derived Workflow and Execution Evidence

- `session_execution_evidence`
- `session_change_shapes`
- `session_recovery_paths`
- `session_workflow_profiles`

These tables power workflow fingerprints, workflow compare mode, recovery analysis, and project
workflow summaries.

### Customization and Orchestration Evidence

- `session_customizations`

This table records explicit customizations such as MCPs, skills, commands, templates, and
subagents, along with provenance, source classification, and state like `available`, `enabled`,
and `invoked`.

Delegation evidence is currently derived at query time from session detail rather than persisted as
a standalone table, but it is treated as a first-class concept across maturity analytics and
session detail.

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

`interventions` now also carry experiment metadata so Primer can measure structured rollouts such as
model changes, prompt standardization, or enablement playbooks.

## Source Capability and Trust Model

Primer treats source parity as a first-class architecture concern.

The capability registry in `src/primer/common/source_capabilities.py` declares, per agent type,
whether telemetry is:

- `required`
- `optional`
- `unavailable`

for fields like:

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
       customization snapshots
```

### Analytics Query

```
Dashboard requests analytics endpoint
  -> auth dependency resolves engineer / team / admin scope
  -> service applies source-capability gating where needed
  -> metrics aggregate over sessions, repositories, PRs, findings, or interventions
  -> typed response is returned to React via TanStack Query
```

### Growth and Coaching

```
Growth or profile surface loads
  -> service joins workflow evidence, reuse analytics, exemplars, team gaps,
     model guidance, and interventions
  -> user sees what to standardize, copy, or experiment with next
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

- Stored as bcrypt hashes on engineers
- Used for ingest, session sync, and engineer-scoped API access
- Best fit for hooks, CLI sync, and MCP sidecar access

### GitHub OAuth + JWT

- Used for dashboard login
- Supports role-aware browser sessions with refresh tokens
- Also powers auto-provisioning and GitHub identity matching

### Admin API Key

- Shared secret via `x-admin-key`
- Useful for internal deployments, automation, and bootstrap admin access

Role scoping is enforced in FastAPI dependencies rather than duplicated across routers.

## Implementation Patterns

- SQLAlchemy 2.0 models with `Mapped` / `mapped_column`
- Pydantic v2 schemas shared across API responses and validation boundaries
- Service-layer business logic with thin routers
- Alembic migrations for schema evolution
- React + TanStack Query on the frontend
- Capability-aware analytics rather than assuming every source has identical telemetry

## Where To Read Next

- [Product Flow](product-flow.md) for the user-facing loop
- [User Journeys](user-journeys.md) for the main personas and decision paths
- [API](api.md) for endpoint-level detail
