# Multi-Agent Data Model Plan

## Context
Primer is built exclusively around Claude Code. To support Codex CLI (OpenAI) and Gemini CLI (Google), the data model needs an `agent_type` dimension throughout.

## Current Claude-Specific Elements
- `Session.claude_version` — stores Claude Code CLI version
- `SessionFacets.claude_helpfulness` — Claude-specific quality metric
- `pricing.py` — only Anthropic model pricing
- `extractor.py` — hardcoded Claude Code JSONL format
- `reader.py` — hardcoded `~/.claude/` paths
- Frontend types reference `claude_version`, `claude_helpfulness`

## Schema Changes

### 1. New `agent_type` column on `sessions`
```python
agent_type: Mapped[str] = mapped_column(String(30), nullable=False, server_default="claude_code")
```
Values: `"claude_code"`, `"codex_cli"`, `"gemini_cli"`. Plain String (not enum) — follows existing convention, avoids migration headaches. `server_default="claude_code"` backfills all existing rows automatically.

### 2. Rename `claude_version` → `agent_version`
```python
agent_version: Mapped[str | None] = mapped_column(String(50))
```
Alembic `alter_column` rename preserves data in-place.

### 3. Rename `claude_helpfulness` → `agent_helpfulness`
Same rename strategy on `SessionFacets`.

### 4. Add index on `agent_type`
```python
Index("ix_sessions_agent_type", "agent_type")
```

### 5. Add `agent_type` to `DailyStats`
Change unique constraint from `(engineer_id, date)` to `(engineer_id, date, agent_type)`.

## Pydantic Schema Changes

### AgentType literal
```python
AgentType = Literal["claude_code", "codex_cli", "gemini_cli"]
```

### SessionIngestPayload
- Add `agent_type: AgentType = "claude_code"`
- Rename `claude_version` → `agent_version`
- Keep `claude_version` as deprecated alias with `model_validator` for backward compat

### SessionResponse
- Add `agent_type`, `agent_version`
- Keep `claude_version` as deprecated alias during transition

### Analytics Schemas
- `OverviewStats` — add `agent_type_counts: dict[str, int]`
- `DailyStatsResponse` — add optional `agent_type`
- `EngineerStats`, `ProjectStats` — add `agent_type_breakdown`

### New filter parameter
Add `agent_type: AgentType | None = None` to `base_session_query` and propagate to all analytics endpoints and session listing.

## Pricing Changes

Add OpenAI and Google model pricing to `MODEL_PRICING`:

```python
# OpenAI (Codex CLI)
"gpt-4.1": ModelPricing(input=2.0/1M, output=8.0/1M, ...)
"gpt-4.1-mini": ModelPricing(input=0.40/1M, output=1.60/1M, ...)
"o3": ModelPricing(input=2.0/1M, output=8.0/1M, ...)
"o4-mini": ModelPricing(input=1.10/1M, output=4.40/1M, ...)
"codex-mini": ModelPricing(input=1.50/1M, output=6.0/1M, ...)

# Google (Gemini CLI)
"gemini-2.5-pro": ModelPricing(input=1.25/1M, output=10.0/1M, ...)
"gemini-2.5-flash": ModelPricing(input=0.15/1M, output=0.60/1M, ...)
"gemini-2.0-flash": ModelPricing(input=0.10/1M, output=0.40/1M, Bradley...)
```

Update fallback logic to detect provider from model name prefix.

## Migration Strategy

Single Alembic migration using `batch_alter_table` for SQLite compatibility:
1. Add `agent_type` column with `server_default='claude_code'`
2. Rename `claude_version` → `agent_version`
3. Rename `claude_helpfulness` → `agent_helpfulness`
4. Add index on `agent_type`
5. Update `daily_stats` constraint

All existing data preserved — no data transformation needed.

## Frontend Changes

- TypeScript: Add `AgentType` type, update `SessionResponse`
- Agent type filter dropdown on session list and analytics pages
- Session detail: show agent icon + version instead of "Claude Version"
- Rename "Claude PR Comparison" → "AI-Assisted PR Comparison"
- Add agent distribution chart to overview dashboard

## Backward Compatibility
1. API accepts both `claude_version` (deprecated) and `agent_version`
2. Responses include both during transition
3. Default `agent_type` to `"claude_code"` — existing hooks work unchanged
4. MCP sync defaults `agent_type` to `"claude_code"`

## Implementation Sequence
1. **Phase 1 — Database & Core**: Migration, models, schemas, pricing, ingest service, analytics query filter
2. **Phase 2 — Extractors & Readers**: New extractors, registry, reader update, sync update
3. **Phase 3 — API & Frontend**: Endpoint params, types, filter component, labels, charts
4. **Phase 4 — Agent Hooks** (optional): Codex/Gemini hook integration if supported
