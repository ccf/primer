# Primer Roadmap

Primer is building the intelligence layer for agentic engineering: capture how engineers use AI tools, understand which workflows actually improve outcomes, and turn that data into coaching, enablement, and operational decisions.

This roadmap is organized in two layers:

1. Strategy and priorities at the top.
2. Detailed shipped and planned capabilities underneath.

Items marked with `[x]` are shipped. Items marked with `[ ]` are planned. Planned items include rough priority tags:

- `P0` - foundational and near-term
- `P1` - important follow-on work
- `P2` - valuable expansion work

## What Primer Should Help Teams Answer

- How are engineers actually using agentic tools across workflows, projects, and repositories?
- Which behaviors correlate with better outcomes: higher success rates, better PR quality, faster reviews, lower friction, and lower cost?
- Which engineers, teams, and projects are getting outsized value from AI, and why?
- Where are the systemic blockers: tool failures, poor repo readiness, prompt hygiene, context overload, or weak delegation patterns?
- What should each engineer, team lead, or platform owner do next to improve results?

## Product Goals

- Measure real engineering impact, not just usage.
- Make the semantic layer trustworthy enough for leaders to act on.
- Improve each engineer's effectiveness, not only their activity.
- Make project and repository readiness a first-class product surface.
- Close the loop from insight to intervention, not just reporting.
- Bring recommendations into the engineer workflow, not only after the fact.

## Strategic Themes

### P0: Measurement Integrity

Primer's moat depends on trustworthy semantics. We need a clean, consistent taxonomy for outcomes, goals, friction, and success, plus reprocessing and coverage tooling so every downstream metric is credible.

### P0: Engineer Impact and Quality Attribution

The platform should prove which agentic behaviors lead to better engineering outcomes. That means connecting sessions, workflows, and tool choices to PR quality, review findings, merge speed, and post-merge stability.

### P0: Project Intelligence

Projects should become a first-class lens alongside engineers and teams. Every repo should have a clear view of readiness, friction, workflow patterns, quality, cost, and recommended enablement actions.

### P1: Closed-Loop Coaching and Experimentation

Recommendations should become assignable, measurable interventions. Primer should help teams run training, tooling, and workflow experiments and track whether they actually moved outcomes.

### P1: In-Workflow Guidance

The most valuable insights should show up during the session, not only in dashboards. Primer should evolve from post-hoc analytics to proactive coaching and live session support.

### P1: Operational Scale and Enterprise Readiness

As usage grows, the platform needs stronger derived data pipelines, performance optimization, durable background jobs, enterprise identity, and observability.

## Near-Term Priorities

- `P0` Unify facet taxonomy and backfill existing data so success and outcome metrics are trustworthy.
- `P0` Build an effectiveness and quality attribution layer that connects workflows to code outcomes.
- `P0` Launch a true project intelligence workspace instead of hiding project insights inside other pages.
- `P0` Turn static recommendations into a measurable intervention workflow.
- `P1` Add Cursor as the next first-class captured session source, with parity checks before it participates in cross-agent analytics.
- `P1` Add workflow fingerprints, exemplar sessions, and playbooks that capture how high performers actually work.
- `P1` Bring key recommendations into the MCP sidecar and live session flow.

## Detailed Roadmap

## Measurement Integrity & Data Foundation

- [x] Facet taxonomy alignment across extraction, schemas, analytics, and UI
- [x] Outcome normalization and historical backfill for previously ingested sessions
- [x] Coverage dashboard for facet extraction, transcript completeness, GitHub sync, and repository metadata
- [x] Confidence scoring for extracted facets and downstream recommendations
- [x] Cross-agent schema parity matrix so Primer knows which session fields are required, optional, or unavailable per source
- [x] Partial-telemetry handling for IDE-native agents like Cursor so missing transcript, tool, or model fields do not distort org-wide metrics
- [ ] [P1] Execution evidence capture: lint, test, build, and verification signals per session
- [ ] [P1] Change-shape capture: files touched, diff size, churn, and rewrite/revert indicators
- [ ] [P1] Recovery-path tracking: detect whether engineers recover after friction or abandon the attempt
- [ ] [P1] Derived analytics tables and materialized rollups for heavy longitudinal queries
- [x] Source-quality dashboard by agent type, including capture coverage and telemetry completeness for Cursor
- [ ] [P2] Data-quality anomaly detection for broken ingestion, sparse transcripts, or stale integrations

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
- [ ] [P0] Cursor session ingestion and discovery pipeline
- [ ] [P0] Cursor transcript, tool-call, and model-usage extraction mapped onto the normalized session model
- [ ] [P1] Workflow fingerprinting: infer common sequences like search -> read -> edit -> test -> fix
- [ ] [P1] Cursor-specific workflow fingerprinting and session archetype mapping
- [ ] [P1] Session archetype detection: debugging, feature delivery, refactor, migration, docs, investigation
- [ ] [P1] Delegation graph capture for multi-agent and subagent workflows
- [ ] [P2] Exemplar session library for high-value workflows and onboarding examples
- [ ] [P2] Prompt, skill, and template reuse analytics by workflow and outcome

