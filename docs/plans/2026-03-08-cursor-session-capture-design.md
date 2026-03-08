# Cursor Session Capture Design

**Goal:** Add Cursor as the next first-class captured session source in Primer without polluting existing cross-agent analytics with lower-fidelity or differently shaped telemetry.

## Why This Matters

Primer already captures `Claude Code`, `Codex CLI`, and `Gemini CLI` sessions, but a growing share of agentic engineering work happens inside IDE-native agents. If Cursor sessions are not captured, org-level analytics are incomplete and can systematically undercount adoption, friction, and tool usage for teams that prefer IDE workflows.

The risk is not just missing data. Cursor may expose a different telemetry shape from CLI agents:

- transcript availability may differ
- tool-call visibility may be partial
- model-usage details may be incomplete
- session boundaries may be inferred differently
- agent actions may blend chat, edits, and background automation

Primer therefore needs a parity-first rollout, not just a new extractor.

## Scope

This design is intentionally limited to `session capture`.

In scope:

- discovering Cursor sessions locally or via an export/integration path
- mapping Cursor sessions into Primer's normalized session model
- tagging Cursor as a first-class `agent_type`
- handling partial telemetry safely
- exposing capture completeness and source quality in measurement-integrity tooling

Out of scope for this phase:

- Cursor PR/review bot intelligence
- IDE UI integrations
- real-time Cursor coaching
- deep Cursor-specific workflow recommendations

## Design Principles

1. **Do not mix incomparable data silently**
   Cursor sessions should not affect org-wide metrics unless required fields for that metric are present.

2. **Capture first, compare second**
   The first milestone is trustworthy ingestion and observability, not polished downstream analytics.

3. **Source capability must be explicit**
   Primer should know which fields are available per source and which analytics are safe to compute.

4. **Degrade gracefully**
   If Cursor lacks a field that CLI agents provide, Primer should mark that metric unavailable rather than inventing or over-inferring it.

## Proposed Rollout

### Phase 1: Source Parity and Ingestion

- Add `cursor` as a new `agent_type`
- Build a Cursor discovery and extraction path
- Map available fields into the normalized `Session`, `SessionMessage`, `ToolUsage`, `ModelUsage`, and `SessionFacets` structures
- Add source-quality metrics so the system can report telemetry completeness by agent type

### Phase 2: Safe Analytics Participation

- Define a source-capability registry
- Gate analytics by required field availability
- Include Cursor in session counts, project mix, and other metrics only when those metrics are supported by its telemetry
- Keep source-specific confidence visible in admin and recommendation layers

### Phase 3: Cursor-Specific Insight Expansion

- Cursor-specific workflow fingerprints
- IDE-native archetype detection
- comparison of Cursor vs CLI usage patterns by team and project

## Data Model and Analytics Implications

Cursor support likely needs more than a new extractor class. Primer should explicitly model per-source capability and completeness.

Recommended additions:

- `agent_type = "cursor"` in session and daily stats models
- a source-capability registry in backend code or config
- measurement-integrity stats broken down by `agent_type`
- partial-telemetry safeguards for:
  - missing transcript content
  - missing tool-call traces
  - missing model usage
  - inferred rather than explicit session boundaries

## Roadmap Implications

This design maps directly to roadmap items in:

- `Measurement Integrity & Data Foundation`
- `Session Intelligence`
- `Project Intelligence`
- `Platform & Infrastructure`

The key roadmap message is:

> Cursor should be treated as the next first-class session source, but only after Primer can measure source parity and telemetry completeness well enough to keep downstream analytics trustworthy.

## Success Criteria

The Cursor capture effort is successful when:

- Cursor sessions ingest into Primer under a first-class `agent_type`
- admins can see Cursor capture coverage and telemetry completeness
- unsupported metrics are gated rather than silently computed from missing data
- project and org views can include Cursor sessions without degrading trust in the numbers

## Open Questions

- What is the most reliable Cursor session source: local files, extension APIs, exported logs, or another integration path?
- How explicit are Cursor session boundaries compared with CLI sessions?
- What tool/model telemetry is actually available versus inferred?
- Should some Cursor interactions be modeled as sessions, or as a different activity type entirely?
