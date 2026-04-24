<p align="center">
  <a href="https://useprimer.dev">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="brand/logo-wordmark-light.svg">
      <source media="(prefers-color-scheme: light)" srcset="brand/logo-wordmark.svg">
      <img src="brand/logo-wordmark.svg" alt="Primer" width="280">
    </picture>
  </a>
</p>

<p align="center">
  <b>See which agent harness patterns actually work.</b>
</p>

<p align="center">
  <a href="https://useprimer.dev"><b>🌐 Website</b></a> &middot;
  <a href="https://demo.useprimer.dev"><b>🎮 Live Demo</b></a> &middot;
  <a href="https://useprimer.dev/docs/installation/">Get Started</a> &middot;
  <a href="https://useprimer.dev/docs/">Docs</a> &middot;
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
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/dashboard-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/images/dashboard-light.png">
    <img src="docs/images/dashboard-light.png" alt="Primer — org-level activity, outcomes, alerts, and deep-dive insights" width="100%">
  </picture>
</p>

---

Your team adopted AI coding tools. Now you need to know what to standardize.

Primer is an open-source agent harness intelligence platform for engineering teams. It captures
session data from [Claude Code](https://docs.anthropic.com/en/docs/claude-code),
[Codex CLI](https://github.com/openai/codex),
[Gemini CLI](https://github.com/google-gemini/gemini-cli), and Cursor, then measures how your
agent harness — tool design, context management, caching, orchestration, and permission
boundaries — determines outcome quality. It turns that telemetry into harness effectiveness
scores, quality attribution, cost proof, exemplar sessions, coaching, and experiments.
Self-hosted. Privacy-first. Your data never leaves your network.

## Questions Primer Answers

### For engineering leadership

- **Is our AI investment paying off?** — Cost per successful outcome, ROI ratio, time saved vs. dollars spent
- **Which teams have figured it out and which are struggling?** — Team-level adoption, success rates, and leverage scores with cross-team comparison
- **What systemic issues tank AI effectiveness across the org?** — Friction impact scoring: not just "errors happen" but "this error type costs us 40% lower success rates"
- **Are we spending efficiently?** — Per-engineer plan modeling (API vs. Pro vs. Max), cache hit optimization, budget burn-rate tracking

### For team leads

- **Who needs help and what specific help?** — Personalized tips, skill gaps, tool diversity analysis, and peer benchmarking
- **How fast are new hires ramping up?** — Cohort analysis comparing onboarding curves against team baselines
- **Are AI-assisted PRs actually better?** — Side-by-side comparison: merge time, review comments, merge rate for Claude vs. non-Claude PRs
- **Where should I invest in training?** — Tool proficiency scoring (novice → expert) per engineer, per tool category

### For individual engineers

- **How am I trending?** — Weekly trajectory with success rate, cost, and session patterns
- **What keeps tripping me up?** — Personal friction breakdown: permission blocks, context limits, tool errors
- **Am I using the right tools?** — Config optimization suggestions based on team benchmarks and entropy-based diversity scoring
- **What should I try next?** — Learning paths generated from high-performer patterns in your org

<p align="center">
  <img src="docs/images/engineer-profile-dark.png" alt="Engineer profile with trajectory, friction analysis, and AI-generated insights" width="100%">
</p>

## What Makes This Different

**Harness intelligence, not just usage tracking.** Primer measures how your agent harness
configuration — tool design, caching strategy, orchestration depth, context management, and
permission boundaries — determines outcome quality. It links harness patterns to merge rates,
review quality, cost, and reusable assets so you can decide which configurations to standardize.

**Friction analysis, not just error counting.** Primer doesn't just count failures. It classifies
*why* sessions fail, what engineers tried next, and which recoveries actually worked. You learn
that `permission_denied` errors cause lower success rates, not just that they happened sometimes.

**Customization and orchestration intelligence.** Primer captures MCPs, skills, commands,
subagents, delegation patterns, and agent-team modes so you can see which explicit agent stacks
differentiate high performers and which ones create friction.

**Individual intelligence, not just org dashboards.** Every engineer gets a trajectory view,
strengths profile, friction breakdown, AI-generated narrative, model coach, and learning paths.
The MCP sidecar now brings session-start coaching, live signals, in-session nudges, stats,
friction reports, recaps, and manager review packs into the session without forcing context
switching.

**Cost optimization, not just cost tracking.** Primer models whether each engineer should be on API billing, Pro ($20/mo), or Max ($100/mo) based on actual usage. It measures cache hit rates per engineer and surfaces how much money is being left on the table. Budget burn-rate alerts catch overruns before they happen.

**Experiments, not just recommendations.** Primer turns recommendations into interventions and
structured experiments so you can measure whether a rollout, training change, or playbook
actually improved outcomes.

<p align="center">
  <img src="docs/images/finops-dark.png" alt="FinOps — cost tracking, cache analytics, subscription modeling, and budget management" width="100%">
</p>

## Capabilities

| Area | What You Get |
|------|-------------|
| **Organization Overview** | Session volume, success rates, health scores, activity heatmaps, outcome distribution, anomaly alerts |
| **FinOps & Cost Management** | Per-model spend, cache savings analysis, API vs. subscription modeling, 30-day linear regression forecasting, budget burn-rate tracking |
| **Engineer Profiles** | Weekly trajectory sparklines, strengths/friction breakdown, peer benchmarking, AI-generated narrative insights |
| **AI Maturity** | Leverage scores (tool mastery, orchestration depth, efficiency), Effectiveness scores (success rate, cost efficiency), model diversity, agent team detection, project AI-readiness |
| **Friction Intelligence** | Categorized friction types with impact scoring, bottleneck detection, root cause patterns, cluster analysis |
| **Quality & Code Impact** | PR merge rates, workflow-based quality attribution, post-merge outcomes, Claude-assisted vs. non-Claude comparison, code volume per session, review comment analysis |
| **AI Synthesis** | LLM-generated narrative reports at org, team, and engineer scope — turns metrics into stories |
| **Conversational Explorer** | Natural language queries over your data via SSE-streamed tool-use chat |
| **Session Browser** | Full-text search, outcome/model/type filters, transcript viewer, message-level detail |
| **MCP Sidecar** | Session-start coaching, live signals, in-session nudges, personal recaps, manager review packs, and mid-session stats |
| **Multi-Agent Support** | Claude Code, Codex CLI, Gemini CLI, and Cursor sessions in one platform |
| **GitHub Integration** | OAuth SSO, PR sync, commit correlation, repository AI-readiness scoring |

## Quickstart

> **🎮 Want to see it first?** [demo.useprimer.dev](https://demo.useprimer.dev) is a live, read-only instance with sample data from a fictional 25-engineer org. No signup required.

**One-liner install:**

```bash
curl -fsSL https://useprimer.dev/install.sh | sh
```

**Or install manually:**

```bash
pip install useprimer            # Install (Python module is `primer`)
primer init                      # Initialize database and config
primer server start              # Start API + dashboard
primer hook install              # Register the SessionEnd hook
```

**Docker:**

```bash
cp .env.docker.example .env && make up
```

See the [Installation guide](https://useprimer.dev/docs/installation/) for full setup, GitHub integration, and production configuration.

## How It Works

```
AI agents + local capture ──POST──┐
GitHub App / webhooks ────────────┼──▶ Primer API ◀──MCP Sidecar
                                  │         │
                                  │         ▼
                                  └── PostgreSQL / SQLite
                                            │
                                            ▼
                                     React Dashboard
```

1. **Capture Layer** — Hooks, sync, and import flows discover sessions across Claude Code, Codex
   CLI, Gemini CLI, and Cursor. Derived evidence includes facets, execution evidence, change
   shape, recovery paths, and workflow profiles.
2. **REST API** — FastAPI service with routers covering analytics, alerting, FinOps, quality,
   maturity, interventions, explorer, and admin workflows. Role-based access is enforced across
   the platform.
3. **Dashboard** — React frontend with organization, project, growth, quality, and individual
   views. Date-range filtering, CSV/PDF export, and role-based navigation are built in.
4. **MCP Sidecar** — Engineers query their own data during sessions for stats, friction,
   recommendations, and coaching.

## Documentation

| | Guide | Description |
|-|-------|-------------|
| **Getting Started** | [Installation](https://useprimer.dev/docs/installation/) | Install, configure, first insights |
| | [Configuration](https://useprimer.dev/docs/configuration/) | Environment variables and options |
| | [CLI Reference](https://useprimer.dev/docs/cli/) | All `primer` commands |
| **Architecture** | [Server & API](https://useprimer.dev/docs/server/) | System design, data model, auth, endpoints |
| | [Hook System](https://useprimer.dev/docs/hooks/) | Multi-agent extractor registry |
| | [MCP Sidecar](https://useprimer.dev/docs/mcp/) | Mid-session stats, friction reports, recommendations |
| **Guides** | [GitHub Integration](https://useprimer.dev/docs/github/) | OAuth login, GitHub App for PR sync |
| | [FinOps & Cost Management](https://useprimer.dev/docs/finops/) | Cache analytics, cost modeling, forecasting, budgets |
| | [Alert Thresholds](https://useprimer.dev/docs/alerts/) | Anomaly detection and Slack notifications |
| | [Deployment](https://useprimer.dev/docs/deployment/) | Docker Compose, Helm, PostgreSQL, scaling |

## About the Name

Named after the Young Lady's Illustrated Primer in Neal Stephenson's *The Diamond Age* — an adaptive, AI-driven book that observes its reader, understands context, and transforms complexity into personalized guidance. Primer brings that same principle to engineering organizations: observe how your team uses AI, understand the patterns, and guide each engineer toward mastery.

## Contributing

We welcome contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- [Open issues](https://github.com/ccf/primer/issues) — bugs and feature requests
- [Roadmap](ROADMAP.md) — what's planned and complete

## License

[MIT](LICENSE)