## Friction & Bottleneck Analysis

- [x] Friction type classification (permission denied, timeout, context limit, edit conflict, tool error, exec error)
- [x] Friction impact scoring (occurrence count x success rate penalty)
- [x] Friction trend chart (count + rate over time)
- [x] Project-level friction breakdown
- [x] Friction cluster analysis with sample details
- [x] Anomaly detection for friction spikes
- [x] [P0] Root-cause clustering from transcripts, tool traces, and repeated failure motifs
- [ ] [P1] Time-lost estimation per friction type, engineer, and project
- [ ] [P1] Toolchain reliability analytics for MCP servers, built-in tools, and external services
- [ ] [P1] Friction recovery analysis: what engineers tried after failure and which recoveries worked
- [ ] [P2] Real-time friction detection for in-session intervention

## Engineer Intelligence

- [x] Engineer leaderboard with multi-dimensional ranking
- [x] Personal trajectory dashboard with weekly sparklines
- [x] Strengths and friction breakdown per engineer
- [x] Peer benchmarking (percentile ranking, vs-team-average deltas)
- [x] AI-generated narrative insights per engineer
- [x] Personalized tips based on friction patterns and tool gaps
- [x] Config optimization suggestions from team benchmark comparison
- [x] Skill inventory with proficiency levels per tool
- [x] Learning paths generated from high-performer patterns
- [x] [P0] Effectiveness score: success rate, cost efficiency, quality outcomes, and follow-through
- [x] [P0] Workflow playbooks derived from high-performing peer patterns
- [ ] [P1] Plugin and tool recommendation engine based on task type, project context, and similar successful sessions
- [ ] [P1] Model selection coach for cost-appropriate model choice by task
- [ ] [P1] Personal impact review that combines trajectory, quality, cost, and workflow maturity
- [ ] [P2] Longitudinal growth view across quarters, role changes, and team moves

## Growth & Onboarding

- [x] Cohort comparison (new hire / ramping / experienced)
- [x] Time-to-team-average tracking for new hires
- [x] Onboarding velocity scoring
- [x] Onboarding recommendations
- [x] Shared behavior pattern discovery with approach comparison
- [ ] [P1] Bright spot detection: explicitly surface high performers and cross-pollinate their patterns
- [ ] [P1] Exemplar-session-to-learning-path pipeline
- [ ] [P1] Team skill gap mapping by workflow, tool category, and project context
- [ ] [P2] Coaching program measurement: which onboarding or training changes improved outcomes

## Project Intelligence

- [x] Dedicated project workspace with readiness, friction, quality, cost, and enablement views
- [x] Project AI-readiness scoring (CLAUDE.md, AGENTS.md, .claude/ detection)
- [x] Project scorecard that combines adoption, effectiveness, quality, and cost efficiency
- [x] [P0] Project-level workflow fingerprints and friction hotspots
- [ ] [P1] Project-level agent mix comparison, including Cursor sessions alongside CLI agents
- [ ] [P1] Repository context model: language mix, test maturity, repo size, and AI-enablement signals
- [x] [P1] Project enablement recommendations tied to observed bottlenecks
- [ ] [P1] Cross-project comparison: which repos are easiest or hardest to use AI effectively in
- [ ] [P2] Project playbook templates for greenfield, legacy, high-compliance, and test-poor repos

## AI Maturity

- [x] Tool leverage scoring (0-100 composite per engineer)
- [x] Tool category classification (core, search, orchestration, skill, MCP)
- [x] Orchestration adoption rate tracking
- [x] Agent and skill usage analytics (invocation patterns, delegation depth)
- [x] Tool adoption rates and trend charts
- [x] Engineer tool proficiency table
- [x] Daily leverage trend tracking
- [ ] [P1] Model diversity factor in leverage scoring
- [ ] [P1] Agent team detection for coordinated multi-agent orchestration
- [ ] [P1] Tool source classification: built-in vs marketplace vs custom
- [ ] [P1] Cross-team tooling landscape: overlap, reuse, and local best-of-breed tools
- [ ] [P2] Prompt, skill, and template maturity scoring

## Code Quality

