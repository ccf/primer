# Product Flow

Primer is no longer a passive analytics dashboard. It is a closed-loop harness intelligence
product for agentic engineering teams:

1. Capture what happened in AI-assisted work.
2. Normalize it into trustworthy workflow, quality, cost, and customization semantics.
3. Prove which patterns are working and where they break down.
4. Coach engineers and teams toward better defaults.
5. Turn recommendations into interventions and experiments.
6. Measure whether those changes improved outcomes.

This document is the product-facing companion to the lower-level
[architecture guide](architecture.md). It answers: "How is Primer supposed to come together as a
user experience?"

## Core Loop

```text
Capture
  Claude / Codex / Gemini / Cursor sessions
  GitHub PRs, review findings, repository readiness
  tool usage, delegation, customizations, execution evidence

Normalize
  session facets
  workflow fingerprints and archetypes
  friction clusters and recovery paths
  quality, cost, and post-merge outcome attribution

Prove
  quality outcomes
  cost per success
  workflow compare mode
  post-merge stability

Coach
  playbooks and exemplars
  project playbook templates
  session-start coaching
  live session signals and nudges

Act
  interventions
  experiments
  coaching programs
  next-step plans

Measure
  before/after baselines
  manager review packs
  leadership performance views
  adoption, cost, quality, and friction changes
```

## Product Surfaces

### My Profile

Primary question: "How am I doing, and what should I change next?"

- overview, effectiveness, trajectory, and friction
- strengths, model/tool recommendations, and workflow playbooks
- personal impact review
- quality and cost context tied back to the engineer

### Sessions

Primary question: "What actually happened in this piece of work?"

- searchable session list
- transcript, tool/model usage, and workflow profile detail
- similar sessions and exemplar evidence
- session-level health, change shape, recovery path, and delegation graph

### Projects

Primary question: "How well does this repo support AI-assisted engineering?"

- readiness and repository context
- workflow fingerprints and friction hotspots
- project-scoped quality, cost, and effectiveness
- enablement recommendations and project playbook templates

### Growth

Primary question: "What good patterns should people copy?"

- bright spots, exemplars, and reusable assets
- learning paths and team skill gaps
- onboarding and coaching-program measurement

### AI Maturity

Primary question: "Which tools, customizations, and agent stacks actually matter?"

- leverage and effectiveness
- customization state, provenance, and outcome attribution
- high-performer stacks and delegation / agent-team patterns
- toolchain reliability

### Code Quality

Primary question: "Which workflows produce code that holds up?"

- PR merge and review metrics
- workflow-based quality attribution
- review findings and post-merge outcomes
- recent PRs and stabilization work

### FinOps

Primary question: "Where are we spending efficiently, and where are we wasting money?"

- cost by workflow and outcome
- compare mode for workflow economics
- model-choice opportunities and cost modeling
- budgets and forecasting

### Compare

Primary question: "What changed across teams, projects, engineers, or time periods?"

- before/after comparisons
- cohort and project comparison
- workflow, quality, cost, and maturity comparisons in one place

### Interventions

Primary question: "What are we changing, and did it work?"

- recommendation-to-intervention conversion
- owner, status, due date, and linked evidence
- baseline and follow-up measurement
- next-step plans and coaching program measurement

### Admin

Primary question: "Is the platform ready, trustworthy, and operating correctly?"

- activation and setup hub
- threshold and alert policy management
- leadership performance views
- system integrity and measurement coverage

### MCP Sidecar

Primary question: "What should I know right now while I work?"

- on-demand stats and friction summaries
- session-start coaching
- live session signals and in-session nudges
- personal recaps and manager review packs

## User-to-Surface Mapping

| User | Starts Here | Then Goes To | Why |
| --- | --- | --- | --- |
| Engineer | Profile or MCP sidecar | Sessions, Growth, Interventions | improve personal workflow and reinforce better habits during work |
| Team lead | Growth, Compare, or Quality | Projects, Interventions, manager review pack | spread strong patterns and remove repeat team bottlenecks |
| Platform/admin | Admin or Projects | Maturity, Interventions, Quality, FinOps | improve systemic enablement and guardrails |
| Leadership | Admin performance views or Compare | Quality, FinOps, Growth | decide where AI is compounding output and where it needs intervention |

## Design Implications

- Primer should always answer a decision question, not just show another chart.
- Every major page should expose at least one next action or next experiment.
- The same concept should not live in multiple places with different meanings.
- Workflow proof should connect quality, cost, and stability instead of splitting those into
  separate narratives.
- Project intelligence should lead naturally into interventions, templates, and coaching.
- Sidecar guidance should point back to the same exemplars, playbooks, and project templates shown
  in the app.

## Current UX Gaps To Watch

- Profile and Growth still overlap in ways that are easy to confuse.
- Playbooks, exemplars, reusable assets, and learning paths still need clearer differentiation.
- Project workspace, Compare, and Interventions should feel more obviously connected.
- Leadership and admin workflows are stronger now, but they still need a tighter single narrative
  for "what needs attention this week."
