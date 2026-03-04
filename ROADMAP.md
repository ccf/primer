# Primer Roadmap

Organized by capability area. Items marked with ✅ are shipped; items marked with ◻️ are planned.

## Session Intelligence

- [x] Session search with full-text, outcome, type, model, branch filters
- [x] Transcript viewer with message-level detail
- [x] Session health scoring (outcome + friction + duration + satisfaction composite)
- [x] LLM-powered facet extraction (goals, friction types, satisfaction signals)
- [x] End reason breakdown with success rate per reason
- [x] Goal analytics (session type and goal category breakdown)
- [x] Permission mode analysis (success rate by permission level)
- [x] Satisfaction trend tracking (satisfied / neutral / dissatisfied over time)
- [x] Similar sessions panel with 3-tier relevance matching

## Friction & Bottleneck Analysis

- [x] Friction type classification (permission denied, timeout, context limit, edit conflict, tool error, exec error)
- [x] Friction impact scoring (occurrence count × success rate penalty)
- [x] Friction trend chart (count + rate over time)
- [x] Project-level friction breakdown
- [x] Friction cluster analysis with sample details
- [x] Anomaly detection for friction spikes

## Engineer Intelligence

- [x] Engineer leaderboard with multi-dimensional ranking
- [x] Personal trajectory dashboard with weekly sparklines
- [x] Strengths and friction breakdown per engineer
- [x] Peer benchmarking (percentile ranking, vs-team-avg deltas)
- [x] AI-generated narrative insights per engineer
- [x] Personalized tips based on friction patterns and tool gaps
- [x] Config optimization suggestions from team benchmark comparison
- [x] Skill inventory with proficiency levels per tool
- [x] Learning paths generated from high-performer patterns

## Growth & Onboarding

- [x] Cohort comparison (new hire / ramping / experienced)
- [x] Time-to-team-average tracking for new hires
- [x] Onboarding velocity scoring
- [x] Onboarding recommendations
- [x] Shared behavior pattern discovery with approach comparison
- [ ] **Bright spot detection** — explicitly surface high-performing engineers and cross-pollinate their patterns across teams

## AI Maturity

- [x] Tool leverage scoring (0-100 composite per engineer)
- [x] Tool category classification (core, search, orchestration, skill, MCP)
- [x] Orchestration adoption rate tracking
- [x] Agent and skill usage analytics (invocation patterns, delegation depth)
- [x] Tool adoption rates and trend charts
- [x] Engineer tool proficiency table
- [x] Project AI-readiness scoring (CLAUDE.md, AGENTS.md, .claude/ detection)
- [x] Daily leverage trend tracking
- [ ] **Tool source classification** — distinguish built-in vs marketplace vs custom tools; identify which MCP servers tools originate from
- [ ] **Cross-team tooling landscape** — analyze tool overlap and reuse across teams; highlight unique vs shared tooling

## Code Quality

- [x] GitHub OAuth SSO
- [x] Pull request sync via GitHub App
- [x] Commit correlation with sessions
- [x] Claude-assisted vs non-Claude PR comparison (merge rate, review comments, time to merge)
- [x] Quality by session type (debugging, feature, refactoring)
- [x] Code volume tracking (daily lines added/deleted)
- [x] Engineer quality ranking table
- [x] Repository AI-readiness scoring

## FinOps & Cost Management

- [x] Per-model spend tracking with daily cost chart
- [x] Cost breakdown by model
- [x] Cache efficiency analytics (hit rates, savings, per-engineer potential)
- [x] Billing mode detection (API vs subscription)
- [x] Subscription vs API cost modeling with optimal plan recommendations
- [x] 30-day cost forecasting (linear regression with confidence bands)
- [x] Budget tracking with burn-rate alerts and projected overrun warnings
- [x] Cost per successful outcome metric
- [ ] **Break-even analysis** — calculate the usage threshold where API billing becomes cheaper than a subscription seat, with per-engineer recommendations

## AI Synthesis

- [x] AI-generated narrative reports (engineer, team, org scope)
- [x] Narrative caching with TTL-based expiry
- [x] Auto-refresh via lifespan task
- [x] Conversational data explorer (SSE-streamed tool-use chat)
- [x] AI-powered recommendations panel

## Organization & Administration

- [x] Hub-and-spoke dashboard with KPI strip, activity section, attention alerts, deep-dive cards
- [x] Custom date range picker (7d / 30d / 90d / 1y presets + custom)
- [x] Team management with member stats
- [x] Role-based access control (engineer, team lead, admin)
- [x] Admin panel (engineer/team management, audit log, system stats)
- [x] Alert system with configurable thresholds, acknowledge/dismiss workflow
- [x] Slack notification integration
- [x] CSV and PDF export
- [x] API rate limiting
- [x] Dark mode with system preference detection
- [ ] **Multi-tenant workspace isolation** — separate data boundaries for distinct organizations sharing a single Primer instance

## Platform & Integrations

- [x] Multi-agent support (Claude Code, Codex CLI, Gemini CLI)
- [x] SessionEnd hook system with agent-specific installers
- [x] `primer sync --watch` for agents without hook systems
- [x] MCP sidecar (sync, my_stats, team_overview, friction_report, recommendations)
- [x] Docker Compose and Kubernetes Helm deployment
- [x] PostgreSQL and SQLite support
- [x] Alembic migration bundling in pip package
- [ ] **Performance measurement views** — leadership-oriented scorecards combining productivity, quality, cost efficiency, and adoption metrics into a single per-engineer view
