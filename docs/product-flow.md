# Product Flow

Primer is no longer just a session dashboard. It is a closed-loop intelligence product:

1. Capture what happened in agent-assisted work.
2. Normalize it into trustworthy workflow and outcome semantics.
3. Surface the right view for the user who needs to act.
4. Turn recommendations into interventions.
5. Measure whether those interventions improved outcomes.

This document is the product-facing companion to the lower-level [architecture guide](architecture.md). It answers: "How is Primer supposed to come together as a user experience?"

## Core Loop

```text
Capture
  Claude / Codex / Gemini / Cursor sessions
  GitHub PRs, review findings, repository readiness

Normalize
  session facets
  workflow fingerprints
  friction clusters
  effectiveness + quality attribution

Surface
  Profile
  Sessions
  Projects
  Growth
  Interventions
  MCP sidecar

Act
  recommendations
  playbooks
  project enablement suggestions
  interventions

Measure
  before/after baselines
  effectiveness score
  quality outcomes
  friction changes
  cost changes
```

## Product Surfaces

### My Profile

Primary question: "How am I doing, and how can I improve?"

- Overview: personal effectiveness, trends, friction, recommendations
- Sessions: inspect specific work and transcripts
- Insights: strengths, quality, cost, and trajectory
- Growth: learning paths and workflow playbooks derived from peers

### Sessions

Primary question: "What actually happened in this piece of work?"

- searchable session list
- transcript and tool/model detail
- similar sessions
- session-level facets and health

### Projects

Primary question: "How well does this repo support AI-assisted engineering?"

- readiness and repository context
- workflow fingerprints and friction hotspots
- project-scoped quality, cost, and effectiveness
- enablement recommendations tied to observed bottlenecks

### Growth

Primary question: "What good patterns should people copy?"

- onboarding velocity
- shared patterns
- skills coverage
- workflow playbooks

### Interventions

Primary question: "What are we changing, and did it work?"

- recommendation-to-intervention conversion
- owner, status, due date, evidence
- baseline and follow-up measurement

### MCP Sidecar

Primary question: "What should I know right now while I work?"

- on-demand stats
- friction summaries
- recommendations
- eventually proactive coaching and live signals

## User-to-Surface Mapping

| User | Starts Here | Then Goes To | Why |
| --- | --- | --- | --- |
| Engineer | Profile | Sessions, Growth, MCP | improve personal workflow |
| Team lead | Dashboard or Growth | Projects, Interventions | spot patterns and coach the team |
| Platform/admin | Projects or Admin | Interventions, Growth | remove systemic blockers and improve enablement |

## Design Implications

- Primer should always answer a decision question, not just show another chart.
- Every major page should expose at least one next action.
- The same concept should not live in multiple places with different meanings.
- Growth concepts should be visible from the Growth area, not only from hidden profile tabs.
- Project intelligence should lead naturally into interventions.

## Current UX Gaps To Watch

- Profile and Growth still overlap in ways that are easy to confuse.
- Playbooks, patterns, and learning paths need clearer differentiation.
- Project enablement and intervention flows should become more obviously connected.
- The sidecar experience still needs a formal "during the session" journey.
