---
hide:
  - navigation
  - toc
---

<div class="primer-hero" markdown>

# Primer

**AI engineering intelligence for agentic teams.**

Capture how engineers use Claude Code, Codex CLI, Gemini CLI, and Cursor, then turn that
telemetry into coaching, project enablement, quality attribution, and operational decisions.

<div class="primer-buttons">
  <a href="getting-started/" class="primary">Get Started</a>
  <a href="https://github.com/ccf/primer" class="secondary">GitHub</a>
</div>

</div>

<div class="primer-features" markdown>

<div class="feature" markdown>
### Multi-Agent Capture
Ingest sessions from Claude Code, Codex CLI, Gemini CLI, and Cursor with capability-aware
analytics that avoid mixing incomparable telemetry.
</div>

<div class="feature" markdown>
### Project Intelligence
See which repositories are AI-ready, where workflow friction clusters, and what enablement work
should happen next.
</div>

<div class="feature" markdown>
### Role-Based Dashboard
Engineers get profile, growth, and session views. Leadership gets organization, quality, maturity,
FinOps, project, and intervention surfaces.
</div>

<div class="feature" markdown>
### Closed-Loop Coaching
Turn recommendations into interventions, track before-and-after measurements, and surface workflow
playbooks learned from high performers.
</div>

<div class="feature" markdown>
### MCP Sidecar
On-demand sidecar tools expose personal stats, friction reports, recommendations, and coaching
inside the engineer workflow.
</div>

<div class="feature" markdown>
### Quality, FinOps, and Maturity
Connect workflows to PR outcomes, review findings, cost efficiency, and leverage across teams,
projects, and engineers.
</div>

</div>

---

## Quick Start

```bash
pip install primer
primer init
primer server start
primer hook install
```

Use `primer sync` to backfill supported local sessions, or run Docker/Helm for shared deployments.

See the [Getting Started guide](getting-started.md) for the full walkthrough.

## Architecture

```
AI agents + local capture ──POST──┐
GitHub App / webhooks ────────────┼──▸ FastAPI platform ──▸ SQLite/PostgreSQL
MCP sidecar ─────────────GET──────┘             │
                                                └──▸ React dashboard
```

Primer has four major runtime surfaces:

- **Capture layer** discovers and extracts local sessions across supported agents
- **FastAPI platform** ingests data and computes analytics, synthesis, quality, FinOps, and alerts
- **React dashboard** exposes organization, profile, project, growth, and intervention workflows
- **MCP sidecar** brings stats, friction, recommendations, and coaching into the session

Read the full [Architecture guide](architecture.md) for details.

## Product Guides

- [Product Flow](product-flow.md) explains how capture, insights, projects, growth, and interventions fit together as one product loop.
- [User Journeys](user-journeys.md) maps Primer's main engineer, team lead, and platform workflows and outlines the future interactive tour.
