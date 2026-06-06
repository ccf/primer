# Project Hive-Mind Memory System — Design Spec v2

**Status:** Draft for review (revised after adversarial review: 23 confirmed findings integrated)
**Date:** 2026-05-18
**Supersedes:** `2026-05-18-memory-system-design.md` (v1, auto-PR-primary design)
**Roadmap link:** ROADMAP.md `P1 Background 'Dream' Worker` + `P1 Dynamic MCP Context Injection` + `P2 Primer Auto-Docs` + `P2 Epistemic Explorer`

## 1. Summary

Primer adds a **shared, project-scoped memory layer** — a hive mind. As different engineers work on a project, their agent sessions (Claude Code, Codex, Gemini, Cursor) feed one memory space scoped by project. Agents read relevant memories at session start (token-budgeted) and on demand; sessions write candidate memories passively (extraction from telemetry) and explicitly (a rate-limited `remember` tool). A periodic **consolidation engine** merges, validates, judges, and promotes candidates; a **measurement loop** tracks corroboration, usage, and outcome signals per memory. The highest-confidence validated memories **crystallize** into `AGENTS.md` via pull requests — the zero-install distribution channel.

The memory store is the source of truth. PRs, MCP injection, and the dashboard are surfaces over it.

**Staging.** This spec defines two stages:
- **v1.0** — the core loop on single-project scope: capture → consolidate → inject → measure (observational) → crystallize.
- **v1.1** — cross-project affinity groups, scope promotion, and randomized withholding experiments (causal measurement). These are designed here (decisions are settled) but sequenced after the core loop ships and has data.

**Claims discipline.** v1.0 measurement is observational. Every surfaced lift number is labeled *observational* in the dashboard, PR bodies, and FinOps views; injection token *cost* is measured exactly; the causal upgrade (withholding) arrives in v1.1. The system never presents an observational estimate as a causal claim.

**Hard gate.** The P0 redaction pipeline must land before any memory capture runs: sketches persist transcript-derived text, so even quarantined capture requires redaction. Until then `MEMORY_ENABLED` refuses to activate (see §16).

### Why this wins (strategic context)

- **The gap:** No vendor-neutral, cross-harness, team/project-scoped memory system validates individual memories against independently measured engineering outcomes. Dedicated memory platforms (Mem0, Zep, Letta, Honcho, Hindsight, Cognee, Supermemory) benchmark conversational recall and scope to individuals; team scope, where present, is a namespace convention.
- **The benchmark to beat:** GitHub Copilot agentic memory (preview, Jan 2026) is repo-scoped, team-shared, citation-validated, usage-decaying, and claims ~7-point PR merge-rate lift — but is locked to Copilot surfaces and GitHub repos. Primer's cross-harness coverage is structurally unavailable to platform vendors. Notably, Copilot's per-memory validation is citation-against-codebase plus usage decay — not per-memory causal lift either; Primer's v1.0 matches that bar honestly and v1.1's experiments exceed it.
- **The cautionary tale:** Cursor shipped learned project memory and removed it (v2.1.x) over quality/noise. Bad shared memory is worse than none. Primer's outcome gate + two-tier trust model is the direct answer.
- **The honest claim:** Controlled benchmarks show memory's proven value in coding agents is token/turn efficiency (15–28% cost reduction, 28–40% fewer turns on complex tasks), not code quality. Primer measures injection cost exactly and reports efficiency estimates with explicit methodology labels.
- **Primer's durable advantage:** an authenticated server of record (real identity via `AuthContext`, project scoping via `GitRepository`, central API) plus an existing multi-harness outcome dataset. The closest OSS competitor (agentmemory) has strong individual-scale primitives but ambient env-var identity, manual point-in-time sharing, last-write-wins merge, and no read ACLs — exactly the gaps Primer's existing infrastructure closes.

## 2. Scoping decisions (from brainstorming)

Decisions carried forward from v1:

| Decision | Choice |
|---|---|
| Layer | Project-level (v1.1 adds affinity groups; org scope later) |
| Content | Hybrid — statistical patterns + LLM-extracted facts, each validated against the other |
| Consolidation cadence | Periodic (≈daily interval), dirty-scope filtering |
| Quality gate | LLM judge over hybrid evidence (no fixed thresholds) |
| Lifecycle | Rejection-aware (sticky) + decay |
| Closed loop | Outcome measurement per memory (observational v1.0 → causal v1.1) |

New decisions from the pivot:

| Decision | Choice | Stage | Rationale |
|---|---|---|---|
| Source of truth | The memory store (server-side), not repo files | v1.0 | Repo files become an export surface; the store carries trust state, provenance, and measurement |
| Write path | Passive extraction (backbone) + explicit `remember` MCP tool (rate-limited) | v1.0 | Explicit signal is evidence extraction can't synthesize; quarantine makes it safe |
| Trust model | Two-tier: `sketch` (quarantined) → `active` (injectable) → `validated` (export-eligible) | v1.0 | Live multi-writer input must never reach agents' context at full trust |
| Cross-project scope | Auto-detected affinity groups with visible guardrails | v1.1 | Affinity widens retrieval, never claims authority; not on the core loop's critical path, so sequenced after it |
| Outcome attribution | Staged: observational continuously, randomized withholding at decision boundaries | observational v1.0, withholding v1.1 | Experiments need volume to be powered; v1.0 builds the data, v1.1 runs the experiments |
| Circular-evidence fix | Engineer-level exposure horizon: an engineer who received memory X (or a near-duplicate) within the horizon cannot independently corroborate X | v1.0 | Session-level exclusion alone misses internalization across sessions |
| PR surface | Minimal crystallization: `validated` memories only → `AGENTS.md`, weekly/on-demand batch | v1.0 | The zero-install distribution channel and growth loop |
| Attribution display | Anonymized by default, per-engineer opt-in visibility; full internal provenance, role-gated audit | v1.0 | Capture must never feel like exposure |
| Cold start | One-time backfill extraction over the existing session corpus on enablement | v1.0 | The product must be useful in week one; backfill machinery (facet-backfill pattern) already exists |

