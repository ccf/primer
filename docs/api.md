# API Reference

Base URL: `http://localhost:8000`

## Authentication

- **Admin endpoints**: Pass `x-admin-key: <admin-key>` header
- **Ingest endpoints**: Pass `api_key` in the JSON body, or `x-api-key` header for facets

---

## Health

### GET /health

No authentication required.

**Response** `200`
```json
{"status": "ok"}
```

---

## Teams

### POST /api/v1/teams

Create a new team.

**Auth**: Admin

**Request**
```json
{"name": "Backend"}
```

**Response** `200`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Backend",
  "created_at": "2025-01-15T10:30:00"
}
```

### GET /api/v1/teams

List all teams.

**Auth**: Admin

**Response** `200`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Backend",
    "created_at": "2025-01-15T10:30:00"
  }
]
```

---

## Engineers

### POST /api/v1/engineers

Create a new engineer. Returns a one-time API key.

**Auth**: Admin

**Request**
```json
{
  "name": "Alice",
  "email": "alice@example.com",
  "team_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** `200`
```json
{
  "engineer": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "Alice",
    "email": "alice@example.com",
    "team_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-01-15T10:30:00"
  },
  "api_key": "primer_abc123..."
}
```

### GET /api/v1/engineers

List all engineers.

**Auth**: Admin

**Response** `200`
```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "Alice",
    "email": "alice@example.com",
    "team_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-01-15T10:30:00"
  }
]
```

### GET /api/v1/engineers/{engineer_id}/sessions

List sessions for a specific engineer.

**Auth**: Admin

**Response** `200`
```json
[
  {
    "id": "session-uuid",
    "engineer_id": "660e8400-e29b-41d4-a716-446655440001",
    "project_name": "my-project",
    "message_count": 42,
    "has_facets": true,
    "created_at": "2025-01-15T10:30:00",
    "..."
  }
]
```

---

## Ingest

### POST /api/v1/ingest/session

Ingest or update a single session.

**Auth**: API key in body

**Request**
```json
{
  "session_id": "unique-session-id",
  "api_key": "primer_abc123...",
  "project_path": "/home/user/my-project",
  "project_name": "my-project",
  "git_branch": "main",
  "claude_version": "1.0.0",
  "permission_mode": "default",
  "end_reason": "user_exit",
  "started_at": "2025-01-15T10:00:00",
  "ended_at": "2025-01-15T10:30:00",
  "duration_seconds": 1800.0,
  "message_count": 42,
  "user_message_count": 20,
  "assistant_message_count": 22,
  "tool_call_count": 15,
  "input_tokens": 50000,
  "output_tokens": 30000,
  "cache_read_tokens": 10000,
  "cache_creation_tokens": 5000,
  "primary_model": "claude-sonnet-4-5-20250929",
  "first_prompt": "Help me fix the login bug",
  "summary": "Fixed authentication issue in login flow",
  "facets": {
    "underlying_goal": "Fix login bug",
    "outcome": "success",
    "session_type": "debugging"
  },
  "tool_usages": [
    {"tool_name": "Read", "call_count": 10},
    {"tool_name": "Edit", "call_count": 5}
  ],
  "model_usages": [
    {
      "model_name": "claude-sonnet-4-5-20250929",
      "input_tokens": 50000,
      "output_tokens": 30000,
      "cache_read_tokens": 10000,
      "cache_creation_tokens": 5000
    }
  ]
}
```

**Response** `200`
```json
{
  "status": "ok",
  "session_id": "unique-session-id",
  "created": true
}
```

### POST /api/v1/ingest/bulk

Ingest multiple sessions at once.

**Auth**: API key in body

**Request**
```json
{
  "api_key": "primer_abc123...",
  "sessions": [
    {"session_id": "session-1", "api_key": "primer_abc123...", "message_count": 10},
    {"session_id": "session-2", "api_key": "primer_abc123...", "message_count": 20}
  ]
}
```

**Response** `200`
```json
{
  "status": "ok",
  "results": [
    {"status": "ok", "session_id": "session-1", "created": true},
    {"status": "ok", "session_id": "session-2", "created": true}
  ]
}
```

### POST /api/v1/ingest/facets/{session_id}

Upsert session facets (qualitative metadata).

**Auth**: `x-api-key` header

**Request**
```json
{
  "underlying_goal": "Fix login bug",
  "goal_categories": ["debugging", "authentication"],
  "outcome": "success",
  "session_type": "debugging",
  "primary_success": "bug_fixed",
  "claude_helpfulness": "very_helpful",
  "brief_summary": "Fixed auth token validation",
  "user_satisfaction_counts": {"satisfied": 1},
  "friction_counts": {"slow_response": 2},
  "friction_detail": "Model was slow on large files"
}
```

**Response** `200`
```json
{
  "status": "ok",
  "session_id": "unique-session-id",
  "created": true
}
```

---

## Sessions

### GET /api/v1/sessions

List sessions with optional filters.

**Auth**: Admin

**Query Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `engineer_id` | string | Filter by engineer |
| `team_id` | string | Filter by team |
| `start_date` | datetime | Filter sessions after this date |
| `end_date` | datetime | Filter sessions before this date |
| `limit` | int | Max results (default 100, max 1000) |
| `offset` | int | Pagination offset |

**Response** `200`
```json
[
  {
    "id": "session-uuid",
    "engineer_id": "engineer-uuid",
    "project_name": "my-project",
    "message_count": 42,
    "input_tokens": 50000,
    "output_tokens": 30000,
    "has_facets": true,
    "created_at": "2025-01-15T10:30:00"
  }
]
```

### GET /api/v1/sessions/{session_id}

Get full session details including facets, tool usages, and model usages.

**Auth**: Admin

**Response** `200`
```json
{
  "id": "session-uuid",
  "engineer_id": "engineer-uuid",
  "project_name": "my-project",
  "message_count": 42,
  "has_facets": true,
  "facets": {
    "underlying_goal": "Fix login bug",
    "outcome": "success",
    "session_type": "debugging",
    "created_at": "2025-01-15T10:30:00"
  },
  "tool_usages": [
    {"tool_name": "Read", "call_count": 10}
  ],
  "model_usages": [
    {"model_name": "claude-sonnet-4-5-20250929", "input_tokens": 50000, "output_tokens": 30000, "cache_read_tokens": 10000, "cache_creation_tokens": 5000}
  ]
}
```

---

## Analytics

All analytics endpoints accept an optional `team_id` query parameter to filter by team.

### GET /api/v1/analytics/overview

Aggregate usage statistics.

**Auth**: Admin

**Response** `200`
```json
{
  "total_sessions": 150,
  "total_engineers": 12,
  "total_messages": 6300,
  "total_tool_calls": 2100,
  "total_input_tokens": 7500000,
  "total_output_tokens": 4500000,
  "avg_session_duration": 1200.5,
  "avg_messages_per_session": 42.0,
  "outcome_counts": {"success": 100, "partial": 30, "failure": 20},
  "session_type_counts": {"feature": 80, "debugging": 40, "refactoring": 30}
}
```

### GET /api/v1/analytics/friction

Friction points ranked by frequency.

**Auth**: Admin

**Response** `200`
```json
[
  {
    "friction_type": "slow_response",
    "count": 25,
    "details": ["Slow on large files", "Long wait for complex queries"]
  },
  {
    "friction_type": "incorrect_edit",
    "count": 12,
    "details": ["Wrong file edited", "Syntax error introduced"]
  }
]
```

### GET /api/v1/analytics/tools

Tool usage rankings.

**Auth**: Admin

**Query Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `team_id` | string | Filter by team |
| `limit` | int | Max results (default 20, max 100) |

**Response** `200`
```json
[
  {"tool_name": "Read", "total_calls": 5000, "session_count": 140},
  {"tool_name": "Edit", "total_calls": 3200, "session_count": 120},
  {"tool_name": "Bash", "total_calls": 1800, "session_count": 90}
]
```

### GET /api/v1/analytics/models

Model usage rankings sorted by input tokens.

**Auth**: Admin

**Response** `200`
```json
[
  {
    "model_name": "claude-sonnet-4-5-20250929",
    "total_input_tokens": 5000000,
    "total_output_tokens": 3000000,
    "session_count": 130
  }
]
```

### GET /api/v1/analytics/recommendations

Actionable recommendations based on usage patterns.

**Auth**: Admin

**Response** `200`
```json
[
  {
    "category": "friction",
    "title": "High friction: slow_response",
    "description": "25 sessions reported slow_response friction. Consider investigating model latency.",
    "severity": "warning",
    "evidence": {"friction_type": "slow_response", "count": 25}
  }
]
```

---

## Error Responses

All endpoints return standard HTTP error codes:

| Status | Description |
|--------|-------------|
| `401` | Invalid API key |
| `403` | Invalid admin key |
| `404` | Resource not found |
| `422` | Validation error (Pydantic) |
