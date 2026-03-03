<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="brand/logo-wordmark-light.svg">
    <source media="(prefers-color-scheme: light)" srcset="brand/logo-wordmark.svg">
    <img src="brand/logo-wordmark.svg" alt="Primer" width="280">
  </picture>
</p>

<p align="center">
  <b>See how your team uses AI coding tools.</b>
</p>

<p align="center">
  <a href="https://ccf.github.io/primer/docs/installation/">Get Started</a> &middot;
  <a href="https://ccf.github.io/primer/docs/">Docs</a> &middot;
  <a href="ROADMAP.md">Roadmap</a> &middot;
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

<p align="center">
  <a href="https://github.com/ccf/primer/actions/workflows/ci.yml"><img src="https://github.com/ccf/primer/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <img src="https://img.shields.io/badge/coverage-92%25-brightgreen.svg" alt="Coverage: 92%">
  <img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT">
</p>

---

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/dashboard.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/images/dashboard-light.png">
    <img src="docs/images/dashboard-light.png" alt="Primer dashboard showing team analytics, cost tracking, and engineer profiles" width="100%">
  </picture>
</p>

---

Primer is a self-hosted, open-source analytics platform for AI coding tools. It captures session data from [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Codex CLI](https://github.com/openai/codex), and [Gemini CLI](https://github.com/google-gemini/gemini-cli) — then turns it into dashboards, cost reports, and actionable insights for your engineering team. Claude Code has the deepest integration today; Codex CLI and Gemini CLI support is in early access.

Your data stays on your infrastructure. No telemetry leaves your network.

## Features

- **Team Dashboard** — Session volume, token usage, cost trends, and activity heatmaps with period-over-period comparisons
- **Cost Analysis & FinOps** — Per-model spend tracking, cache savings analysis, subscription vs API cost modeling, 30-day cost forecasting, and budget management with burn-rate alerts
- **Engineer Profiles** — Personal trajectory dashboards with weekly sparklines, strengths, friction breakdown, and peer benchmarking
- **Friction Detection** — Surface where engineers struggle: tool errors, permission blocks, timeouts, and context limits
- **Anomaly Alerts** — Automatic detection of cost spikes, usage drops, and success rate degradation with configurable thresholds
- **AI Maturity Scoring** — Tool leverage scores, category usage, project AI-readiness checks, and agent/skill analytics
- **Session Browser** — Full-text search with outcome, type, and model filters plus transcript viewer with message-level detail
- **Multi-Agent Support** — Collect sessions from Claude Code, Codex CLI, and Gemini CLI in a single dashboard
- **GitHub Integration** — OAuth SSO, pull request sync, commit correlation, and repository AI-readiness scoring
- **MCP Sidecar** — Claude queries your team's own usage patterns mid-session: stats, friction reports, recommendations
- **Role-Based Access** — Engineers see their profile; leadership sees the org dashboard; admins manage teams and thresholds

## Quickstart

**One-liner install:**

```bash
curl -fsSL https://ccf.github.io/primer/install.sh | sh
```

**Or install manually:**

```bash
pip install primer-io            # Install
primer init                      # Initialize database and config
primer server start              # Start API + dashboard
primer hook install              # Register the SessionEnd hook
```

**Docker:**

```bash
cp .env.docker.example .env && make up
```

See the [Installation guide](https://ccf.github.io/primer/docs/installation/) for full setup details, GitHub integration, and production configuration.

## How It Works

```
AI Coding Tools ──SessionEnd Hook──▶ Primer API ◀──MCP Sidecar
 (Claude Code,                           │
  Codex CLI,                             ▼
  Gemini CLI)                    PostgreSQL / SQLite
                                         │
                                         ▼
                                  React Dashboard
```

1. **SessionEnd Hook** — Automatically uploads session transcripts after each AI coding session
2. **REST API** — FastAPI service that stores sessions, computes analytics, and serves the dashboard
3. **Dashboard** — React + Tailwind CSS frontend with role-based views and real-time filtering
4. **MCP Sidecar** — Lets Claude query your team's data during conversations

## Documentation

| | Guide | Description |
|-|-------|-------------|
| **Getting Started** | [Installation](https://ccf.github.io/primer/docs/installation/) | Install, configure, first dashboard |
| | [Configuration](https://ccf.github.io/primer/docs/configuration/) | Environment variables and options |
| | [CLI Reference](https://ccf.github.io/primer/docs/cli-reference/) | All `primer` commands |
| **Architecture** | [Architecture](https://ccf.github.io/primer/docs/architecture/) | System design, data model, request flows |
| | [API Reference](https://ccf.github.io/primer/docs/api/) | Endpoints, auth, request/response schemas |
| **Guides** | [GitHub Integration](https://ccf.github.io/primer/docs/github-integration/) | OAuth login, GitHub App for PR sync |
| | [Deployment](https://ccf.github.io/primer/docs/deployment/) | Docker Compose, Helm, PostgreSQL, scaling |
| | [MCP Sidecar](https://ccf.github.io/primer/docs/mcp/) | Mid-session stats, friction reports, recommendations |

## About the Name

Named after the Young Lady's Illustrated Primer in Neal Stephenson's *The Diamond Age* — an adaptive, AI-driven book that observes its reader, understands context, and transforms complexity into personalized guidance. Primer brings that same principle to engineering organizations.

## Contributing

We welcome contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- [Open issues](https://github.com/ccf/primer/issues) — bugs and feature requests
- [Roadmap](ROADMAP.md) — what's planned and complete

## License

[MIT](LICENSE)
