---
hide:
  - navigation
  - toc
---

<div class="primer-hero" markdown>

# Primer

**Agent harness intelligence for engineering teams.**

Primer captures work across Claude Code, Cursor, Codex CLI, and Gemini CLI, then measures how
your agent harness — tool design, context management, caching, orchestration, and permission
boundaries — determines outcome quality. It turns that telemetry into harness effectiveness
scores, quality attribution, cost proof, exemplars, and experiments your team can standardize.

<div class="primer-buttons">
  <a href="getting-started/" class="primary">Get Started</a>
  <a href="architecture/" class="secondary">Read the Architecture</a>
</div>

</div>

## What Primer Proves

<div class="primer-features" markdown>

<div class="feature" markdown>
### Harness Intelligence
Measure how your agent harness shapes outcomes — which tool designs, context strategies, and
caching patterns are tied to better merge rates, fewer review findings, and lower cost per success.
</div>

<div class="feature" markdown>
### Customization Intelligence
Track MCPs, skills, commands, templates, and subagents by provenance, state, reliability, and
outcome so you can separate explicit choices from defaults.
</div>

<div class="feature" markdown>
### Exemplar Sessions
Surface bright spots, exemplar sessions, and reusable assets that top performers use so other
engineers can copy what works.
</div>

<div class="feature" markdown>
### Experiments
Turn recommendations into interventions and structured experiments, then measure whether a rollout,
playbook, or model change improved outcomes.
</div>

<div class="feature" markdown>
### Delegation and Agent Teams
Capture delegation graphs and coordinated agent-team patterns so you can see when orchestration
helps and when it adds friction.
</div>

<div class="feature" markdown>
### Closed-Loop Coaching
Move from evidence to action with workflow playbooks, model recommendations, team skill gaps, and
project enablement guidance.
</div>

</div>

---

## Why The Product Is Different

Primer is strongest when it links:

- **workflow fingerprint -> quality**
- **workflow fingerprint -> cost**
- **customization stack -> reliability**
- **exemplar session -> coaching**
- **recommendation -> experiment -> measured change**

That is the core product loop. Primer is no longer just a usage dashboard.

## Product Loop

1. **Capture** multi-agent sessions, PRs, review findings, repo context, and customization state.
2. **Normalize** them into workflows, recovery paths, change shape, delegation graphs, and asset reuse.
3. **Surface** those signals by persona across leadership, platform, team, project, and engineer views.
4. **Act** with playbooks, recommendations, exemplars, and interventions.
5. **Measure** whether the change improved quality, cost, friction, or adoption.

## Quick Start

```bash
pip install primer
primer init
primer server start
primer hook install
```

Use `primer sync` to backfill supported local sessions, or deploy with Docker or Helm for shared
environments.

## Architecture

```
AI agents + local capture ──POST──┐
GitHub App / webhooks ────────────┼──▸ FastAPI platform ──▸ SQLite/PostgreSQL
MCP sidecar ─────────────GET──────┘             │
                                                └──▸ React dashboard
```

Primer has four major runtime surfaces:

- **Capture layer** discovers and extracts local sessions across supported agents
- **FastAPI platform** ingests data and computes workflow, quality, cost, growth, maturity, and experiment analytics
- **React dashboard** exposes organization, project, growth, quality, FinOps, and intervention workflows
- **MCP sidecar** brings session-start coaching, live signals, nudges, stats, recaps, and manager packs into the engineer workflow

Read the full [Architecture guide](architecture.md) for details.

## Recommended Next Reads

- [Product Flow](product-flow.md) for the full capture -> normalize -> surface -> act -> measure loop
- [Architecture](architecture.md) for the data model, trust boundaries, and implementation patterns
- [User Journeys](user-journeys.md) for how engineers, leads, and platform teams use the product