## 3. Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                       Primer monolith (FastAPI)                        │
│                                                                        │
│  WRITE PATH                                                            │
│  ┌──────────────────────────┐    ┌───────────────────────────────┐    │
│  │ Session ingest (existing) │    │ MCP `primer_remember` tool    │    │
│  │ SessionEnd + PreCompact   │    │ (rate-limited in handler)     │    │
│  └────────────┬──────────────┘    └──────────────┬────────────────┘    │
│               ▼                                   ▼                    │
│     background job: memory                POST /memories/remember      │
│     candidate extraction (LLM)                    │                    │
│     + one-time backfill job                       │                    │
│               └───────────────┬───────────────────┘                    │
│                               ▼                                        │
│                    ┌────────────────────┐                              │
│                    │  SKETCH tier       │  quarantined, never injected │
│                    └─────────┬──────────┘                              │
│                              │                                         │
│  CONSOLIDATION ENGINE (recurring job, ~24h interval, dirty-scope)      │
│  ┌───────────────────────────▼──────────────────────────────────┐     │
│  │ 1. Cluster + merge near-duplicate sketches/evidence          │     │
│  │ 2. Compute corroboration + outcome stats                     │     │
│  │    (engineer-level exposure exclusion)                       │     │
│  │ 3. LLM judge gate (sketch → active promotion)                │     │
│  │ 4. Decay scoring on active/validated entries                 │     │
│  │ 5. Rebuild retrieval indexes (keyword + vector where avail.) │     │
│  │ [v1.1: scope promotion + affinity update]                    │     │
│  └───────────────────────────┬──────────────────────────────────┘     │
│                              ▼                                        │
│                    ┌────────────────────┐                              │
│                    │  ACTIVE tier       │  injectable                  │
│                    └─────────┬──────────┘                              │
│                              │ post-activation measurement             │
│                              ▼ (observational; v1.1 adds withholding)  │
│                    ┌────────────────────┐                              │
│                    │  VALIDATED tier    │  export-eligible             │
│                    └─────────┬──────────┘                              │
│                              │                                         │
│  READ PATH                   │          EXPORT PATH                    │
│  ┌──────────────────────┐    │    ┌────────────────────────────┐      │
│  │ MCP session start:   │◀───┤    │ Crystallization PRs:       │      │
│  │ token-budgeted bundle│    └───▶│ validated → AGENTS.md      │      │
│  │ MCP `primer_recall`  │         │ (weekly batch / on-demand) │      │
│  └──────────┬───────────┘         └────────────────────────────┘      │
│             ▼                                                          │
│   memory_injection log (per serve: memory_id × session_id)             │
│   → feeds usage, exposure horizon, and (v1.1) experiments              │
└────────────────────────────────────────────────────────────────────────┘
```

Reuses (verified against current code):
- `src/primer/mcp/` — `session_start_coaching`, `live_session_signals`, `in_session_nudges` are the read-surface skeleton
- `src/primer/hook/` — SessionEnd + PreCompact incremental capture is the passive write path
- `facet_extraction_service.py` — LLM extraction pattern, including its backfill job pattern (`JOB_TYPE_FACET_BACKFILL`) reused for cold-start
- `background_job_service.py` — async job queue; recurring jobs via `ensure_recurring_jobs` (interval-since-last-run semantics — see §7 scheduling note)
- `NarrativeCache` pattern — caching assembled per-scope bundles with TTL
- `AuthContext` (`server/deps.py`) — authenticated identity for writer attribution
- `github_service.py` — **App-auth token plumbing only** (`_generate_app_jwt` / `_get_installation_token`). Note: the service is currently read-only and `webhooks.py` is inbound-only; the GitHub *write* client (branches, file contents, PR creation) is net-new work (§16)

Borrowed from agentmemory (with adaptation):
- The structured memory-card schema (`title`, `body`, `concepts`, `files`, `confidence`) — with repo-relative path normalization (their live instance leaks machine-specific absolute paths)
- Hybrid retrieval under an explicit token budget; per-session result diversification
- Auto-derived project profiles (top concepts, conventions, common errors) as a dashboard artifact
- Tier-promotion vocabulary, simplified to sketch → active → validated

## 4. Data model

Five tables. UUID string PKs, server-side timestamps, per Primer conventions.

### `memory_scope`

The unit memory belongs to. Every repository gets a project scope automatically at first ingest. In v1.0 only `kind=project` is created; the enum reserves `group`/`org` for v1.1 so the FK shape doesn't churn.

| Field | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | |
| `kind` | Enum | `project` (v1.0) / `group`, `org` (reserved, v1.1) |
| `name` | String | display name |
| `repository_id` | FK → `git_repositories.id`, nullable | set for `kind=project` |
| `last_consolidation_at` | DateTime, nullable | dirty-tracking |
| `memory_paused_at` | DateTime, nullable | non-null disables all memory activity |
| `created_at`, `updated_at` | DateTime | |

*(v1.1 adds `memory_scope_member` for affinity groups: scope_id, repository_id, source auto/manual, affinity_score, affinity_signals, severed_at. Severed pairs are never re-added; groupings are dashboard-visible with contributing signals. Defined here so v1.1 is a migration, not a redesign.)*

### `memory_entry`

| Field | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | |
| `scope_id` | FK → `memory_scope.id` | |
| `kind` | Enum | `project_fact` / `anti_pattern` / `tool_pointer` / `harness_config` / `procedure` |
| `title` | String(200) | memory-card headline |
| `body` | Text | the text agents receive |
| `concepts` | JSON | topic tags |
| `files` | JSON | repo-relative paths (normalized at write time) |
| `content_hash` | String(64) | sha256 of canonicalized `body` |
| `status` | Enum | `sketch` / `active` / `validated` / `decaying` / `retired` / `rejected` |
| `confidence_score` | Float | recomputed each consolidation |
| `corroboration_count` | Integer | distinct engineers with independent evidence (see exposure horizon, §8) |
| `embedding` | `Vector(1024)`, **nullable** | present only on postgres+pgvector deployments (§6 retrieval modes) |
| `judge_critique` | Text, nullable | |
| `origin` | Enum | `passive_extraction` / `remember_tool` / `consolidation_merge` (v1.1 adds `scope_promotion`) |
| `created_by_engineer_id` | FK → `engineers.id`, nullable | internal provenance |
| `activated_at` | DateTime, nullable | when entry became injectable; reset on rehabilitation |
| `activation_baseline` | JSON, nullable | outcome + token stats snapshot at (re)activation |
| `activation_observation` | JSON, nullable | post-activation measurement payload (labeled observational) |
| `validated_at` | DateTime, nullable | |
| `token_cost` | JSON, nullable | `{avg_tokens_injected, n_injections, retrieval_rate}` — measured exactly |
| `efficiency_estimate` | JSON, nullable | `{est_turns_delta, est_tokens_delta, n, method: "observational"}` — diagnostic, labeled |
| `export_status` | Enum | `none` / `pr_open` / `exported` / `export_kept` / `removal_pr_open` / `removed` |
| `export_pr_number` | Integer, nullable | |
| `export_cooldown_until` | DateTime, nullable | set when an export PR is declined; entry skipped by export batches until then |
| `superseded_by_id` | FK self, nullable | |
| `created_at`, `updated_at` | DateTime | |

*(v1.1 adds `experiment_state` JSON and `promoted_from_id` for withholding experiments and scope promotion.)*

Constraints / indexes: `UNIQUE(scope_id, content_hash)`; index on `(scope_id, status)`; HNSW index on `embedding` (postgres only).

**Status semantics:**
- `sketch` — quarantined; never injected; awaiting consolidation
- `active` — passed judge + corroboration bar; served by the read path
- `validated` — met the post-activation validation criteria (§8); export-eligible
- `decaying` — decay trigger fired; demoted out of injection bundles; next consolidations either rehabilitate or retire
- **Rehabilitation back-edge (explicit):** a `decaying` entry that recovers returns to `active` — not directly to `validated` — and must re-earn validation. Rehabilitation re-snapshots `activation_baseline`, resets `activated_at = now` (restarting the §8 measurement window), and clears `validated_at`. A previously exported entry remains in the file while it re-earns status; rehabilitation alone never re-triggers export.
- `retired` — terminal (decayed out for `MEMORY_DECAY_GRACE_PASSES` consecutive passes, or manually retired); re-proposal only via manual un-retire
- `rejected` — judge-rejected sketch or human-rejected entry; **sticky** — blocks re-proposal of same/similar content until manually retired

**Export status transitions (complete):**
- `none → pr_open` (crystallization PR opened) → `exported` (PR merged) or `none` + `export_cooldown_until` set + confidence penalty (PR closed unmerged — event `export_pr_declined`)
- `exported → removal_pr_open` (entry retired; removal PR opened — event `removal_pr_opened`) → `removed` (removal PR merged — event `removal_pr_merged`; terminal) or `export_kept` (removal PR closed unmerged — event `removal_pr_closed`; the humans chose to keep the lines; consolidation never re-proposes removal for an `export_kept` entry — preserves v1's anti-thrashing `merged_protected` semantics)
- Human deletes an exported bullet from the file → event `export_bullet_deleted`; `export_status=none`; entry `status=rejected` (sticky — the team said no)
- Human edits an exported bullet → event `human_edited`; Primer stops re-rendering that entry (the human version owns the file lines; the store entry continues its measurement lifecycle)

### `memory_evidence`

| Field | Type | Notes |
|---|---|---|
| `id` | PK | |
| `memory_id` | FK → `memory_entry.id`, cascade | |
| `evidence_kind` | Enum | `outcome_lift_stat` / `transcript_citation` / `friction_pattern` / `tool_correlation` / `explicit_remember` |
| `session_id` | FK → `sessions.id`, nullable | |
| `engineer_id` | FK → `engineers.id`, nullable | internal writer identity |
| `independent` | Boolean | false if the writing **engineer** was exposed to this entry (or a near-duplicate) within the exposure horizon — not merely the source session (§8) |
| `payload` | JSON | shape varies by kind |
| `created_at` | DateTime | |

Index on `memory_id`; index on `(memory_id, independent)`.

### `memory_injection`

One row per memory served to a session. The join table for usage accounting, the exposure horizon, and (v1.1) experiments.

| Field | Type | Notes |
|---|---|---|
| `id` | PK | |
| `memory_id` | FK → `memory_entry.id` | |
| `session_id` | FK → `sessions.id` | |
| `engineer_id` | FK → `engineers.id` | denormalized for exposure-horizon queries |
| `surface` | Enum | `session_start` / `recall` / `nudge` |
| `token_count` | Integer | tokens contributed to the bundle |
| `injected_at` | DateTime | |

Index on `(memory_id, injected_at)`; index on `(engineer_id, injected_at)`; index on `session_id`. *(v1.1 adds `withheld` Boolean for experiments.)*

### `memory_event`

Append-only audit trail. Event kinds: `sketch_created` / `merged_into` / `promoted_to_active` / `judge_rejected` / `decay_started` / `rehabilitated` / `retired` / `validation_confirmed` / `validation_failed` / `export_pr_opened` / `export_pr_merged` / `export_pr_declined` / `removal_pr_opened` / `removal_pr_merged` / `removal_pr_closed` / `export_bullet_deleted` / `human_edited` / `visibility_opt_in` *(v1.1 adds: `experiment_started` / `experiment_completed` / `scope_promoted`)*. Fields: `id`, `memory_id`, `event_kind`, `occurred_at`, `actor`, `payload`.

## 5. Write path

### Passive extraction (the backbone)

After facet extraction completes for a session (existing background job), enqueue `memory_candidate_extraction`:

1. **Pre-filter gate**: extraction runs only on sessions with extraction-worthy substance (e.g., ≥ N tool calls or friction events or commits — threshold configurable). Empty and trivial sessions (common in real corpora — the agentmemory live instance showed most sessions with zero observations) are skipped; this is the primary cost control.
2. Input: session transcript (redacted), facets, execution evidence, change shape, recovery path
3. LLM extracts 0–5 candidate memory cards (`title`, `body`, `kind`, `concepts`, `files`, citations) using the existing haiku-tier facet-extraction model (`settings.facet_extraction_model`)
4. Repo-relative path normalization on `files`; engineer-identity scrub on `body`
5. Persist as `status=sketch` with `transcript_citation` evidence rows
6. Dedup: near-duplicate `active`/`validated` entry exists → attach the citation as new evidence to that entry (evidence accretion) instead of creating a sketch; `rejected` near-duplicate exists → drop silently

### Cold-start backfill (day-one behavior)

When memory is enabled for a scope (or at first ingest thereafter), enqueue a one-time `memory_backfill` job: run the identical per-session extractor over the scope's existing session corpus, newest-first, bounded by `MEMORY_BACKFILL_MAX_SESSIONS` (default 200) and the daily LLM budget. This mirrors the existing `JOB_TYPE_FACET_BACKFILL` pattern (`background_job_service.py`, `facet_extraction_service.backfill_facets`). Backfilled sketches carry genuine multi-writer corroboration immediately, so the first consolidation pass can promote a useful starter set — the product is alive in week one, not week four. Backfill respects the same pre-filter gate and budget caps; backfill-derived entries get `activation_baseline` snapshots at promotion like any other entry.

### Explicit `remember` (the high-signal channel)

New MCP tool `primer_remember(text, kind?, files?)`:
- POSTs to `POST /api/v1/memories/remember` with the engineer's auth
- Server creates a `sketch` with `origin=remember_tool` and an `explicit_remember` evidence row — explicit intent is itself evidence, weighted in `confidence_score`
- **Rate limiting (handler-enforced):** the per-session cap (`MEMORY_REMEMBER_PER_SESSION`, default 5) is enforced in the endpoint handler by counting existing `explicit_remember` evidence rows for the session — slowapi cannot key on session. A coarse per-engineer daily backstop can use slowapi only after its key function learns to read `x-device-token` (today it reads only `x-api-key`, so device-token MCP traffic would be keyed by client IP — middleware change noted in §16)
- Same redaction + identity scrub + quarantine as the passive path — `remember` does not bypass the judge

### Write-time safety

- **Redaction is a hard gate on capture itself** (§16): sketches persist transcript-derived text, so no sketch is written anywhere until the redaction pipeline is active. There is no unredacted "capture-only" mode.
- Identity scrub: engineer names/handles stripped from `body`; attribution lives in structured fields governed by the privacy policy
- All writes carry authenticated `engineer_id` from `AuthContext` — no ambient identity
- Sketch flood control: per-engineer and per-session sketch caps; consolidation processes newest-first with a per-pass ceiling

## 6. Read path

### Repository identity and access

The read surface is keyed on repository identity resolved server-side: MCP tools send `git_remote_url` (as the ingest path already does — `parse_repo_full_name` / `find_or_create_repository` in `ingest_service.py`), not free-text project names. Note: per-repository read authorization is **net-new** — the existing `_resolve_scope` convention in analytics resolves only (team_id, engineer_id) and has no repository ACL. v1.0 rule: an engineer may read memory for a repository if their team has sessions in it (computed membership), with admin override; this is implemented in the memory service, not borrowed from analytics.

### Session-start bundle

`GET /api/v1/memories/bundle?repo_remote_url=&goal_hint=&token_budget=`:

1. Resolve project scope (v1.1: scope chain project → groups → org)
2. Candidate set: `status IN (active, validated)`
3. Rank: `confidence × freshness × usage_value` — where `usage_value` demotes entries with high measured token cost and low retrieval relevance; entries in `decaying` are excluded
4. Retrieval when `goal_hint` present — **two modes by deployment** (resolves v1's open question):
   - **Postgres + pgvector**: keyword (postgres `tsvector`) + vector cosine, fused via Reciprocal Rank Fusion (k=60)
   - **SQLite**: keyword-only via FTS5 (BM25-style ranking); no vector column exists on these deployments. The core loop ships everywhere; vector recall is a postgres enhancement.
5. Fill to `token_budget` (default 2,000 tokens)
6. Log a `memory_injection` row per served entry
7. Cache the assembled bundle per (scope, goal-hint-hash) with short TTL (NarrativeCache pattern); injection logging still happens per serve

MCP surface: extend `session_start_coaching` to include the bundle, rendered as a compact markdown block. The tool's repo identity comes from `git_remote_url` (above).

### Mid-session recall

New MCP tool `primer_recall(query)` → same endpoint, smaller budget (default 800 tokens), `surface=recall`. Results carry `last_validated` timestamps so agents can weigh staleness. Also powers `in_session_nudges` enrichment (`surface=nudge`).

## 7. Consolidation engine

**Scheduling (corrected):** there is no cron scheduler in Primer; recurring work runs via `ensure_recurring_jobs` (interval-since-last-completion, in-process worker loop). Consolidation is registered as a recurring job with `MEMORY_CONSOLIDATION_INTERVAL_HOURS` (default 24); the cheap measurement pass (§8) runs at `MEMORY_MEASUREMENT_INTERVAL_HOURS` (default 6). No fixed wall-clock time in v1; multi-replica deployments rely on the existing job-claim semantics plus the per-scope advisory lock.

For each `memory_scope` with activity since `last_consolidation_at` (≥10 new sessions OR ≥5 new friction events OR ≥5 new sketches):

### Step 1 — Cluster and merge
Near-duplicate sketches (similarity above `MEMORY_DEDUP_SIMILARITY`; cosine where vectors exist, else keyword-overlap heuristic) merge into one canonical entry: evidence reparents, `corroboration_count` recomputes over distinct engineers with `independent=true`, originals get `merged_into` events. Merging is steady-state behavior — many sessions rediscover the same fact.

### Step 2 — Corroboration and statistical grounding
For each surviving sketch and each `active`/`validated` entry with new evidence:
- Recompute `independent` flags under the **engineer-level exposure horizon** (§8)
- Compute supporting outcome stats for the entry's cohort — defined keys: **turns** := `Session.assistant_message_count`; **input tokens** := `Session.input_tokens`; **success/friction** := `SessionFacets.outcome` / `friction_counts`; **harness cohort key** := derived from (agent_type, agent_version, permission_mode, customizations, tool-usage profile) — note this is a net-new derivation, not `SessionWorkflowProfile.fingerprint_id`
- Validate citations against the DB (drop hallucinated references)
- Recompute `confidence_score = f(corroboration_count, citation_count, explicit_remember_count, freshness, outcome_signal)`

### Step 3 — Judge gate (sketch → active)
Sketches with ≥2 independent corroborating engineers (configurable; `remember`-origin sketches qualify with 1 writer + 1 independent passive corroboration) go to the LLM judge. Criteria: reject if trivial / already represented / overstated vs. evidence / too general / not falsifiable / destructive operations / credential-or-secret-like content / **identity leakage**. Accept → `status=active`, `activated_at=now`, `activation_baseline` snapshot. Reject → `status=rejected` (sticky), critique persisted.

### Step 4 — Decay scoring
For `active`/`validated` entries, decay triggers (any):
- **Outcome floor:** the current-window outcome signal falls below an absolute minimum useful effect (`MEMORY_DECAY_MIN_USEFUL_LIFT`) — computed only when the window has ≥ `MEMORY_POSTACTIVATION_MIN_SESSIONS` sessions. No ratio-to-original-lift anchor: original point estimates at small N are too noisy to anchor on, and regression to the mean would mechanically trigger false decays.
- **Pattern extinct:** <3 matching sessions in the window
- **Persistent retrieval irrelevance:** entry ranks into bundles but is never retrieved by `recall` and its cohort stops appearing
→ `status=decaying`. Recovery in a later pass rehabilitates (→ `active`, window restarts — §4); no recovery within `MEMORY_DECAY_GRACE_PASSES` (default 3) → `retired`. Retired exported entries enter the removal-PR flow (§9); entries with `export_kept` are never re-proposed for removal.

### Step 5 — Index rebuild
Refresh keyword index (tsvector/FTS5) and verify vector index health where present.

*(v1.1 adds Step 6 scope promotion — pattern independently corroborated in ≥3 member projects → judged group-scope entry — and Step 7 affinity update with severed-pair memory.)*

### Concurrency and idempotency
Advisory lock per scope (postgres `pg_try_advisory_lock`; SQLite deployments run a single worker process so the job-claim semantics suffice). Idempotent: `UNIQUE(scope_id, content_hash)` absorbs replays; merges are evented for audit.

## 8. Measurement

### What v1.0 measures (and what it claims)

Per-entry signals, in decreasing order of certainty:
1. **Injection cost — measured exactly.** `avg_tokens_injected × n_injections` from `memory_injection`. Always reported.
2. **Usage — measured exactly.** Retrieval frequency, recall hits, bundle inclusion rate.
3. **Corroboration — measured, with exposure control.** Distinct engineers independently rediscovering the pattern (below).
4. **Human signals — measured.** Export PR merged/declined, bullet kept/deleted/edited, dashboard retire/un-retire actions.
5. **Outcome association — observational, labeled.** Cohort comparisons of sessions with vs. without the entry. Confounded by relevance-based injection (memories are injected into sessions they fit); reported as `method: "observational"` everywhere it surfaces, never as a causal claim, never aggregated into an unlabeled dollar headline.

**Promotion to `validated` (v1.0 criteria):** all of —
- ≥ `MEMORY_VALIDATION_MIN_CORROBORATION` (default 3) independent corroborating engineers post-activation
- sustained retrieval relevance (entry actually gets served/recalled, not just stored)
- no contradicting evidence or human-negative signals in the window
- judge re-check passes (still true, still specific, still identity-clean)

This is honest per-entry validation by corroboration + usage + human agreement — the same epistemic bar as GitHub Copilot's citation-validity + usage-decay, while the *causal* upgrade ships in v1.1. Session-level outcome deltas are **bundle-level diagnostics** in v1.0: a 2,000-token bundle co-injects many entries, so attributing a session outcome to a single entry is statistically unidentifiable without withholding; the spec does not pretend otherwise.

### Circular-evidence defense: engineer-level exposure horizon

A corroborating evidence row is `independent=true` only if the writing engineer was **not exposed** to this entry (or any near-duplicate above `MEMORY_DEDUP_SIMILARITY`) within `MEMORY_EXPOSURE_HORIZON_DAYS` (default 45) before the evidence's session — computed via `memory_injection` joined on `engineer_id`, not just `session_id`. This closes the internalization loophole: an engineer who read memory X last week and manifests it today is not independent corroboration, even though today's session never had X injected. Both the corroboration count and the cohort comparisons apply this filter.

### Token-efficiency ledger
- **Cost side (exact):** tokens injected, per entry and per scope.
- **Savings side (estimate, labeled):** turn/token deltas of exposed vs. unexposed cohorts, `method: "observational"`. "Avoided rediscovery" is a diagnostic counter only (it requires a detector with unmeasured precision) and never enters dollar figures.
- **FinOps surface:** v1.0 reports *"memory cost your team $X in injected tokens (measured); estimated efficiency effect: Y (observational — causal measurement arrives with experiments)."* No unlabeled "saved $X" headline until v1.1 experimental data exists.
- Ranking governor uses the **cost side** plus usage: high-cost, low-retrieval entries get demoted; persistent cost-without-usage is a decay input.

### v1.1: withholding experiments (designed now, shipped second)
The randomized layer activates once scopes have volume. Power analysis drove the design (a per-memory two-proportion test on success rate at a 10% holdout needs ~4,300 eligible sessions to detect a 7-pt lift — unreachable per-memory at realistic team volumes):
- **Per-entry experiments target continuous efficiency outcomes** (turns, input tokens) with paired/matched designs — adequately powered at tens-of-sessions scale
- **Binary outcome claims (success/merge-rate) run cluster-randomized at bundle level** — entire bundle on/off per session at a configured fraction — answering "does memory help this team" rather than "does entry #47"
- Experiments run at decision boundaries (validated promotion, scope promotion, decay disputes), auto-stop at confidence or sample cap, and exclude safety-relevant `anti_pattern` entries (those validate observationally + by human review only)
- Schema additions: `memory_injection.withheld`, `memory_entry.experiment_state`, events `experiment_started/completed`, config `MEMORY_HOLDOUT_FRACTION`

## 9. Crystallization export (the PR surface)

Eligibility: `status=validated` and not in `export_cooldown`. Cadence: weekly batch per project scope, or on-demand from the dashboard. One PR per batch; no stacking (wait if previous PR open).

- Target: `AGENTS.md` fenced sections (`<!-- primer:learned -->` block layout carried from v1 — facts / anti-patterns / pointers; `harness_config` and `procedure` render as markdown guidance in v1.0; `.claude.json` / `.cursor/rules` renderers deferred)
- PR body per entry: confidence, corroboration count, usage stats, outcome association **labeled observational** (v1.1 experiments upgrade the label), token cost, anonymized provenance ("11 sessions, 4 engineers"; names only where opted in)
- Branch `primer/crystallize-<repo>-<date>`, labels `primer`, `primer:learned`; never edit outside fenced sections
- **Lifecycle (complete, see §4 export transitions):**
  - PR merged → `exported` (`export_pr_merged`)
  - PR closed unmerged → `export_pr_declined`: `export_status=none`, confidence penalty, `export_cooldown_until = now + MEMORY_EXPORT_COOLDOWN_DAYS` (default 28) — entry stays `validated` and continues its lifecycle; it is not status-`rejected` (the team declined the *export*, not necessarily the memory)
  - Entry retires after export → removal PR (`removal_pr_opened`, `export_status=removal_pr_open`) → merged: `removed` (`removal_pr_merged`) / closed unmerged: `export_kept` (`removal_pr_closed`) — never re-proposed
  - Human deletes a bullet → `export_bullet_deleted`, `status=rejected` (sticky)
  - Human edits a bullet → `human_edited`, Primer stops re-rendering that entry; the store entry lives on for measurement

The strategic purpose: `AGENTS.md` is read natively by every harness, so validated memories reach engineers who never installed the MCP sidecar — and each PR is a visible, evidence-bearing artifact of Primer working.

## 10. Privacy and attribution

- **Internal provenance is complete**: every entry and evidence row carries `engineer_id` and `session_id` — required for corroboration counting, the exposure horizon, and audit.
- **Display is anonymized by default**: dashboard, bundles, and PR bodies show aggregate provenance only. Memory `body` text is identity-scrubbed at write time.
- **Opt-in visibility**: per-engineer setting (`visibility_opt_in` event); flips display only, never structured provenance.
- **Role-gated audit**: full provenance for admin roles via `AuthContext` role checks; access is audit-logged (existing `AuditLog` pattern).
- **Scope-boundary enforcement**: memory never crosses scopes (v1.1 scope promotion is the only judged, evented exception).
- **Redaction gate**: see §16 — no capture without the redaction pipeline. Cross-engineer sharing turns one machine's secret leak into the whole team's.

## 11. Dashboard (v1.0 scope, minimal)

A "Memory" tab per project workspace:
- Entry list: status, confidence, corroboration, usage, token cost, outcome association (labeled); filters by status/kind
- Entry detail: body, evidence (anonymized), event timeline
- Controls: retire, un-retire, trigger crystallization PR, pause memory for scope
- *(v1.1 adds: affinity panel with sever control, experiment results, re-test triggers)*

## 12. Configuration

| Var (PRIMER_ prefix) | Default | Stage | Purpose |
|---|---|---|---|
| `MEMORY_ENABLED` | `false` | v1.0 | master switch; refuses to activate without redaction pipeline + (postgres OR explicit `MEMORY_KEYWORD_ONLY=true` ack on SQLite) |
| `MEMORY_CONSOLIDATION_INTERVAL_HOURS` | `24` | v1.0 | recurring-job interval (no cron) |
| `MEMORY_MEASUREMENT_INTERVAL_HOURS` | `6` | v1.0 | cheap measurement pass |
| `MEMORY_DIRTY_SESSION_THRESHOLD` | `10` | v1.0 | |
| `MEMORY_DIRTY_FRICTION_THRESHOLD` | `5` | v1.0 | |
| `MEMORY_DIRTY_SKETCH_THRESHOLD` | `5` | v1.0 | |
| `MEMORY_MIN_CORROBORATION` | `2` | v1.0 | judge eligibility |
| `MEMORY_VALIDATION_MIN_CORROBORATION` | `3` | v1.0 | validated promotion |
| `MEMORY_EXPOSURE_HORIZON_DAYS` | `45` | v1.0 | engineer-level circular-evidence window |
| `MEMORY_DEDUP_SIMILARITY` | `0.85` | v1.0 | |
| `MEMORY_BUNDLE_TOKEN_BUDGET` | `2000` | v1.0 | |
| `MEMORY_RECALL_TOKEN_BUDGET` | `800` | v1.0 | |
| `MEMORY_REMEMBER_PER_SESSION` | `5` | v1.0 | handler-enforced |
| `MEMORY_EXTRACTION_MIN_SUBSTANCE` | `5` | v1.0 | pre-filter: min tool calls/friction/commits for extraction |
| `MEMORY_BACKFILL_MAX_SESSIONS` | `200` | v1.0 | cold-start bound |
| `MEMORY_POSTACTIVATION_WINDOW_DAYS` | `14` | v1.0 | |
| `MEMORY_POSTACTIVATION_MIN_SESSIONS` | `10` | v1.0 | sample floor for any outcome computation (incl. decay) |
| `MEMORY_DECAY_MIN_USEFUL_LIFT` | `0.02` | v1.0 | absolute outcome floor (no ratio-to-original anchor) |
| `MEMORY_DECAY_GRACE_PASSES` | `3` | v1.0 | |
| `MEMORY_EXPORT_CADENCE` | `weekly` | v1.0 | |
| `MEMORY_EXPORT_COOLDOWN_DAYS` | `28` | v1.0 | after declined export PR |
| `MEMORY_DAILY_TOKEN_BUDGET_USD` | `10.0` | v1.0 | per-org LLM spend cap |
| `MEMORY_PER_SCOPE_BUDGET_FRACTION` | `0.30` | v1.0 | |
| `MEMORY_AFFINITY_THRESHOLD` | `0.6` | v1.1 | |
| `MEMORY_HOLDOUT_FRACTION` | `0.10` | v1.1 | |

### Operational cost model

Extraction reuses the haiku-tier facet model. Per qualifying session: ~1 extraction call (redacted transcript excerpt + facets in, ≤5 cards out — comparable to a facet-extraction call, roughly $0.005–0.02 at haiku pricing). Consolidation adds judge calls (one per gated sketch, short prompts) and embedding generation (postgres only). Worked figure: a 25-engineer org at ~40 qualifying sessions/day ≈ $0.30–0.80/day extraction + nightly consolidation well under $1 — comfortably inside the $10/day default cap. **Cap-exhaustion behavior: defer, don't drop** — extraction jobs queue to a backlog and run when budget refreshes, so the cap never silently starves the corroboration bar (§14).

## 13. Testing

Carries the v1 strategy (SQLite unit tests, mocked-Anthropic integration tests, golden-case LLM evals nightly against the real API, rendering idempotence), plus:

- **Two-tier trust invariants**: `sketch` never appears in any bundle; `rejected` blocks similar sketches; promotion requires judge accept AND corroboration bar
- **Exposure horizon**: engineer E receives entry X in session 1; E's session 2 (no injection) produces matching evidence → `independent=false`, corroboration unchanged; engineer F (never exposed) produces matching evidence → corroboration increments
- **Status machine completeness**: every enum value reachable and exitable (export transitions incl. `removal_pr_merged`/`removal_pr_closed`/`export_kept`; rehabilitation → `active` with window reset); property-style test walking all documented transitions
- **Retrieval modes**: keyword-only path on SQLite (FTS5); hybrid RRF path on postgres (`@pytest.mark.pgvector` job against postgres+pgvector container)
- **Cold-start backfill**: seeded historical corpus → backfill produces sketches respecting pre-filter + budget; first consolidation promotes a starter set
- **Rate limiting**: handler-enforced per-session `remember` cap (count-based), 429 on breach
- **Token budget**: bundle never exceeds budget; governor demotes high-cost/low-usage entries
- **Privacy**: identity-scrub golden cases; anonymized display defaults; opt-in flips display only
- **Export drift**: human-edited bullet → `human_edited`, no re-render; deleted bullet → `export_bullet_deleted` + sticky rejection; declined PR → cooldown honored
- **Claims labeling**: every API payload carrying an outcome estimate includes `method: "observational"` (v1.0) — asserted in schema tests
- Coverage: ≥85% on new services; 100% on status-transition and exposure-exclusion logic
- *(v1.1 adds withholding-correctness suite)*

## 14. Error handling and failure modes

Carries v1's LLM-failure handling (retry/backoff/repair/defer), GitHub-failure handling (permission revocation → pause, conflict → retry with fresh reads), concurrency (advisory locks, idempotent replays). Additions:

- **Read path degradation**: retrieval failure → `session_start_coaching` returns its existing coaching content without the bundle; memory is additive, never blocking; MCP tools never propagate 5xx
- **Injection-log write failure**: bundle still served, serve excluded from measurement (attribution integrity beats data volume)
- **Budget exhaustion**: extraction defers to backlog (never drops); consolidation degrades to merge+dedup-only (skips LLM judge calls, leaves sketches pending) rather than skipping scopes entirely
- **Sketch flooding**: per-engineer/per-session caps; newest-first with per-pass ceiling
- **Stale-while-revalidate**: freshness factor decays ranking between consolidations; `recall` results carry `last_validated`
- **Observability**: `GET /api/v1/admin/memory/runs`, `/budget`; structured log per pass (sketches in, merged, promoted, rejected, decayed, retired, tokens, cost); alerts on pass >10min, budget exceeded, 3+ consecutive scope failures

## 15. Out of scope for v1.0

| Deferred | Target |
|---|---|
| Affinity groups, scope chain retrieval, scope promotion | v1.1 (designed in this spec) |
| Withholding experiments (causal measurement) | v1.1 (designed in this spec, §8) |
| Engineer-level personal memory | v2 |
| Group → org scope promotion | v2 |
| `.claude.json` / `.cursor/rules` export renderers | v1.1 |
| Full curation UX (votes, comments, bulk ops) | v1.1 |
| Knowledge-graph retrieval stream | v2 |
| Contradiction detection vs. human-written AGENTS.md prose | v2 |
| Auto-revert/auto-removal without human approval | v2, opt-in |
| Slack/Discord digest | v2 |
| Backtesting memories against historical sessions | separate roadmap |
| Mid-session proactive push | v2 — v1 is pull-only + session-start |
| Cross-org federation | not planned |

## 16. Dependencies and prerequisites

Ordered — these gate implementation start:

1. **P0 redaction pipeline (build first; entirely net-new).** No scrubbing code exists today (`_redact_mcp_config` is config-only). Redaction gates **capture itself**, not just promotion: sketches persist transcript-derived text. `MEMORY_ENABLED` hard-fails without it. Sequencing: redaction lands → capture + consolidation ship → read path activates.
2. **GitHub write client (net-new).** `github_service.py` is read-only (verified: no POST to GitHub exists; `webhooks.py` is inbound-only). The crystallization surface needs: create branch, read/write file contents, open PR — reusing the existing App-auth token plumbing. GitHub App permissions must include `contents: write` + `pull_requests: write` (currently read-oriented).
3. **pgvector (postgres enhancement, not a hard gate).** `pgvector` package + `CREATE EXTENSION` migration guarded to the postgres dialect (no-op on SQLite so `alembic upgrade head` and the SQLite test suite keep working). SQLite deployments — the shipped default (`config.py` defaults to `sqlite:///./primer.db`) — run keyword-only retrieval (FTS5) with full core-loop functionality.
4. **slowapi key function extension** (only if the per-engineer daily `remember` backstop is wanted): read `x-device-token` in addition to `x-api-key`.

Aligned existing work: async ingest + background jobs (incl. recurring-job and backfill patterns); MCP sidecar auth per-engineer; webhook ingestion for PR lifecycle events.

## 17. Open questions for implementation planning

1. Embedding model choice and dimensionality (1024 assumed; postgres deployments only)
2. Exact extraction and judge prompt texts — iterate against real session data before freezing golden evals
3. Bundle rendering format for `session_start_coaching` — markdown block that all four harnesses digest well
4. Cohort-matching method for the observational diagnostics (start with simple cohort baselines; propensity-style matching later)
5. Whether `procedure` kind needs structured steps or freeform markdown suffices for v1
6. Repository read-ACL refinement: is "team has sessions in repo" the right v1.0 membership heuristic, or should repo access be explicit config?
