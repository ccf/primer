# Cursor Session Capture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Cursor as a first-class captured session source in Primer using a hybrid rollout: a safe import-based path first, then native local discovery once the telemetry contract is stable.

**Architecture:** Phase 1 introduces a Primer-owned Cursor session bundle format plus a new `CursorExtractor` that reads those bundles from a Primer-managed local directory, so `primer sync` can ingest Cursor sessions without depending on unstable Cursor internals. Phase 2 adds native discovery from Cursor-managed local files, plus a source-capability registry and measurement-integrity surfaces so Primer can include Cursor data safely in broader analytics.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, Click CLI, existing extractor/sync pipeline, pytest, TypeScript for shared API types.

**Design doc:** `docs/plans/2026-03-08-cursor-session-capture-design.md`

---

### Task 1: Add Cursor Agent Type and Source Capability Groundwork

**Files:**
- Create: `src/primer/common/source_capabilities.py`
- Modify: `src/primer/common/schemas.py`
- Modify: `frontend/src/types/api.ts`
- Test: `tests/test_source_capabilities.py`

**Step 1: Write the failing tests**

Create `tests/test_source_capabilities.py` with:

```python
from primer.common.source_capabilities import (
    AgentCapability,
    get_capability_for,
)


def test_cursor_capability_exists():
    cap = get_capability_for("cursor")
    assert cap.agent_type == "cursor"
    assert cap.supports_transcript is True


def test_unknown_agent_capability_is_none():
    assert get_capability_for("totally_unknown") is None
```

Also add a schema-level regression in a small new or existing test asserting `SessionIngestPayload(agent_type="cursor", ...)` is accepted.

**Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_source_capabilities.py -v`

Expected: FAIL because the capability registry and `cursor` agent type do not exist yet.

**Step 3: Implement the capability registry and agent type extension**

Create `src/primer/common/source_capabilities.py` with:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentCapability:
    agent_type: str
    supports_transcript: bool
    supports_tool_calls: bool
    supports_model_usage: bool
    supports_facets: bool
    supports_native_discovery: bool


CAPABILITIES = {
    "claude_code": ...,
    "codex_cli": ...,
    "gemini_cli": ...,
    "cursor": ...,
}


def get_capability_for(agent_type: str) -> AgentCapability | None: ...
```

Update:
- `src/primer/common/schemas.py` → extend `AgentType = Literal["claude_code", "codex_cli", "gemini_cli", "cursor"]`
- `frontend/src/types/api.ts` → add `cursor` to the shared agent type or any agent-type-dependent interface

**Step 4: Re-run the tests**

Run: `pytest tests/test_source_capabilities.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/primer/common/source_capabilities.py src/primer/common/schemas.py frontend/src/types/api.ts tests/test_source_capabilities.py
git commit -m "feat: add cursor agent type and capability registry"
```

---

### Task 2: Implement a Primer-Owned Cursor Bundle Format and Cursor Extractor

**Files:**
- Create: `src/primer/hook/cursor_extractor.py`
- Modify: `src/primer/hook/extractor_registry.py`
- Test: `tests/test_cursor_extractor.py`
- Test: `tests/test_extractor_registry.py`

**Step 1: Write the failing extractor tests**

Create `tests/test_cursor_extractor.py` with fixture-driven tests for a Primer-owned Cursor bundle format, for example:

```python
def test_extract_cursor_bundle_reads_core_metadata(tmp_path):
    bundle = {
        "session_id": "cursor-sess-1",
        "project_path": "/tmp/demo",
        "agent_version": "cursor-1.0.0",
        "started_at": "2026-03-08T10:00:00Z",
        "ended_at": "2026-03-08T10:05:00Z",
        "messages": [
            {"role": "human", "content_text": "Fix the failing test"},
            {"role": "assistant", "content_text": "I'll inspect the suite."},
        ],
        "tool_usages": [{"tool_name": "Read", "call_count": 2}],
        "model_usages": [{"model_name": "gpt-4.1", "input_tokens": 100, "output_tokens": 50}],
    }
```

Assert that:
- `meta.agent_type == "cursor"`
- messages, tools, models, and first prompt are mapped correctly
- token counts roll up into `SessionMetadata`

Add a registry assertion in `tests/test_extractor_registry.py`:

```python
ext = get_extractor_for("cursor")
assert ext is not None
assert ext.agent_type == "cursor"
```

**Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_cursor_extractor.py tests/test_extractor_registry.py -v`

Expected: FAIL because `CursorExtractor` does not exist and the registry only has three extractors.

**Step 3: Implement `CursorExtractor`**

Create `src/primer/hook/cursor_extractor.py` using the same interface shape as `CodexExtractor` and `GeminiExtractor`.

Recommended bundle format for Phase 1:

```json
{
  "session_id": "cursor-sess-1",
  "project_path": "/path/to/repo",
  "agent_version": "cursor-<version>",
  "started_at": "...",
  "ended_at": "...",
  "permission_mode": "workspace-write",
  "primary_model": "gpt-4.1",
  "messages": [...],
  "tool_usages": [...],
  "model_usages": [...],
  "summary": "...",
  "source_metadata": {
    "capture_mode": "import"
  }
}
```

The extractor should:
- set `agent_type = "cursor"`
- parse timestamps into `SessionMetadata`
- map imported messages directly into `meta.messages`
- roll tool/model usage into `tool_counts`, `model_tokens`, `input_tokens`, `output_tokens`
- degrade gracefully if optional sections are missing

Update `src/primer/hook/extractor_registry.py` to register `CursorExtractor`.

**Step 4: Re-run the tests**

Run: `pytest tests/test_cursor_extractor.py tests/test_extractor_registry.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/primer/hook/cursor_extractor.py src/primer/hook/extractor_registry.py tests/test_cursor_extractor.py tests/test_extractor_registry.py
git commit -m "feat: add cursor extractor for imported session bundles"
```

---

### Task 3: Add a `primer cursor import` Command and Primer-Managed Local Discovery

**Files:**
- Create: `src/primer/cli/commands/cursor_cmd.py`
- Modify: `src/primer/cli/main.py`
- Modify: `src/primer/mcp/reader.py`
- Modify: `src/primer/hook/cursor_extractor.py`
- Test: `tests/test_cursor_import.py`
- Test: `tests/test_mcp_reader.py`

**Step 1: Write the failing CLI and discovery tests**

Create `tests/test_cursor_import.py` with cases like:

```python
def test_cursor_import_copies_valid_bundle_into_primer_store(...): ...
def test_cursor_import_rejects_missing_session_id(...): ...
def test_cursor_import_is_idempotent_for_same_session_id(...): ...
```

Extend `tests/test_mcp_reader.py` to assert imported Cursor sessions appear in `list_local_sessions()` alongside Claude/Codex/Gemini sessions.

**Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_cursor_import.py tests/test_mcp_reader.py -v`

Expected: FAIL because there is no Cursor CLI group/command or Primer-managed storage path yet.

**Step 3: Implement the import command and discovery path**

Create `src/primer/cli/commands/cursor_cmd.py` with a Click group:

```python
@click.group("cursor")
def cursor() -> None: ...


@cursor.command("import")
@click.argument("bundle_path", type=click.Path(exists=True, path_type=Path))
def import_bundle(bundle_path: Path) -> None: ...
```

Recommended storage path:

```python
Path.home() / ".primer" / "cursor" / "sessions" / f"{session_id}.json"
```

The command should:
- validate the bundle by reusing `CursorExtractor.extract()` or a shared parser helper
- copy the validated bundle into Primer-managed storage
- avoid duplicate writes for the same `session_id`

Update:
- `src/primer/cli/main.py` → register the new `cursor` command group
- `src/primer/mcp/reader.py` → allow `list_local_sessions()` to discover Cursor bundles through the registered extractor
- `src/primer/hook/cursor_extractor.py` → `discover_sessions()` should scan the Primer-managed Cursor store in Phase 1

**Step 4: Re-run the tests**

Run: `pytest tests/test_cursor_import.py tests/test_mcp_reader.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/primer/cli/commands/cursor_cmd.py src/primer/cli/main.py src/primer/mcp/reader.py src/primer/hook/cursor_extractor.py tests/test_cursor_import.py tests/test_mcp_reader.py
git commit -m "feat: add cursor import command and local discovery"
```

---

### Task 4: Wire Cursor Through Sync and Ingest End-to-End

**Files:**
- Modify: `src/primer/mcp/sync.py`
- Modify: `src/primer/common/schemas.py`
- Modify: `src/primer/hook/extractor.py`
- Test: `tests/test_ingest.py`
- Test: `tests/test_hook_session_end.py`

**Step 1: Write the failing end-to-end tests**

Add regressions such as:

```python
def test_ingest_session_accepts_cursor_agent_type(...): ...
def test_sync_sessions_uploads_imported_cursor_bundle(...): ...
```

If `tests/test_hook_session_end.py` is the best place to assert agent-type forwarding and payload shape, add a Cursor-specific case there. Otherwise keep Cursor out of the SessionEnd hook until native discovery lands and keep the tests focused on sync/import.

**Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_ingest.py tests/test_hook_session_end.py -v`

Expected: FAIL because `cursor` is not yet represented consistently across sync/ingest paths.

**Step 3: Implement the minimal end-to-end wiring**

Update:
- `src/primer/mcp/sync.py` → no agent-specific assumptions that break Cursor imports
- `src/primer/common/schemas.py` → ensure ingest payloads and responses accept `cursor`
- `src/primer/hook/extractor.py` → if any helper assumes CLI-only semantics, make it generic enough for imported Cursor sessions

Keep Phase 1 out of the hook installer path. Cursor import-based capture should ride through `primer sync`, not pretend to be SessionEnd-hook-driven yet.

**Step 4: Re-run the tests**

Run: `pytest tests/test_ingest.py tests/test_hook_session_end.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/primer/mcp/sync.py src/primer/common/schemas.py src/primer/hook/extractor.py tests/test_ingest.py tests/test_hook_session_end.py
git commit -m "feat: wire cursor imports through sync and ingest"
```

---

### Task 5: Add Source-Quality and Safe Analytics Participation

**Files:**
- Modify: `src/primer/server/services/measurement_integrity_service.py`
- Modify: `src/primer/server/services/analytics_service.py`
- Modify: `src/primer/common/schemas.py`
- Modify: `frontend/src/types/api.ts`
- Test: `tests/test_admin.py`
- Test: `tests/test_analytics.py`

**Step 1: Write the failing integrity and analytics tests**

Add tests asserting:

```python
def test_measurement_integrity_stats_include_cursor_source_counts(...): ...
def test_overview_excludes_unsupported_cursor_metrics_from_success_rate_or_flags_them(...): ...
```

You do not need to redesign every metric in this phase. The goal is to prove Cursor does not silently corrupt unsupported analytics.

**Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_admin.py tests/test_analytics.py -v`

Expected: FAIL because measurement integrity and analytics do not yet distinguish source capability or partial telemetry.

**Step 3: Implement source-aware metrics**

Add to `measurement_integrity_service.py`:
- source-quality breakdown by `agent_type`
- counts for sessions missing transcript/tool/model telemetry

In `analytics_service.py`, add the minimum viable guardrails:
- only include sessions in a metric when required fields for that metric are present
- document those guardrails in code comments near the capability checks

If needed, add a schema like:

```python
class AgentSourceQuality(BaseModel):
    agent_type: str
    session_count: int
    transcript_coverage_pct: float
    tool_call_coverage_pct: float
    model_usage_coverage_pct: float
```

**Step 4: Re-run the tests**

Run: `pytest tests/test_admin.py tests/test_analytics.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/primer/server/services/measurement_integrity_service.py src/primer/server/services/analytics_service.py src/primer/common/schemas.py frontend/src/types/api.ts tests/test_admin.py tests/test_analytics.py
git commit -m "feat: add source-aware integrity metrics for cursor"
```

---

### Task 6: Phase 2 Native Discovery for Cursor Local Sessions

**Files:**
- Modify: `src/primer/hook/cursor_extractor.py`
- Modify: `src/primer/mcp/reader.py`
- Test: `tests/test_cursor_extractor.py`
- Test: `tests/test_mcp_reader.py`

**Step 1: Write the failing native-discovery tests**

Add tests for a native Cursor path once a local format decision is confirmed, for example:

```python
def test_discover_sessions_from_cursor_native_directory(tmp_path, monkeypatch): ...
```

This task should remain behind a stable fixture-based contract. If the actual Cursor format is not yet trustworthy, stop after Phase 1 and leave this task pending.

**Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_cursor_extractor.py tests/test_mcp_reader.py -v`

Expected: FAIL because native discovery is not implemented yet.

**Step 3: Implement native discovery behind a conservative probe**

Extend `CursorExtractor.discover_sessions()` to:
- prefer Primer-managed imported bundles
- optionally add native Cursor-discovered sessions if the local format can be parsed reliably
- deduplicate by `session_id`

Do not break the import-based path if native discovery is missing or incompatible.

**Step 4: Re-run the tests**

Run: `pytest tests/test_cursor_extractor.py tests/test_mcp_reader.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/primer/hook/cursor_extractor.py src/primer/mcp/reader.py tests/test_cursor_extractor.py tests/test_mcp_reader.py
git commit -m "feat: add native cursor session discovery"
```

---

### Final Verification

**Files:**
- Verify: `src/primer/hook/cursor_extractor.py`
- Verify: `src/primer/common/source_capabilities.py`
- Verify: `src/primer/mcp/sync.py`
- Verify: `src/primer/cli/commands/cursor_cmd.py`

**Step 1: Run the focused backend suite**

Run:

```bash
pytest tests/test_source_capabilities.py tests/test_cursor_extractor.py tests/test_cursor_import.py tests/test_mcp_reader.py tests/test_extractor_registry.py tests/test_ingest.py tests/test_hook_session_end.py tests/test_admin.py tests/test_analytics.py -v
```

Expected: PASS

**Step 2: Run lint**

Run:

```bash
ruff check src tests
```

Expected: PASS

**Step 3: Run the frontend type-check if shared types changed**

Run:

```bash
cd frontend && npx tsc -b --noEmit
```

Expected: PASS

**Step 4: Run a sync smoke test**

Run:

```bash
python -m primer.cli.main cursor import tests/fixtures/cursor/basic-session.json
python -m primer.cli.main sync
```

Expected: import succeeds and sync reports at least one local Cursor session discovered.

**Step 5: Final commit if verification changes were needed**

```bash
git add -A
git commit -m "chore: finish cursor session capture rollout"
```
