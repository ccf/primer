# Architecture

## System Overview

Primer consists of three components that work together to collect, store, and surface Claude Code usage insights:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Claude Code     │     │  Primer API      │     │  MCP Sidecar    │
│  SessionEnd Hook │────▶│  (FastAPI)       │◀────│  (FastMCP)      │
│                  │     │                  │     │                  │
│  Extracts data   │POST │  Stores sessions │HTTP │  Queries data   │
│  from transcripts│────▶│  Runs analytics  │◀────│  for Claude     │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                        ┌────────▼─────────┐
                        │  PostgreSQL       │
                        │  (or SQLite dev)  │
                        └──────────────────┘
```

### Component Responsibilities

**REST API Server** (`src/primer/server/`)
- Receives session data via ingest endpoints
- Stores and indexes sessions, facets, tool/model usage
- Computes analytics: overview stats, friction reports, tool rankings, recommendations
- Admin endpoints for team and engineer management

**Claude Code Hook** (`src/primer/hook/`)
- Runs automatically after each Claude Code session ends
- Parses JSONL transcript files to extract metadata
- Uploads session data to the Primer API server
- Zero-config after initial installation

**MCP Sidecar** (`src/primer/mcp/`)
- Model Context Protocol server with 5 tools
- Lets Claude query usage patterns during conversations
- Can sync local sessions and fetch team analytics
- Connects to the REST API via httpx

## Data Model

Primer uses 8 tables to capture the full picture of Claude Code usage:

```
teams
├── id (PK, UUID)
├── name (UNIQUE)
└── created_at

engineers
├── id (PK, UUID)
├── name
├── email (UNIQUE)
├── team_id (FK → teams)
├── api_key_hash (bcrypt)
├── created_at
└── updated_at

sessions
├── id (PK, UUID, client-provided)
├── engineer_id (FK → engineers)
├── project_path, project_name, git_branch
├── claude_version, permission_mode, end_reason
├── started_at, ended_at, duration_seconds
├── message_count, user_message_count, assistant_message_count
├── tool_call_count
├── input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens
├── primary_model, first_prompt, summary
├── has_facets
├── created_at
└── updated_at

session_facets (1:1 with sessions)
├── id (PK, auto)
├── session_id (FK → sessions, UNIQUE)
├── underlying_goal, goal_categories
├── outcome, session_type
├── primary_success, claude_helpfulness
├── brief_summary
├── user_satisfaction_counts, friction_counts
├── friction_detail
└── created_at

tool_usages (N:1 with sessions)
├── id (PK, auto)
├── session_id (FK → sessions)
├── tool_name
└── call_count

model_usages (N:1 with sessions)
├── id (PK, auto)
├── session_id (FK → sessions)
├── model_name
├── input_tokens, output_tokens
├── cache_read_tokens
└── cache_creation_tokens

daily_stats (per engineer, per day)
├── id (PK, auto)
├── engineer_id (FK → engineers)
├── date
├── message_count, session_count, tool_call_count
└── UNIQUE(engineer_id, date)

ingest_events (audit log)
├── id (PK, auto)
├── engineer_id (FK → engineers)
├── event_type (session, bulk, facets)
├── session_id, payload_size_bytes
├── status (ok, error), error_message
└── created_at
```

## Request Flows

### Session Ingest

```
Claude Code session ends
  → SessionEnd hook fires
  → extractor.py parses JSONL transcript
  → Extracts: messages, tokens, tools, models, metadata
  → Loads facets from ~/.claude/usage-data/facets/ (if available)
  → POST /api/v1/ingest/session with API key in body
  → ingest_service.upsert_session() creates/updates session
  → Tool usages, model usages, and facets stored
  → Ingest event logged for audit
```

### Analytics Query

```
Admin requests GET /api/v1/analytics/overview?team_id=...
  → require_admin dependency validates x-admin-key header
  → analytics_service.get_overview() queries sessions
  → Aggregates: totals, averages, outcome/type distributions
  → Returns OverviewStats schema
```

### MCP Tool Call

```
Claude calls `team_overview` MCP tool
  → primer_team_overview() in tools.py
  → httpx GET to PRIMER_SERVER_URL/api/v1/analytics/overview
  → Passes PRIMER_ADMIN_API_KEY as x-admin-key header
  → Returns JSON string to Claude
```

## Auth Model

Primer uses two authentication mechanisms:

**Admin Auth** — Simple shared secret
- Header: `x-admin-key`
- Compared against `PRIMER_ADMIN_API_KEY` setting
- Used for: team/engineer management, analytics, session queries

**Engineer Auth** — Bcrypt-hashed API keys
- Generated on engineer creation: `primer_{urlsafe_base64}`
- Stored as bcrypt hash in `engineers.api_key_hash`
- Verified by iterating all engineers and checking `bcrypt.checkpw()`
- Used for: session ingest (in body), facet upsert (in header)

The admin key is suitable for internal deployments. For production, consider adding rate limiting and key rotation.