- [x] GitHub OAuth SSO
- [x] Pull request sync via GitHub App
- [x] Commit correlation with sessions
- [x] Claude-assisted vs non-Claude PR comparison (merge rate, review comments, time to merge)
- [x] Quality by session type (debugging, feature, refactoring)
- [x] Code volume tracking (daily lines added/deleted)
- [x] Engineer quality ranking table
- [x] Repository AI-readiness scoring
- [x] Automated review findings tracker (BugBot parser, severity breakdown, fix rate)
- [x] Review findings overview in quality dashboard and engineer profile
- [x] `GET /api/v1/analytics/review-findings` endpoint with source/severity/status filters
- [x] Quality attribution layer linking session behavior to PR outcomes and review findings
- [ ] [P1] Additional review bot parsers: CodeRabbit, SonarQube, and other automated review tools
- [ ] [P1] Post-merge outcome tracking: reverts, hotfixes, and follow-up bug volume
- [ ] [P1] Change-quality analysis by workflow fingerprint and session archetype
- [ ] [P2] Review remediation tracking from finding creation to fix completion

## FinOps & Cost Management

- [x] Per-model spend tracking with daily cost chart
- [x] Cost breakdown by model
- [x] Cache efficiency analytics (hit rates, savings, per-engineer potential)
- [x] Billing mode detection (API vs subscription)
- [x] Subscription vs API cost modeling with optimal plan recommendations
- [x] 30-day cost forecasting (linear regression with confidence bands)
- [x] Budget tracking with burn-rate alerts and projected overrun warnings
- [x] Cost per successful outcome metric
- [ ] [P1] Break-even analysis for API vs seat-based pricing with per-engineer recommendations
- [ ] [P1] Cost per workflow archetype and cost per engineering outcome
- [ ] [P1] Model-choice opportunity scoring for overspend reduction
- [ ] [P2] Budget policy simulation by team, project, and billing model

## AI Synthesis & Explorer

- [x] AI-generated narrative reports (engineer, team, org scope)
- [x] Narrative caching with TTL-based expiry
- [x] Auto-refresh via lifespan task
- [x] Conversational data explorer (SSE-streamed tool-use chat)
- [x] AI-powered recommendations panel
- [ ] [P1] Saved explorer prompts and reusable report cards
- [ ] [P1] Compare mode for engineer, team, project, and time-period analysis
- [ ] [P2] Weekly manager review packs that combine quality, friction, growth, and cost
- [ ] [P2] Recommendation narratives that explain why a workflow is likely to help

## Interventions & Experimentation

- [x] [P0] Recommendation-to-intervention workflow with owner, status, due date, and linked evidence
- [x] [P0] Before-and-after measurement for coaching, tooling, or repo changes
- [ ] [P1] Experimentation layer for training rollouts, tool changes, and enablement playbooks
- [x] [P1] Intervention effectiveness reporting by team, project, and engineer cohort
- [ ] [P2] Auto-generated next-step plans from alerts, narratives, and project findings

## Real-Time Engineer Experience

- [x] MCP sidecar with on-demand stats, friction reports, and recommendations
- [ ] [P0] Proactive coaching skill that activates at session start with contextual suggestions
- [ ] [P0] Live session signals that stream friction, satisfaction, and risk as work happens
- [ ] [P1] In-session workflow nudges based on project playbooks and prior failures
- [ ] [P1] Daily and weekly personal recaps inside the sidecar
- [ ] [P2] Lightweight session planning prompts before complex work begins

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
- [ ] [P1] Activation and setup hub for GitHub, budgets, alerts, narrative readiness, and data freshness
- [ ] [P1] Performance measurement views for leadership across productivity, quality, cost, and adoption
- [ ] [P1] Threshold resolution and policy management that matches actual alerting behavior
- [ ] [P2] Multi-tenant workspace isolation for multiple organizations on a shared Primer instance
- [ ] [P2] Enterprise IdP support with SAML and OIDC for provisioning and SSO

## Platform & Infrastructure

- [x] Multi-agent support (Claude Code, Codex CLI, Gemini CLI)
- [x] SessionEnd hook system with agent-specific installers
- [x] `primer sync --watch` for agents without hook systems
- [x] Docker Compose and Kubernetes Helm deployment
- [x] PostgreSQL and SQLite support
- [x] Alembic migration bundling in pip package
- [ ] [P0] Cursor `agent_type` support across capture, sync, ingest, and analytics filters
- [ ] [P0] Durable background job system for sync, facet extraction, narratives, and alerts
- [ ] [P0] Scalable API key lookup and verification strategy
- [ ] [P1] Source-capability registry so Primer can safely gate analytics by what each agent source actually provides
- [ ] [P1] OpenTelemetry integration for metrics, traces, and logs
- [ ] [P1] Redis-backed caching for analytics query results and high-read metadata
- [ ] [P1] Analytics performance work for large orgs and concurrent dashboard usage
- [ ] [P2] Pluggable warehouse export for long-horizon analysis in external BI tools
