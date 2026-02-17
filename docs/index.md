---
hide:
  - navigation
  - toc
---

<div class="primer-hero" markdown>

# Primer

**AI engineering analytics for Claude Code teams.**

Aggregate usage data, track developer productivity, and surface actionable insights across your engineering organization.

<div class="primer-buttons">
  <a href="getting-started/" class="primary">Get Started</a>
  <a href="https://github.com/ccf/primer" class="secondary">GitHub</a>
</div>

</div>

<div class="primer-features" markdown>

<div class="feature" markdown>
### Usage Analytics
Track sessions, token consumption, cost breakdowns, and model usage patterns across teams and engineers.
</div>

<div class="feature" markdown>
### GitHub Integration
Sync pull requests, correlate commits with Claude Code sessions, and measure AI-readiness across repositories.
</div>

<div class="feature" markdown>
### Role-Based Dashboard
Engineers see a GitHub-like profile with personal stats. Leadership sees org-wide metrics, leaderboards, and team comparisons.
</div>

<div class="feature" markdown>
### Friction Detection
Identify bottlenecks, tool over-reliance, and workflow inefficiencies with automated recommendations.
</div>

<div class="feature" markdown>
### MCP Sidecar
Five built-in MCP tools let Claude Code query its own usage stats, team overviews, and friction reports.
</div>

<div class="feature" markdown>
### AI Maturity Scoring
Score repositories on AI-readiness (CLAUDE.md, AGENTS.md, .claude/ config) and track adoption across the org.
</div>

</div>

---

## Quick Start

```bash
pip install -e .
alembic upgrade head
python scripts/seed_data.py     # optional: generate demo data
uvicorn primer.server.app:app --reload
```

Then open [localhost:5173](http://localhost:5173) for the dashboard.

See the [Getting Started guide](getting-started.md) for the full walkthrough.

## Architecture

```
Claude Code (hook) ──POST──▸ FastAPI Server ──▸ SQLite/PostgreSQL
                                  │
MCP Sidecar ──────GET/POST──▸─────┘
                                  │
React Dashboard ◂──GET────────────┘
```

Primer has three entry points:

- **SessionEnd Hook** extracts usage data from Claude Code and sends it to the server
- **MCP Sidecar** provides five tools for Claude Code to query its own analytics
- **React Dashboard** visualizes everything with role-based views

Read the full [Architecture guide](architecture.md) for details.
