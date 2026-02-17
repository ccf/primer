# Primer Roadmap

## Tier 1 — Core Dashboard (Complete)

- [x] Session search with full-text, outcome, type, model filters
- [x] Transcript viewer with message-level detail
- [x] Custom date range picker (7d/30d/90d/1y presets + custom)
- [x] Team dashboard with member stats
- [x] Daily activity chart
- [x] Tool ranking chart
- [x] Model usage chart
- [x] Outcome and session type distribution
- [x] Cost analysis (daily cost chart, model cost breakdown)
- [x] Activity heatmap (day-of-week x hour)
- [x] Dark mode with system preference detection
- [x] Deep links for sessions, teams
- [x] Previous-period comparison deltas on KPI cards

## Tier 2 — Engineering Leadership (Complete)

- [x] ROI / Productivity metrics (time saved, value created, adoption rate, power users)
- [x] Peer benchmarking (percentile ranking, vs-team-avg deltas, radar chart)
- [x] Anomaly detection (friction spikes, usage drops, cost spikes, success rate drops)
- [x] Alert system with acknowledge/dismiss workflow
- [x] Admin panel (engineer management, team management, audit log, system stats)
- [x] Engineer activation/deactivation
- [x] API key rotation

## Tier 3 — Enterprise Features (Complete)

- [x] GitHub OAuth SSO for dashboard access
- [x] Role-based access control (engineer, team_lead, admin)
- [x] Exportable reports (CSV)
- [x] Custom alert thresholds configuration
- [x] Audit trail for admin actions
- [x] API rate limiting
- [x] Scheduled alert digests (email/Slack)
- [ ] Multi-tenant workspace isolation
- [x] PDF export

## Tier 4 — Future Ideas

- [x] **Config optimization** — auto-suggest hooks/skills from repeated patterns
- [x] **Personalized tips** — "You use X but rarely Y; here's when Y helps"
- [x] **Learning paths** — identify knowledge gaps from session patterns
- [x] **Pattern sharing** — "3 engineers solved similar problems; best approach"
- [x] **Bottleneck detection** — common friction points across team
- [x] **Onboarding acceleration** — compare new hire vs experienced patterns
- [x] **Skill inventory** — team capabilities from session topics
- [x] **Tool adoption tracking** — which Claude Code features are/aren't used
- [x] **Quality metrics** — correlate session outcomes with code quality via git

## Tier 5 — Personal Engineer Experience (Complete)

- [x] **Engineer profile page** — personal trajectory dashboard with weekly sparklines, friction breakdown, strengths/skills, and quality tabs (`/engineers/:id`)
- [x] **Similar sessions** — contextual pattern sharing panel on session detail with 3-tier relevance matching
- [x] **Claude vs non-Claude PR comparison** — side-by-side metrics for Claude-assisted vs other PRs (stub awaiting PR models)
- [x] **Time-to-team-average** — ramp-up tracking for new hires with rolling success rates vs team average

## Tier 6 — AI DevEx Maturity

- [x] **Tool classification & leverage scoring** — categorize tool usage into tiers (core, extended, orchestration, MCP) and score engineers on a leverage spectrum from basic to advanced
- [x] **Enhanced tool metadata extraction** — capture subagent types from Task calls, skill names from Skill calls, and MCP tool origins from transcripts
- [x] **Project AI-readiness scoring** — detect CLAUDE.md, AGENTS.md, .claude/ config presence in repos; score project-level AI alignment
- [ ] **Agent & skill usage analytics** — track built-in vs custom/marketplace agent usage, skill invocation patterns, and delegation depth
- [ ] **Cache efficiency dashboard** — surface cache hit ratios, cost savings from caching, and model-specific cache strategies from existing token data

## Tier 7 — Tooling Landscape & Performance

- [ ] **Tool source classification** — distinguish built-in vs marketplace vs custom tools/agents/skills; identify which MCP servers tools originate from
- [ ] **Cross-team tooling landscape** — analyze overlap/reuse of custom tools, agents, skills, and MCP servers across teams; highlight unique vs shared tooling
- [ ] **Bright spot detection** — surface high-performing engineers and effective patterns to cross-pollinate across teams
- [ ] **Performance measurement views** — leadership-oriented scorecards combining productivity, quality, cost efficiency, and adoption metrics per engineer
- [ ] **Claude vs non-Claude PR comparison** — activate the existing stub with real PR data; side-by-side metrics for AI-assisted vs unassisted pull requests
- [ ] **GitHub integration setup** — connect to real GitHub repos for PR data, avatars, repository metadata, and AI-readiness scoring
