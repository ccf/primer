# Multi-Agent Extractors Plan

## Context
Primer's extraction pipeline (discover → extract → normalize → sync → ingest) is hardcoded for Claude Code. This plan adds Codex CLI and Gemini CLI support.

## Current Pipeline
1. **Discovery** (`reader.py`): Reads `~/.claude/usage-data/session-meta/*.json`, resolves transcripts
2. **Extraction** (`extractor.py`): Parses Claude JSONL → `SessionMetadata` dataclass
3. **Normalization** (`SessionMetadata.to_ingest_payload()`): Converts to `SessionIngestPayload` dict
4. **Sync** (`sync.py`): Diffs local vs server, POSTs missing sessions
5. **Ingest** (`ingest_service.py`): Stores in Session model and related tables

## Agent Session Format Analysis

### Codex CLI (OpenAI)
- **Location**: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`
- **Structure**: JSONL with `RolloutLine` entries containing `timestamp` + variant type
- **Variants**: `SessionMeta` (id, cwd, cli_version, model), `TurnContext` (model, approval_policy), `EventMsg` (UserMessage, AgentMessage, ExecCommand*), `ResponseItem` (function calls)
- **Tokens**: Cumulative `token_count` events — requires delta computation
- **Tools**: ExecCommandBegin/End for shell, function_call ResponseItems
- **No facets system**

### Gemini CLI (Google)
- **Location**: `~/.gemini/tmp/<project_hash>/chats/session-*.json`
- **Structure**: JSON (not JSONL) with `Content[]` array
- **Messages**: `role` (user/model/function) + `parts` array with `text`/`functionCall`/`functionResponse`
- **Tokens**: Primary from `~/.gemini/telemetry.log` (OpenTelemetry events); session files may lack token data
- **Tools**: `functionCall`/`functionResponse` in message parts
- **No facets system**

### Token Mapping

| SessionMetadata field | Claude Code | Codex CLI | Gemini CLI |
|---|---|---|---|
| `input_tokens` | `input_tokens` | `input_tokens` (delta) | `input_token_count` |
| `output_tokens` | `output_tokens` | `output_tokens` (delta) | `output_token_count` |
| `cache_read_tokens` | `cache_read_input_tokens` | `cached_input_tokens` | `cached_content_token_count` |
| `cache_creation_tokens` | `cache_creation_input_tokens` | 0 (N/A) | 0 (N/A) |

## Design

### Extractor Protocol
```python
class SessionExtractor(Protocol):
    agent_type: str
    def discover_sessions(self) -> list[LocalSession]: ...
    def extract(self, transcript_path: str) -> SessionMetadata: ...
    def get_data_dir(self) -> Path: ...
```

### LocalSession update
```python
@dataclass
class LocalSession:
    session_id: str
    transcript_path: str
    facets_path: str | None
    has_facets: bool
    project_path: str | None = None
    agent_type: str = "claude_code"  # NEW
```

## New Files

### `src/primer/hook/codex_extractor.py`
- `CodexExtractor` class implementing the protocol
- Discovery: glob `**/rollout-*.jsonl` under `~/.codex/sessions/`
- Session ID from `SessionMeta.id` field (thread ID)
- Token delta computation from cumulative `token_count` events
- Tool counting: ExecCommandBegin + function_call events
- Message mapping: UserMessage → "human", AgentMessage → "assistant"
- Model from `TurnContext.model`; version from `SessionMeta.cli_version`

### `src/primer/hook/gemini_extractor.py`
- `GeminiExtractor` class implementing the protocol
- Discovery: glob `session-*.json` under `~/.gemini/tmp/*/chats/`
- Session ID from filename
- Dual data sources: session JSON for messages + telemetry.log for tokens
- Tool counting: `functionCall` parts in model messages
- Message mapping: `user` → "human", `model` → "assistant"
- Graceful degradation if telemetry unavailable (zero token counts)

### `src/primer/hook/extractor_registry.py`
```python
EXTRACTORS = {
    "claude_code": ClaudeCodeExtractor,
    "codex_cli": CodexExtractor,
    "gemini_cli": GeminiExtractor,
}

def get_all_extractors() -> list[SessionExtractor]: ...
def get_extractor_for(agent_type: str) -> SessionExtractor: ...
```

## Modified Files

### `reader.py`
- `list_local_sessions()` aggregates from all extractors
- Each extractor's `discover_sessions()` sets correct `agent_type`

### `sync.py`
- Dispatch to correct extractor based on `local_session.agent_type`
- Include `agent_type` in ingest payload

### `extractor.py`
- Wrap existing logic in `ClaudeCodeExtractor` class
- Keep module-level functions as backward-compatible aliases

### `ingest_service.py`
- Add `agent_type` to scalar field copy list

## Challenges
1. **Gemini token availability**: Telemetry may not be enabled → sessions with zero tokens
2. **Codex cumulative tokens**: Delta computation requires careful tracking of previous values
3. **Session ID collisions**: Negligible with UUIDs; document assumption rather than add prefixes
4. **Gemini project path**: Hash-based dirs may not reverse to readable paths
5. **Format stability**: Newer tools may change formats → write defensively

## Implementation Sequence

| Phase | Work | Dependencies |
|---|---|---|
| 1 | Schema changes (agent_type on models/schemas) | None |
| 2 | Pricing (add OpenAI/Google models) | None |
| 3 | Base extractor protocol + refactor Claude extractor | Phase 1 |
| 4 | Codex extractor + tests | Phase 3 |
| 5 | Gemini extractor + tests | Phase 3 |
| 6 | Update reader for multi-agent discovery | Phase 3 |
| 7 | Update sync for extractor dispatch | Phases 4, 5, 6 |
| 8 | Update ingest service | Phase 1 |
| 9 | End-to-end integration tests | All |

Phases 1-3 can proceed in parallel. Phases 4 and 5 can proceed in parallel.
