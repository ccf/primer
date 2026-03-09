"""Seed the database with realistic test data for development."""

import math
import os
import random
import uuid
from datetime import datetime, timedelta

import httpx

SERVER_URL = os.environ.get("PRIMER_SERVER_URL", "http://localhost:8000")


def _build_seed_auth_headers() -> dict[str, str]:
    """Prefer an explicit admin key, but allow an admin-role API key for local seeding."""
    admin_key = os.environ.get("PRIMER_ADMIN_API_KEY")
    if admin_key:
        return {"x-admin-key": admin_key}

    api_key = os.environ.get("PRIMER_API_KEY")
    if api_key:
        return {"x-api-key": api_key}

    return {"x-admin-key": "primer-admin-dev-key"}


ADMIN_HEADERS = _build_seed_auth_headers()


def _parse_bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _should_force_facets() -> bool:
    """Allow local refreshes to require facets for every seeded session."""
    return _parse_bool_env("PRIMER_SEED_FORCE_FACETS")


# ── Engineer personas ──────────────────────────────────────────────
PERSONAS = {
    "power_user": {
        "sessions_per_day": (3, 8),
        "weekend_factor": 0.3,
        "model_weights": {
            "claude-sonnet-4-5-20250929": 50,
            "claude-opus-4-20250514": 35,
            "claude-haiku-4-5-20251001": 15,
        },
        "outcome_weights": {"success": 70, "partial": 18, "failure": 8, "abandoned": 4},
        "tool_bias": [
            "Read",
            "Edit",
            "Write",
            "Bash",
            "Grep",
            "Glob",
            "Task:explore",
            "Task:python-pro",
            "Task:frontend-developer",
            "Skill:commit",
            "Skill:review-pr",
            "EnterPlanMode",
            "WebSearch",
            "AskUserQuestion",
        ],
        "token_scale": 1.5,
        "duration_range": (120, 5400),
    },
    "moderate": {
        "sessions_per_day": (1, 4),
        "weekend_factor": 0.1,
        "model_weights": {
            "claude-sonnet-4-5-20250929": 65,
            "claude-opus-4-20250514": 20,
            "claude-haiku-4-5-20251001": 15,
        },
        "outcome_weights": {"success": 65, "partial": 20, "failure": 10, "abandoned": 5},
        "tool_bias": [
            "Read",
            "Edit",
            "Bash",
            "Grep",
            "Glob",
            "Task:explore",
            "Skill:commit",
            "EnterPlanMode",
        ],
        "token_scale": 1.0,
        "duration_range": (60, 3600),
    },
    "occasional": {
        "sessions_per_day": (0, 2),
        "weekend_factor": 0.05,
        "model_weights": {
            "claude-sonnet-4-5-20250929": 75,
            "claude-opus-4-20250514": 5,
            "claude-haiku-4-5-20251001": 20,
        },
        "outcome_weights": {"success": 55, "partial": 25, "failure": 12, "abandoned": 8},
        "tool_bias": ["Read", "Edit", "Bash"],
        "token_scale": 0.7,
        "duration_range": (30, 1800),
    },
    "new_hire": {
        "sessions_per_day": (1, 3),
        "weekend_factor": 0.0,
        "model_weights": {
            "claude-sonnet-4-5-20250929": 80,
            "claude-opus-4-20250514": 5,
            "claude-haiku-4-5-20251001": 15,
        },
        "outcome_weights": {"success": 45, "partial": 30, "failure": 15, "abandoned": 10},
        "tool_bias": ["Read", "Bash", "Grep", "Task:explore"],
        "token_scale": 0.6,
        "duration_range": (60, 2400),
    },
    "ramping_up": {
        "sessions_per_day": (1, 4),
        "weekend_factor": 0.05,
        "model_weights": {
            "claude-sonnet-4-5-20250929": 70,
            "claude-opus-4-20250514": 15,
            "claude-haiku-4-5-20251001": 15,
        },
        "outcome_weights": {"success": 55, "partial": 25, "failure": 12, "abandoned": 8},
        "tool_bias": ["Read", "Edit", "Bash", "Grep", "Glob", "Task:explore", "Skill:commit"],
        "token_scale": 0.85,
        "duration_range": (60, 2700),
    },
}

# ── Agent type config (models, tools, versions per CLI) ───────────
AGENT_TYPE_CONFIG = {
    "claude_code": {
        "model_weights": None,  # uses PERSONAS[persona]["model_weights"]
        "tools": [
            "Read",
            "Edit",
            "Write",
            "Bash",
            "Grep",
            "Glob",
            "Task:explore",
            "Task:python-pro",
            "Task:frontend-developer",
            "Skill:commit",
            "Skill:review-pr",
            "EnterPlanMode",
            "WebSearch",
            "AskUserQuestion",
        ],
        "versions": ["1.0.17", "1.0.16", "1.0.15", "1.0.14", "1.0.13"],
        "permission_modes": ["default", "plan", "bypassPermissions"],
    },
    "codex_cli": {
        "model_weights": {
            "power_user": {"gpt-5.4": 40, "gpt-5.3-codex": 30, "gpt-5-mini": 15, "gpt-4.1": 15},
            "moderate": {"gpt-5.4": 30, "gpt-5.3-codex": 25, "gpt-5-mini": 25, "gpt-4.1": 20},
            "occasional": {"gpt-5-mini": 45, "gpt-4.1": 30, "gpt-5.4": 15, "gpt-5.3-codex": 10},
            "new_hire": {"gpt-5-mini": 45, "gpt-4.1": 30, "gpt-5.4": 15, "gpt-5.3-codex": 10},
            "ramping_up": {"gpt-5.4": 25, "gpt-5.3-codex": 20, "gpt-5-mini": 35, "gpt-4.1": 20},
        },
        "tools": [
            "exec_command",
            "shell",
            "file_read",
            "file_write",
            "function_call",
        ],
        "versions": ["0.111.0", "0.110.1", "0.110.0"],
        "permission_modes": ["on-request", "on-failure", "never"],
    },
    "gemini_cli": {
        "model_weights": {
            "power_user": {"gemini-2.5-pro": 55, "gemini-2.5-flash": 30, "gemini-2.0-flash": 15},
            "moderate": {"gemini-2.5-pro": 40, "gemini-2.5-flash": 40, "gemini-2.0-flash": 20},
            "occasional": {"gemini-2.5-flash": 50, "gemini-2.0-flash": 35, "gemini-2.5-pro": 15},
            "new_hire": {"gemini-2.5-flash": 55, "gemini-2.0-flash": 30, "gemini-2.5-pro": 15},
            "ramping_up": {
                "gemini-2.5-pro": 30,
                "gemini-2.5-flash": 45,
                "gemini-2.0-flash": 25,
            },
        },
        "tools": [
            "readFile",
            "writeFile",
            "editFile",
            "runShell",
            "searchWeb",
            "listFiles",
            "grepSearch",
        ],
        "versions": ["1.0.0", "0.9.2", "0.9.1"],
        "permission_modes": [None],
    },
}

# (name, email, team_idx, role, github_user, github_id, persona, agent_mix)
# Platform (0): Alice(admin,power), Marcus(lead,moderate), Priya(power), Jake(moderate,codex-heavy),
#               Yuki(new_hire)
# Backend  (1): Bob(lead,moderate), Carol(power), Dan(moderate,claude-only), Nina(occasional),
#               Raj(new_hire)
# Frontend (2): Eve(lead,moderate), Frank(power,codex-heavy), Lily(ramping_up),
#               Oscar(new_hire,gemini-heavy)
# Mobile   (3): Grace(lead,moderate), Hiro(occasional,mixed), Sofia(moderate)
# Data     (4): James(lead,power), Aisha(power), Chris(moderate,mixed), Mia(occasional)
# DevEx    (5): Kenji(lead,moderate), Fatima(ramping_up), Liam(ramping_up), Zara(new_hire)
ENGINEERS = [
    # ── Platform (team_idx=0) ──────────────────────────────────────
    (
        "Alice Chen",
        "alice@example.com",
        0,
        "admin",
        "alicechen",
        1001,
        "power_user",
        {"claude_code": 65, "codex_cli": 20, "gemini_cli": 15},
    ),
    (
        "Marcus Rivera",
        "marcus@example.com",
        0,
        "team_lead",
        "marcusrivera",
        1002,
        "moderate",
        {"claude_code": 70, "codex_cli": 20, "gemini_cli": 10},
    ),
    (
        "Priya Sharma",
        "priya@example.com",
        0,
        "engineer",
        "priyasharma",
        1003,
        "power_user",
        {"claude_code": 60, "codex_cli": 25, "gemini_cli": 15},
    ),
    (
        "Jake Thompson",
        "jake@example.com",
        0,
        "engineer",
        "jakethompson",
        1004,
        "moderate",
        {"claude_code": 45, "codex_cli": 50, "gemini_cli": 5},
    ),
    (
        "Yuki Sato",
        "yuki@example.com",
        0,
        "engineer",
        "yukisato",
        1005,
        "new_hire",
        {"claude_code": 80, "codex_cli": 10, "gemini_cli": 10},
    ),
    # ── Backend (team_idx=1) ───────────────────────────────────────
    (
        "Bob Smith",
        "bob@example.com",
        1,
        "team_lead",
        "bobsmith",
        1006,
        "moderate",
        {"claude_code": 75, "codex_cli": 15, "gemini_cli": 10},
    ),
    (
        "Carol Davis",
        "carol@example.com",
        1,
        "engineer",
        "caroldavis",
        1007,
        "power_user",
        {"claude_code": 70, "codex_cli": 20, "gemini_cli": 10},
    ),
    (
        "Dan Wilson",
        "dan@example.com",
        1,
        "engineer",
        "danwilson",
        1008,
        "moderate",
        {"claude_code": 100},
    ),
    (
        "Nina Patel",
        "nina@example.com",
        1,
        "engineer",
        "ninapatel",
        1009,
        "occasional",
        {"claude_code": 75, "codex_cli": 15, "gemini_cli": 10},
    ),
    (
        "Raj Krishnan",
        "raj@example.com",
        1,
        "engineer",
        "rajkrishnan",
        1010,
        "new_hire",
        {"claude_code": 85, "codex_cli": 10, "gemini_cli": 5},
    ),
    # ── Frontend (team_idx=2) ──────────────────────────────────────
    (
        "Eve Martinez",
        "eve@example.com",
        2,
        "team_lead",
        "evemartinez",
        1011,
        "moderate",
        {"claude_code": 70, "gemini_cli": 30},
    ),
    (
        "Frank Lee",
        "frank@example.com",
        2,
        "engineer",
        "franklee",
        1012,
        "power_user",
        {"claude_code": 45, "codex_cli": 45, "gemini_cli": 10},
    ),
    (
        "Lily Zhang",
        "lily@example.com",
        2,
        "engineer",
        "lilyzhang",
        1013,
        "ramping_up",
        {"claude_code": 75, "codex_cli": 15, "gemini_cli": 10},
    ),
    (
        "Oscar Mendez",
        "oscar@example.com",
        2,
        "engineer",
        "oscarmendez",
        1014,
        "new_hire",
        {"claude_code": 35, "codex_cli": 15, "gemini_cli": 50},
    ),
    # ── Mobile (team_idx=3) ────────────────────────────────────────
    (
        "Grace Kim",
        "grace@example.com",
        3,
        "team_lead",
        "gracekim",
        1015,
        "moderate",
        {"claude_code": 70, "codex_cli": 15, "gemini_cli": 15},
    ),
    (
        "Hiro Tanaka",
        "hiro@example.com",
        3,
        "engineer",
        "hirotanaka",
        1016,
        "occasional",
        {"claude_code": 34, "codex_cli": 33, "gemini_cli": 33},
    ),
    (
        "Sofia Rossi",
        "sofia@example.com",
        3,
        "engineer",
        "sofiarossi",
        1017,
        "moderate",
        {"claude_code": 65, "codex_cli": 20, "gemini_cli": 15},
    ),
    # ── Data (team_idx=4) ──────────────────────────────────────────
    (
        "James O'Brien",
        "james@example.com",
        4,
        "team_lead",
        "jamesobrien",
        1018,
        "power_user",
        {"claude_code": 60, "codex_cli": 25, "gemini_cli": 15},
    ),
    (
        "Aisha Mohammed",
        "aisha@example.com",
        4,
        "engineer",
        "aishamohammed",
        1019,
        "power_user",
        {"claude_code": 65, "codex_cli": 20, "gemini_cli": 15},
    ),
    (
        "Chris Nguyen",
        "chris@example.com",
        4,
        "engineer",
        "chrisnguyen",
        1020,
        "moderate",
        {"claude_code": 50, "codex_cli": 25, "gemini_cli": 25},
    ),
    (
        "Mia Johnson",
        "mia@example.com",
        4,
        "engineer",
        "miajohnson",
        1021,
        "occasional",
        {"claude_code": 70, "codex_cli": 20, "gemini_cli": 10},
    ),
    # ── DevEx (team_idx=5) ─────────────────────────────────────────
    (
        "Kenji Watanabe",
        "kenji@example.com",
        5,
        "team_lead",
        "kenjiwatanabe",
        1022,
        "moderate",
        {"claude_code": 70, "codex_cli": 20, "gemini_cli": 10},
    ),
    (
        "Fatima Al-Rashid",
        "fatima@example.com",
        5,
        "engineer",
        "fatimaalrashid",
        1023,
        "ramping_up",
        {"claude_code": 75, "codex_cli": 15, "gemini_cli": 10},
    ),
    (
        "Liam O'Connor",
        "liam@example.com",
        5,
        "engineer",
        "liamoconnor",
        1024,
        "ramping_up",
        {"claude_code": 70, "codex_cli": 20, "gemini_cli": 10},
    ),
    (
        "Zara Ahmed",
        "zara@example.com",
        5,
        "engineer",
        "zaraahmed",
        1025,
        "new_hire",
        {"claude_code": 80, "codex_cli": 10, "gemini_cli": 10},
    ),
]

# ── Projects ───────────────────────────────────────────────────────
PROJECTS = {
    "api-service": {
        "tool_weights": {
            "Read": 15,
            "Edit": 20,
            "Write": 10,
            "Bash": 25,
            "Grep": 15,
            "Glob": 10,
            "Task:explore": 6,
            "Task:python-pro": 4,
            "Skill:commit": 5,
            "EnterPlanMode": 3,
        },
        "outcome_bias": {"success": 5, "partial": 0, "failure": 0, "abandoned": 0},
    },
    "web-app": {
        "tool_weights": {
            "Read": 20,
            "Edit": 25,
            "Write": 15,
            "Bash": 10,
            "Grep": 10,
            "Glob": 10,
            "Task:explore": 5,
            "Task:frontend-developer": 8,
            "Skill:commit": 4,
            "Skill:review-pr": 3,
            "EnterPlanMode": 4,
            "WebSearch": 3,
        },
        "outcome_bias": {"success": 0, "partial": 5, "failure": 0, "abandoned": 0},
    },
    "cli-tool": {
        "tool_weights": {
            "Read": 10,
            "Edit": 15,
            "Write": 10,
            "Bash": 35,
            "Grep": 10,
            "Glob": 5,
            "Task:explore": 8,
            "Task:python-pro": 6,
            "Skill:commit": 6,
            "EnterPlanMode": 5,
        },
        "outcome_bias": {"success": 5, "partial": 0, "failure": -3, "abandoned": 0},
    },
    "shared-lib": {
        "tool_weights": {
            "Read": 25,
            "Edit": 20,
            "Write": 5,
            "Bash": 15,
            "Grep": 20,
            "Glob": 10,
            "Task:explore": 4,
            "Skill:commit": 3,
        },
        "outcome_bias": {"success": 0, "partial": 0, "failure": 5, "abandoned": 0},
    },
    "data-pipeline": {
        "tool_weights": {
            "Read": 15,
            "Edit": 10,
            "Write": 20,
            "Bash": 30,
            "Grep": 10,
            "Glob": 5,
            "Task:explore": 5,
            "Task:python-pro": 5,
            "Skill:commit": 4,
            "EnterPlanMode": 3,
            "AskUserQuestion": 2,
        },
        "outcome_bias": {"success": -5, "partial": 5, "failure": 5, "abandoned": 0},
    },
    "mobile-app": {
        "tool_weights": {
            "Read": 20,
            "Edit": 20,
            "Write": 15,
            "Bash": 15,
            "Grep": 10,
            "Glob": 10,
            "Task:explore": 5,
            "Task:frontend-developer": 4,
            "Skill:commit": 4,
            "Skill:review-pr": 2,
            "WebSearch": 3,
        },
        "outcome_bias": {"success": -3, "partial": 3, "failure": 3, "abandoned": 0},
    },
    "infra-config": {
        "tool_weights": {
            "Read": 15,
            "Edit": 10,
            "Write": 5,
            "Bash": 35,
            "Grep": 20,
            "Glob": 5,
            "Task:explore": 5,
            "Skill:commit": 5,
            "EnterPlanMode": 4,
        },
        "outcome_bias": {"success": 5, "partial": 0, "failure": -3, "abandoned": 0},
    },
    "ml-pipeline": {
        "tool_weights": {
            "Read": 15,
            "Edit": 10,
            "Write": 25,
            "Bash": 25,
            "Grep": 5,
            "Glob": 5,
            "Task:explore": 3,
            "Task:python-pro": 8,
            "Skill:commit": 4,
            "EnterPlanMode": 3,
            "AskUserQuestion": 3,
        },
        "outcome_bias": {"success": -5, "partial": 5, "failure": 5, "abandoned": 0},
    },
}

# ── First prompts by session type ──────────────────────────────────
FIRST_PROMPTS = {
    "feature": [
        "Add user authentication with JWT tokens",
        "Implement pagination for the list endpoint",
        "Add a new /health endpoint with database connectivity check",
        "Create a webhook handler for incoming events",
        "Build a file upload endpoint with S3 storage",
        "Implement rate limiting middleware",
        "Add email notification service for alerts",
        "Create a caching layer using Redis",
        "Build a search endpoint with full-text search",
        "Implement WebSocket support for real-time updates",
        "Add CSV export functionality to the reports API",
        "Create an audit log for all admin operations",
    ],
    "debugging": [
        "Fix the 500 error when submitting empty forms",
        "Debug why the login endpoint returns 401 intermittently",
        "The database connection pool is exhausting under load",
        "Memory leak in the background worker process",
        "Fix race condition in the concurrent update handler",
        "Debug flaky test in test_integration.py",
        "Investigate why cache invalidation isn't working",
        "Fix the CORS issue with the frontend",
        "Debug slow query on the sessions table",
        "Fix the timezone handling bug in date filters",
    ],
    "refactoring": [
        "Refactor the auth module to use dependency injection",
        "Split the monolithic router into domain-specific files",
        "Migrate from callbacks to async/await pattern",
        "Extract the validation logic into reusable decorators",
        "Convert raw SQL queries to SQLAlchemy ORM",
        "Refactor the test fixtures to reduce duplication",
        "Simplify the error handling middleware",
        "Move configuration into pydantic-settings",
        "Refactor the service layer to follow repository pattern",
        "Clean up unused imports and dead code",
    ],
    "exploration": [
        "How does the authentication flow work end-to-end?",
        "What's the current database schema for the sessions table?",
        "Show me all the API endpoints and their auth requirements",
        "Explain how the caching layer is implemented",
        "Walk me through the deployment pipeline",
        "What testing patterns are used in this codebase?",
        "How is error handling structured across the app?",
        "Show me the data flow from ingestion to analytics",
        "What are the main dependencies and their versions?",
        "Analyze the performance bottlenecks in the query layer",
    ],
    "documentation": [
        "Write API documentation for the sessions endpoint",
        "Add docstrings to the analytics service module",
        "Create a README for the deployment process",
        "Document the data model and relationships",
        "Write a migration guide for the v2 API changes",
        "Add inline comments to the pricing calculation logic",
        "Create a troubleshooting guide for common errors",
        "Document the environment variables and configuration",
        "Write a developer onboarding guide",
        "Update the CHANGELOG with recent changes",
    ],
}

# ── Summary templates ──────────────────────────────────────────────
SUMMARY_TEMPLATES = {
    "feature": [
        "Implemented {feature} with full test coverage",
        "Added {feature} endpoint and integrated with existing auth",
        "Built {feature} using the repository pattern with migrations",
        "Created {feature} with input validation and error handling",
        "Implemented {feature} with rate limiting and monitoring",
    ],
    "debugging": [
        "Fixed {issue} by correcting the query filter logic",
        "Resolved {issue} — root cause was a missing null check",
        "Debugged and fixed {issue} in the middleware chain",
        "Traced {issue} to a race condition in async handler, applied lock",
        "Fixed {issue} by updating the connection pool configuration",
    ],
    "refactoring": [
        "Refactored {module} to improve separation of concerns",
        "Simplified {module} by extracting common patterns",
        "Migrated {module} to use modern async patterns",
        "Cleaned up {module} and improved type annotations",
        "Restructured {module} following domain-driven design principles",
    ],
    "exploration": [
        "Explored {area} and documented findings",
        "Analyzed {area} — identified three improvement areas",
        "Reviewed {area} and created summary notes",
        "Investigated {area} for potential optimization",
        "Mapped out {area} dependencies and data flow",
    ],
    "documentation": [
        "Documented {topic} with examples and edge cases",
        "Added comprehensive docs for {topic}",
        "Created developer guide for {topic}",
        "Updated documentation for {topic} with latest changes",
        "Wrote API reference for {topic}",
    ],
}

FEATURE_NOUNS = [
    "JWT auth middleware",
    "pagination support",
    "health check",
    "webhook handler",
    "file upload",
    "rate limiter",
    "email notifications",
    "Redis caching",
    "full-text search",
    "WebSocket support",
    "CSV export",
    "audit logging",
]

ISSUE_NOUNS = [
    "500 error on empty form submission",
    "intermittent auth failure",
    "connection pool exhaustion",
    "memory leak in worker",
    "race condition in updates",
    "flaky integration test",
    "cache invalidation bug",
    "CORS misconfiguration",
    "slow session query",
    "timezone handling bug",
]

MODULE_NOUNS = [
    "auth module",
    "router structure",
    "async handlers",
    "validation layer",
    "query builder",
    "test fixtures",
    "error middleware",
    "config management",
    "service layer",
    "import cleanup",
]

AREA_NOUNS = [
    "authentication flow",
    "database schema",
    "API surface",
    "caching implementation",
    "deployment pipeline",
    "testing patterns",
    "error handling",
    "data flow",
    "dependency tree",
    "query performance",
]

TOPIC_NOUNS = [
    "sessions API",
    "analytics service",
    "deployment process",
    "data model",
    "v2 migration",
    "pricing logic",
    "troubleshooting",
    "environment config",
    "onboarding",
    "CHANGELOG",
]

# ── Git branch templates ───────────────────────────────────────────
BRANCH_TEMPLATES = {
    "feature": ["feat/{slug}", "feature/{slug}"],
    "debugging": ["fix/{slug}", "hotfix/{slug}", "bugfix/{slug}"],
    "refactoring": ["refactor/{slug}", "chore/{slug}"],
    "exploration": ["explore/{slug}", "spike/{slug}"],
    "documentation": ["docs/{slug}", "chore/docs-{slug}"],
}

BRANCH_SLUGS = [
    "auth-middleware",
    "pagination",
    "health-check",
    "webhooks",
    "file-upload",
    "rate-limit",
    "email-notifications",
    "redis-cache",
    "search",
    "websocket",
    "csv-export",
    "audit-log",
    "fix-500",
    "fix-auth",
    "pool-config",
    "memory-leak",
    "race-condition",
    "flaky-test",
    "cache-fix",
    "cors-fix",
    "slow-query",
    "timezone-bug",
    "cleanup",
    "refactor-services",
]

# ── Git repositories for commit generation ────────────────────────
GIT_REPOS = {
    "api-service": "https://github.com/acme-corp/api-service.git",
    "web-app": "https://github.com/acme-corp/web-app.git",
    "cli-tool": "https://github.com/acme-corp/cli-tool.git",
    "shared-lib": "https://github.com/acme-corp/shared-lib.git",
    "data-pipeline": "https://github.com/acme-corp/data-pipeline.git",
    "mobile-app": "https://github.com/acme-corp/mobile-app.git",
    "infra-config": "https://github.com/acme-corp/infra-config.git",
    "ml-pipeline": "https://github.com/acme-corp/ml-pipeline.git",
}

COMMIT_MESSAGES = {
    "feature": [
        "Add {slug} endpoint",
        "Implement {slug} handler",
        "Create {slug} model and migration",
        "Add tests for {slug}",
        "Wire up {slug} to router",
        "Add validation for {slug} input",
    ],
    "debugging": [
        "Fix null check in {slug} handler",
        "Correct query filter for {slug}",
        "Handle edge case in {slug}",
        "Fix off-by-one error in {slug}",
        "Add missing error handling for {slug}",
    ],
    "refactoring": [
        "Extract {slug} into separate module",
        "Simplify {slug} logic",
        "Rename variables in {slug} for clarity",
        "Move {slug} to service layer",
        "Clean up {slug} imports",
    ],
}

COMMIT_AUTHORS = {
    "Alice Chen": "alice@example.com",
    "Marcus Rivera": "marcus@example.com",
    "Priya Sharma": "priya@example.com",
    "Jake Thompson": "jake@example.com",
    "Yuki Sato": "yuki@example.com",
    "Bob Smith": "bob@example.com",
    "Carol Davis": "carol@example.com",
    "Dan Wilson": "dan@example.com",
    "Nina Patel": "nina@example.com",
    "Raj Krishnan": "raj@example.com",
    "Eve Martinez": "eve@example.com",
    "Frank Lee": "frank@example.com",
    "Lily Zhang": "lily@example.com",
    "Oscar Mendez": "oscar@example.com",
    "Grace Kim": "grace@example.com",
    "Hiro Tanaka": "hiro@example.com",
    "Sofia Rossi": "sofia@example.com",
    "James O'Brien": "james@example.com",
    "Aisha Mohammed": "aisha@example.com",
    "Chris Nguyen": "chris@example.com",
    "Mia Johnson": "mia@example.com",
    "Kenji Watanabe": "kenji@example.com",
    "Fatima Al-Rashid": "fatima@example.com",
    "Liam O'Connor": "liam@example.com",
    "Zara Ahmed": "zara@example.com",
}


def _generate_commits(
    session_type: str, started_at: datetime, ended_at: datetime, eng_name: str, branch_slug: str
) -> list[dict]:
    """Generate synthetic commits for a session."""
    if session_type not in ("feature", "debugging", "refactoring"):
        return []
    if random.random() < 0.3:  # 30% of coding sessions have no commits
        return []

    n_commits = random.randint(1, 5)
    commits = []
    duration = (ended_at - started_at).total_seconds()

    for _i in range(n_commits):
        offset_secs = random.uniform(duration * 0.2, duration * 0.95)
        committed_at = started_at + timedelta(seconds=offset_secs)
        slug = branch_slug.split("/")[-1] if "/" in branch_slug else branch_slug
        msg = random.choice(COMMIT_MESSAGES[session_type]).format(slug=slug)
        files_changed = random.randint(1, 12)
        lines_added = random.randint(5, 300)
        lines_deleted = random.randint(0, 150)

        commits.append(
            {
                "sha": uuid.uuid4().hex + uuid.uuid4().hex[:8],
                "message": msg,
                "author_name": eng_name,
                "author_email": COMMIT_AUTHORS.get(eng_name, "dev@example.com"),
                "committed_at": committed_at.isoformat(),
                "files_changed": files_changed,
                "lines_added": lines_added,
                "lines_deleted": lines_deleted,
            }
        )

    return commits


GOAL_CATEGORIES_BY_TYPE = {
    "feature": ["new_feature", "api_endpoint", "integration", "ui_component"],
    "debugging": ["bug_fix", "performance", "error_handling", "regression"],
    "refactoring": ["code_quality", "architecture", "testing", "cleanup"],
    "exploration": ["code_review", "learning", "investigation", "planning"],
    "documentation": ["api_docs", "guides", "comments", "changelog"],
}


FRICTION_TYPES = ["tool_error", "permission_denied", "timeout", "context_limit", "edit_conflict"]
FRICTION_DETAILS = {
    "tool_error": [
        "Bash tool failed: command not found 'jq'",
        "Edit tool rejected: old_string not found in file",
        "Write tool failed: permission denied on /etc/config",
        "Grep returned no results for expected pattern",
    ],
    "permission_denied": [
        "User denied Bash execution for 'rm -rf node_modules'",
        "Permission denied to read .env file",
        "Blocked from executing git push --force",
    ],
    "timeout": [
        "Bash command timed out after 120s: npm install",
        "Long-running test suite exceeded timeout",
        "API request to external service timed out",
    ],
    "context_limit": [
        "Context window exhausted after reading large file",
        "Conversation compressed due to context limits",
    ],
    "edit_conflict": [
        "Edit failed: file was modified externally",
        "Concurrent edit detected on models.py",
    ],
}

# ── Assistant responses by agent type ─────────────────────────────
ASSISTANT_RESPONSES = [
    "Let me look at the code first.",
    "I'll read the file to understand the current implementation.",
    "I've found the issue. Let me fix it.",
    "I'll run the tests to verify the fix.",
    "Here's the implementation. I've added proper error handling.",
    "Let me check the existing tests for this module.",
    "I'll create a new test file for this functionality.",
    "The build is passing. Let me verify the changes.",
    "I'll refactor this to use the existing pattern in the codebase.",
    "I've made the changes. Here's a summary of what was modified.",
]

CODEX_ASSISTANT_RESPONSES = [
    "Reading the file to understand the structure.",
    "I'll execute the command to check the current state.",
    "Found the issue. Applying the fix now.",
    "Running tests to verify the change.",
    "Here's the updated implementation.",
    "Let me read the test file first.",
    "Writing the new file with the changes.",
    "The command completed successfully.",
    "I've applied the patch. Let me verify.",
    "Changes applied. Here's what was modified.",
]

GEMINI_ASSISTANT_RESPONSES = [
    "Let me read the relevant files.",
    "I'll search the codebase for that pattern.",
    "Found it. Let me edit the file now.",
    "Running the shell command to verify.",
    "Here's the implementation with the requested changes.",
    "Let me search the web for the latest docs on this.",
    "I'll list the files in this directory first.",
    "The edit was applied successfully.",
    "Let me grep for related usages.",
    "Changes complete. Here's a summary.",
]

ASSISTANT_RESPONSES_BY_AGENT = {
    "claude_code": ASSISTANT_RESPONSES,
    "codex_cli": CODEX_ASSISTANT_RESPONSES,
    "gemini_cli": GEMINI_ASSISTANT_RESPONSES,
}

# ── Tool call/result templates by agent type ─────────────────────
TOOL_CALL_TEMPLATES = [
    {"name": "Read", "input_preview": '{"file_path": "src/main.py"}'},
    {"name": "Edit", "input_preview": '{"file_path": "src/main.py", "old_string": "..."}'},
    {"name": "Write", "input_preview": '{"file_path": "src/new_file.py", "content": "..."}'},
    {"name": "Bash", "input_preview": '{"command": "pytest -v tests/"}'},
    {"name": "Grep", "input_preview": '{"pattern": "def handle_", "path": "src/"}'},
    {"name": "Glob", "input_preview": '{"pattern": "**/*.py"}'},
    {"name": "Task", "input_preview": '{"subagent_type": "explore", "prompt": "find usage"}'},
    {"name": "Skill", "input_preview": '{"skill": "commit"}'},
    {"name": "EnterPlanMode", "input_preview": "{}"},
]

TOOL_RESULT_TEMPLATES = [
    {"name": "Read", "output_preview": "import os\nimport sys\n\ndef main():\n    ..."},
    {"name": "Edit", "output_preview": "File updated successfully."},
    {"name": "Bash", "output_preview": "PASSED 12 tests in 0.5s"},
    {"name": "Grep", "output_preview": "src/handler.py:15: def handle_request"},
    {"name": "Glob", "output_preview": "src/main.py\nsrc/utils.py\nsrc/handler.py"},
    {"name": "Task", "output_preview": "Found 3 usages of the function across the codebase."},
    {"name": "Skill", "output_preview": "Committed changes with message: feat: add endpoint"},
    {"name": "EnterPlanMode", "output_preview": "Entered plan mode."},
]

CODEX_TOOL_CALL_TEMPLATES = [
    {"name": "exec_command", "input_preview": '{"command": "pytest -v tests/"}'},
    {"name": "shell", "input_preview": '{"command": "ls -la src/"}'},
    {"name": "file_read", "input_preview": '{"path": "src/main.py"}'},
    {"name": "file_write", "input_preview": '{"path": "src/main.py", "content": "..."}'},
    {"name": "function_call", "input_preview": '{"name": "apply_patch", "args": {...}}'},
]

CODEX_TOOL_RESULT_TEMPLATES = [
    {"name": "exec_command", "output_preview": "PASSED 12 tests in 0.5s"},
    {"name": "shell", "output_preview": "src/main.py\nsrc/utils.py\nsrc/handler.py"},
    {"name": "file_read", "output_preview": "import os\nimport sys\n\ndef main():\n    ..."},
    {"name": "file_write", "output_preview": "File written successfully."},
    {"name": "function_call", "output_preview": "Patch applied successfully."},
]

GEMINI_TOOL_CALL_TEMPLATES = [
    {"name": "readFile", "input_preview": '{"path": "src/main.py"}'},
    {"name": "writeFile", "input_preview": '{"path": "src/new_file.py", "content": "..."}'},
    {"name": "editFile", "input_preview": '{"path": "src/main.py", "edits": [...]}'},
    {"name": "runShell", "input_preview": '{"command": "pytest -v tests/"}'},
    {"name": "searchWeb", "input_preview": '{"query": "python async patterns"}'},
    {"name": "listFiles", "input_preview": '{"path": "src/"}'},
    {"name": "grepSearch", "input_preview": '{"pattern": "def handle_", "path": "src/"}'},
]

GEMINI_TOOL_RESULT_TEMPLATES = [
    {"name": "readFile", "output_preview": "import os\nimport sys\n\ndef main():\n    ..."},
    {"name": "writeFile", "output_preview": "File written successfully."},
    {"name": "editFile", "output_preview": "File updated successfully."},
    {"name": "runShell", "output_preview": "PASSED 12 tests in 0.5s"},
    {"name": "searchWeb", "output_preview": "Found 5 relevant results."},
    {"name": "listFiles", "output_preview": "src/main.py\nsrc/utils.py\nsrc/handler.py"},
    {"name": "grepSearch", "output_preview": "src/handler.py:15: def handle_request"},
]

TOOL_TEMPLATES_BY_AGENT = {
    "claude_code": (TOOL_CALL_TEMPLATES, TOOL_RESULT_TEMPLATES),
    "codex_cli": (CODEX_TOOL_CALL_TEMPLATES, CODEX_TOOL_RESULT_TEMPLATES),
    "gemini_cli": (GEMINI_TOOL_CALL_TEMPLATES, GEMINI_TOOL_RESULT_TEMPLATES),
}

# ── Project tool weights by agent type ────────────────────────────
CODEX_PROJECT_TOOL_WEIGHTS = {
    "api-service": {
        "exec_command": 25,
        "shell": 15,
        "file_read": 20,
        "file_write": 25,
        "function_call": 15,
    },
    "web-app": {
        "exec_command": 15,
        "shell": 10,
        "file_read": 25,
        "file_write": 30,
        "function_call": 20,
    },
    "cli-tool": {
        "exec_command": 35,
        "shell": 20,
        "file_read": 15,
        "file_write": 20,
        "function_call": 10,
    },
    "shared-lib": {
        "exec_command": 15,
        "shell": 10,
        "file_read": 30,
        "file_write": 25,
        "function_call": 20,
    },
    "data-pipeline": {
        "exec_command": 30,
        "shell": 20,
        "file_read": 15,
        "file_write": 20,
        "function_call": 15,
    },
    "mobile-app": {
        "exec_command": 15,
        "shell": 10,
        "file_read": 25,
        "file_write": 30,
        "function_call": 20,
    },
    "infra-config": {
        "exec_command": 35,
        "shell": 25,
        "file_read": 15,
        "file_write": 15,
        "function_call": 10,
    },
    "ml-pipeline": {
        "exec_command": 25,
        "shell": 15,
        "file_read": 15,
        "file_write": 30,
        "function_call": 15,
    },
}

GEMINI_PROJECT_TOOL_WEIGHTS = {
    "api-service": {
        "readFile": 15,
        "writeFile": 15,
        "editFile": 20,
        "runShell": 25,
        "searchWeb": 5,
        "listFiles": 10,
        "grepSearch": 10,
    },
    "web-app": {
        "readFile": 20,
        "writeFile": 15,
        "editFile": 25,
        "runShell": 10,
        "searchWeb": 10,
        "listFiles": 10,
        "grepSearch": 10,
    },
    "cli-tool": {
        "readFile": 10,
        "writeFile": 10,
        "editFile": 15,
        "runShell": 35,
        "searchWeb": 5,
        "listFiles": 10,
        "grepSearch": 15,
    },
    "shared-lib": {
        "readFile": 25,
        "writeFile": 10,
        "editFile": 20,
        "runShell": 15,
        "searchWeb": 5,
        "listFiles": 10,
        "grepSearch": 15,
    },
    "data-pipeline": {
        "readFile": 15,
        "writeFile": 15,
        "editFile": 15,
        "runShell": 30,
        "searchWeb": 5,
        "listFiles": 10,
        "grepSearch": 10,
    },
    "mobile-app": {
        "readFile": 20,
        "writeFile": 15,
        "editFile": 20,
        "runShell": 15,
        "searchWeb": 10,
        "listFiles": 10,
        "grepSearch": 10,
    },
    "infra-config": {
        "readFile": 10,
        "writeFile": 10,
        "editFile": 10,
        "runShell": 35,
        "searchWeb": 5,
        "listFiles": 15,
        "grepSearch": 15,
    },
    "ml-pipeline": {
        "readFile": 15,
        "writeFile": 20,
        "editFile": 15,
        "runShell": 25,
        "searchWeb": 10,
        "listFiles": 5,
        "grepSearch": 10,
    },
}

PROJECT_TOOL_WEIGHTS_BY_AGENT = {
    "claude_code": None,  # uses PROJECTS[name]["tool_weights"]
    "codex_cli": CODEX_PROJECT_TOOL_WEIGHTS,
    "gemini_cli": GEMINI_PROJECT_TOOL_WEIGHTS,
}

# ── Friction types by agent type ──────────────────────────────────
CODEX_FRICTION_TYPES = ["exec_error", "permission_denied", "timeout", "context_limit"]
CODEX_FRICTION_DETAILS = {
    "exec_error": [
        "exec_command failed: command not found 'jq'",
        "shell command returned non-zero exit code",
        "file_write failed: permission denied on /etc/config",
    ],
    "permission_denied": [
        "User denied execution of 'rm -rf node_modules'",
        "Sandbox blocked network access",
    ],
    "timeout": [
        "Command timed out after 120s: npm install",
        "Long-running test suite exceeded timeout",
    ],
    "context_limit": [
        "Context window exhausted after reading large file",
        "Response truncated due to token limit",
    ],
}

GEMINI_FRICTION_TYPES = ["tool_error", "permission_denied", "timeout", "context_limit"]
GEMINI_FRICTION_DETAILS = {
    "tool_error": [
        "runShell failed: command not found 'jq'",
        "editFile rejected: file not found",
        "writeFile failed: permission denied",
        "grepSearch returned no results",
    ],
    "permission_denied": [
        "User denied shell execution for destructive command",
        "Blocked from writing to protected path",
    ],
    "timeout": [
        "Shell command timed out after 120s",
        "API request to external service timed out",
    ],
    "context_limit": [
        "Context window exhausted after reading large file",
        "Conversation exceeded token limit",
    ],
}

FRICTION_BY_AGENT = {
    "claude_code": (FRICTION_TYPES, FRICTION_DETAILS),
    "codex_cli": (CODEX_FRICTION_TYPES, CODEX_FRICTION_DETAILS),
    "gemini_cli": (GEMINI_FRICTION_TYPES, GEMINI_FRICTION_DETAILS),
}


def _generate_messages(
    session_type: str, msg_count: int, model: str, agent_type: str = "claude_code"
) -> list[dict]:
    """Generate synthetic transcript messages for a session."""
    responses = ASSISTANT_RESPONSES_BY_AGENT[agent_type]
    call_templates, result_templates = TOOL_TEMPLATES_BY_AGENT[agent_type]

    messages = []
    ordinal = 0

    # First human message is always the prompt
    prompt = random.choice(FIRST_PROMPTS[session_type])
    messages.append({"ordinal": ordinal, "role": "human", "content_text": prompt})
    ordinal += 1

    remaining = msg_count - 1
    while remaining > 0:
        # Assistant turn
        text = random.choice(responses)
        tool_calls = None
        if random.random() < 0.6:
            n_tools = random.randint(1, 3)
            k = min(n_tools, len(call_templates))
            tool_calls = random.sample(call_templates, k=k)
        token_count = random.randint(100, 2000)
        messages.append(
            {
                "ordinal": ordinal,
                "role": "assistant",
                "content_text": text,
                "tool_calls": tool_calls,
                "token_count": token_count,
                "model": model,
            }
        )
        ordinal += 1
        remaining -= 1

        # Tool results for each tool call
        if tool_calls and remaining > 0:
            for tc in tool_calls:
                tr_match = [t for t in result_templates if t["name"] == tc["name"]]
                tr = random.choice(tr_match) if tr_match else random.choice(result_templates)
                messages.append(
                    {
                        "ordinal": ordinal,
                        "role": "tool_result",
                        "tool_results": [
                            {"name": tr["name"], "output_preview": tr["output_preview"]}
                        ],
                    }
                )
                ordinal += 1
                remaining -= 1
                if remaining <= 0:
                    break

        # Human follow-up (not always)
        if remaining > 0 and random.random() < 0.5:
            followups = [
                "Looks good, can you also add tests?",
                "That works. Now update the documentation.",
                "Can you refactor that to be cleaner?",
                "What about error handling?",
                "Run the full test suite to make sure nothing broke.",
                "Great, let's move on to the next step.",
            ]
            messages.append(
                {
                    "ordinal": ordinal,
                    "role": "human",
                    "content_text": random.choice(followups),
                }
            )
            ordinal += 1
            remaining -= 1

    return messages


END_REASONS = ["user_exit", "conversation_end", "timeout", "error"]
PRIMARY_SUCCESS_VALUES = ["full", "partial", "none"]

# ── Hourly weights (24 hours, peaks at working hours) ──────────────
HOUR_WEIGHTS = [
    1,
    1,
    0,
    0,
    0,
    0,  # 00-05
    2,
    5,
    12,
    18,
    20,
    18,  # 06-11
    10,
    16,
    20,
    19,
    17,
    14,  # 12-17
    8,
    5,
    3,
    2,
    2,
    1,  # 18-23
]


def _weighted_choice(options: dict[str, int]) -> str:
    """Pick a key from {option: weight} dict."""
    keys = list(options.keys())
    weights = list(options.values())
    # Clamp negative weights to 0
    weights = [max(0, w) for w in weights]
    return random.choices(keys, weights=weights, k=1)[0]


def _parse_selected_agent_types() -> set[str] | None:
    """Parse optional comma-separated agent-type filter from the environment."""
    raw = os.environ.get("PRIMER_SEED_AGENT_TYPES")
    if not raw:
        return None

    selected = {part.strip() for part in raw.split(",") if part.strip()}
    invalid = sorted(selected - set(AGENT_TYPE_CONFIG))
    if invalid:
        valid = ", ".join(sorted(AGENT_TYPE_CONFIG))
        raise ValueError(
            f"Unknown agent types in PRIMER_SEED_AGENT_TYPES: {invalid}. Valid: {valid}"
        )
    return selected


def _filter_agent_mix(
    agent_mix: dict[str, int], selected_agents: set[str] | None
) -> dict[str, int]:
    """Restrict an engineer's agent mix to the requested agent types."""
    if not selected_agents:
        return dict(agent_mix)
    return {
        agent_type: weight
        for agent_type, weight in agent_mix.items()
        if agent_type in selected_agents
    }


def _scale_session_count_for_selected_agents(
    session_count: int,
    full_agent_mix: dict[str, int],
    filtered_agent_mix: dict[str, int],
) -> int:
    """Preserve expected session volume when seeding only a subset of agent types."""
    full_weight = sum(full_agent_mix.values())
    filtered_weight = sum(filtered_agent_mix.values())
    if full_weight <= 0 or filtered_weight <= 0:
        return 0

    scaled = session_count * (filtered_weight / full_weight)
    whole = int(scaled)
    if random.random() < scaled - whole:
        whole += 1
    return whole


def _lognormal_tokens(mu: float, sigma: float, scale: float = 1.0) -> int:
    """Generate log-normally distributed token count."""
    return max(100, int(random.lognormvariate(mu, sigma) * scale))


def _generate_summary(session_type: str) -> str:
    template = random.choice(SUMMARY_TEMPLATES[session_type])
    nouns_map = {
        "feature": FEATURE_NOUNS,
        "debugging": ISSUE_NOUNS,
        "refactoring": MODULE_NOUNS,
        "exploration": AREA_NOUNS,
        "documentation": TOPIC_NOUNS,
    }
    noun = random.choice(nouns_map[session_type])
    key = next(iter(template.split("{")[-1].split("}")[0:1])) if "{" in template else ""
    if key:
        return template.replace(f"{{{key}}}", noun)
    return template


def _generate_branch(session_type: str) -> str:
    template = random.choice(BRANCH_TEMPLATES[session_type])
    slug = random.choice(BRANCH_SLUGS)
    return template.format(slug=slug)


def _build_facets(
    session_type: str,
    outcome: str,
    project_name: str,
    summary: str | None,
    friction_counts: dict[str, int] | None,
    friction_detail: str | None,
    include_user_satisfaction: bool = True,
) -> dict:
    """Generate a complete facet payload for a synthetic session."""
    if outcome == "success":
        primary_success = random.choices(PRIMARY_SUCCESS_VALUES, weights=[75, 20, 5], k=1)[0]
        satisfaction_weights = [70, 22, 8]
        confidence_range = (0.84, 0.98)
    elif outcome == "partial":
        primary_success = random.choices(PRIMARY_SUCCESS_VALUES, weights=[15, 60, 25], k=1)[0]
        satisfaction_weights = [25, 45, 30]
        confidence_range = (0.7, 0.9)
    else:
        primary_success = random.choices(PRIMARY_SUCCESS_VALUES, weights=[5, 25, 70], k=1)[0]
        satisfaction_weights = [5, 25, 70]
        confidence_range = (0.58, 0.82)

    categories = GOAL_CATEGORIES_BY_TYPE[session_type]
    goal_categories = random.sample(categories, k=random.randint(1, min(2, len(categories))))
    satisfaction = None
    if include_user_satisfaction:
        satisfaction_label = random.choices(
            ["satisfied", "neutral", "dissatisfied"],
            weights=satisfaction_weights,
            k=1,
        )[0]
        satisfaction = {satisfaction_label: 1}

    return {
        "underlying_goal": f"Working on {session_type} task for {project_name}",
        "outcome": outcome,
        "session_type": session_type,
        "goal_categories": goal_categories,
        "brief_summary": summary or f"Session for {project_name}",
        "friction_counts": friction_counts,
        "friction_detail": friction_detail,
        "primary_success": primary_success,
        "user_satisfaction_counts": satisfaction,
        "confidence_score": round(random.uniform(*confidence_range), 2),
    }


def _build_tool_usages(
    persona: dict, project: dict, agent_type: str = "claude_code", project_name: str = ""
) -> list[dict]:
    """Generate tool usages combining persona and project biases."""
    if agent_type == "claude_code":
        available_tools = persona["tool_bias"]
        proj_weights = project["tool_weights"]
    else:
        agent_cfg = AGENT_TYPE_CONFIG[agent_type]
        available_tools = agent_cfg["tools"]
        agent_proj_weights = PROJECT_TOOL_WEIGHTS_BY_AGENT[agent_type]
        proj_weights = agent_proj_weights.get(project_name, {}) if agent_proj_weights else {}

    n_tools = random.randint(2, min(6, len(available_tools)))
    selected = random.sample(available_tools, k=n_tools)

    usages = []
    for tool in selected:
        base_weight = proj_weights.get(tool, 5)
        call_count = max(1, int(random.gauss(base_weight / 2, base_weight / 4)))
        usages.append({"tool_name": tool, "call_count": call_count})
    return usages


def main():
    random.seed(42)
    force_facets = _should_force_facets()
    selected_agent_types = _parse_selected_agent_types()

    # Create or fetch teams
    teams = []
    team_names = ["Platform", "Backend", "Frontend", "Mobile", "Data", "DevEx"]
    for name in team_names:
        r = httpx.post(f"{SERVER_URL}/api/v1/teams", json={"name": name}, headers=ADMIN_HEADERS)
        if r.status_code == 200:
            teams.append(r.json())
            print(f"Created team: {name} ({r.json()['id']})")
        elif r.status_code == 409:
            print(f"Team {name} already exists")

    # If teams weren't created (already existed), fetch them
    if len(teams) < len(team_names):
        r = httpx.get(f"{SERVER_URL}/api/v1/teams", headers=ADMIN_HEADERS)
        if r.status_code == 200:
            all_teams = r.json()
            teams = [t for t in all_teams if t["name"] in team_names]
            teams.sort(key=lambda t: team_names.index(t["name"]))

    # Create or fetch engineers
    engineers = []
    for name, email, team_idx, role, github_user, github_id, persona_type, agent_mix in ENGINEERS:
        team_id = teams[team_idx]["id"] if teams else None
        r = httpx.post(
            f"{SERVER_URL}/api/v1/engineers",
            json={"name": name, "email": email, "team_id": team_id},
            headers=ADMIN_HEADERS,
        )
        if r.status_code == 200:
            data = r.json()
            engineers.append(
                {**data, "persona": persona_type, "team_idx": team_idx, "agent_mix": agent_mix}
            )
            key_preview = data["api_key"][:20]
            print(f"Created engineer: {name} (persona: {persona_type}, key: {key_preview}...)")
            eng_id = data["engineer"]["id"]
            avatar = f"https://avatars.githubusercontent.com/u/{github_id}"
            httpx.patch(
                f"{SERVER_URL}/api/v1/engineers/{eng_id}",
                json={
                    "role": role,
                    "github_username": github_user,
                    "avatar_url": avatar,
                    "display_name": name,
                },
                headers=ADMIN_HEADERS,
            )
        elif r.status_code == 409:
            print(f"Engineer {email} already exists")

    # If some engineers already existed, fetch them from the API
    if len(engineers) < len(ENGINEERS):
        r = httpx.get(f"{SERVER_URL}/api/v1/engineers", headers=ADMIN_HEADERS)
        if r.status_code == 200:
            all_engs = r.json()
            eng_lookup = {e["email"]: e for e in all_engs}
            engineers = []
            for _name, email, team_idx, _role, _gh, _ghid, persona_type, agent_mix in ENGINEERS:
                if email in eng_lookup:
                    eng_data = eng_lookup[email]
                    # Rotate API key so we have a valid key for session seeding
                    # (api_key is not returned by the list endpoint)
                    rot = httpx.post(
                        f"{SERVER_URL}/api/v1/engineers/{eng_data['id']}/rotate-key",
                        headers=ADMIN_HEADERS,
                    )
                    api_key = rot.json()["api_key"] if rot.status_code == 200 else None
                    if not api_key:
                        print(f"Warning: could not get API key for {email}, skipping")
                        continue
                    engineers.append(
                        {
                            "engineer": eng_data,
                            "persona": persona_type,
                            "team_idx": team_idx,
                            "agent_mix": agent_mix,
                            "api_key": api_key,
                        }
                    )
            print(f"Fetched {len(engineers)} existing engineers for session seeding.")

    if not engineers:
        print("No engineers found. Cannot seed sessions.")
        return

    now = datetime.now()
    session_types = list(FIRST_PROMPTS.keys())
    session_type_weights = [35, 25, 15, 15, 10]  # feature-heavy
    project_names = list(PROJECTS.keys())
    total_sessions = 0

    # Assign preferred projects per engineer (2-3 each)
    engineer_projects = {}
    for eng in engineers:
        n_projects = random.randint(2, 4)
        engineer_projects[eng["engineer"]["id"]] = random.sample(
            project_names, k=min(n_projects, len(project_names))
        )

    agent_type_totals = {"claude_code": 0, "codex_cli": 0, "gemini_cli": 0}

    for eng_data in engineers:
        api_key = eng_data["api_key"]
        eng_id = eng_data["engineer"]["id"]
        persona_type = eng_data["persona"]
        persona = PERSONAS[persona_type]
        preferred_projects = engineer_projects[eng_id]
        full_agent_mix = eng_data["agent_mix"]
        eng_agent_mix = _filter_agent_mix(full_agent_mix, selected_agent_types)
        if not eng_agent_mix:
            continue
        eng_sessions = 0

        for day_offset in range(90):
            day = now - timedelta(days=day_offset)
            is_weekend = day.weekday() >= 5

            # Skip most weekends for non-power users
            if is_weekend and random.random() > persona["weekend_factor"]:
                continue

            lo, hi = persona["sessions_per_day"]
            if is_weekend:
                lo, hi = 0, max(1, hi // 3)
            n_sessions = random.randint(lo, hi)
            n_sessions = _scale_session_count_for_selected_agents(
                n_sessions,
                full_agent_mix=full_agent_mix,
                filtered_agent_mix=eng_agent_mix,
            )

            for _ in range(n_sessions):
                session_id = str(uuid.uuid4())

                # Pick agent type for this session
                agent_type = _weighted_choice(eng_agent_mix)
                agent_cfg = AGENT_TYPE_CONFIG[agent_type]

                # Pick time weighted toward working hours
                hour = random.choices(range(24), weights=HOUR_WEIGHTS, k=1)[0]
                minute = random.randint(0, 59)
                started_at = day.replace(hour=hour, minute=minute, second=random.randint(0, 59))

                # Duration (log-normal)
                dur_lo, dur_hi = persona["duration_range"]
                duration = max(dur_lo, min(dur_hi, int(random.lognormvariate(math.log(600), 0.8))))

                ended_at = started_at + timedelta(seconds=duration)

                # Messages (correlate with duration)
                msg_count = max(3, int(duration / 30 + random.gauss(0, 3)))
                user_msgs = max(1, msg_count // 2 + random.randint(-2, 2))
                assistant_msgs = msg_count - user_msgs

                # Session type
                session_type = random.choices(session_types, weights=session_type_weights, k=1)[0]

                # Project (biased toward preferred)
                if random.random() < 0.8:
                    project_name = random.choice(preferred_projects)
                else:
                    project_name = random.choice(project_names)
                project = PROJECTS[project_name]

                # Tool usages (agent-specific)
                tool_usages = _build_tool_usages(
                    persona, project, agent_type=agent_type, project_name=project_name
                )
                tool_count = sum(t["call_count"] for t in tool_usages)

                # Model (agent-specific weights)
                if agent_type == "claude_code":
                    model_weights = persona["model_weights"]
                else:
                    model_weights = agent_cfg["model_weights"][persona_type]
                model = _weighted_choice(model_weights)

                # Tokens (log-normal, scaled by persona + model)
                token_scale = persona["token_scale"]
                if "opus" in model:
                    token_scale *= 1.8
                elif "haiku" in model:
                    token_scale *= 0.5
                elif (
                    model == "gpt-5.3-codex"
                    or model == "gpt-5.2"
                    or model == "gpt-5.4"
                    or (model.startswith("gpt-5") and "mini" not in model)
                    or model == "gemini-2.5-pro"
                ):
                    token_scale *= 1.6  # reasoning models produce more tokens
                elif model in ("gpt-4.1-nano", "gemini-2.0-flash"):
                    token_scale *= 0.5
                elif "flash" in model or "mini" in model:
                    token_scale *= 0.7

                inp_tokens = _lognormal_tokens(8.5, 1.0, token_scale)
                out_tokens = _lognormal_tokens(7.5, 1.0, token_scale)

                # Cache tokens (agent-specific probability)
                cache_prob = {"claude_code": 0.5, "codex_cli": 0.35, "gemini_cli": 0.3}
                cache_read = 0
                cache_creation = 0
                if random.random() < cache_prob[agent_type]:
                    cache_read = int(inp_tokens * random.uniform(0.1, 0.6))
                    cache_creation = int(inp_tokens * random.uniform(0.02, 0.15))

                # Model usages (sometimes split across models within same agent)
                model_usages = []
                if random.random() < 0.15:
                    others = [m for m in model_weights if m != model]
                    if others:
                        secondary = random.choice(others)
                        split = random.uniform(0.6, 0.9)
                        model_usages = [
                            {
                                "model_name": model,
                                "input_tokens": int(inp_tokens * split),
                                "output_tokens": int(out_tokens * split),
                                "cache_read_tokens": int(cache_read * split),
                                "cache_creation_tokens": int(cache_creation * split),
                            },
                            {
                                "model_name": secondary,
                                "input_tokens": int(inp_tokens * (1 - split)),
                                "output_tokens": int(out_tokens * (1 - split)),
                                "cache_read_tokens": int(cache_read * (1 - split)),
                                "cache_creation_tokens": int(cache_creation * (1 - split)),
                            },
                        ]
                    else:
                        model_usages = [
                            {
                                "model_name": model,
                                "input_tokens": inp_tokens,
                                "output_tokens": out_tokens,
                                "cache_read_tokens": cache_read,
                                "cache_creation_tokens": cache_creation,
                            }
                        ]
                else:
                    model_usages = [
                        {
                            "model_name": model,
                            "input_tokens": inp_tokens,
                            "output_tokens": out_tokens,
                            "cache_read_tokens": cache_read,
                            "cache_creation_tokens": cache_creation,
                        }
                    ]

                # Outcome (combine persona + project bias)
                outcome_weights = {}
                for k, v in persona["outcome_weights"].items():
                    outcome_weights[k] = v + project["outcome_bias"].get(k, 0)
                outcome = _weighted_choice(outcome_weights)

                # Friction (agent-specific types, more likely on failures)
                friction_types, friction_details = FRICTION_BY_AGENT[agent_type]
                friction_counts = None
                friction_detail = None
                friction_prob = (
                    0.08 if outcome == "success" else 0.25 if outcome == "partial" else 0.4
                )
                if random.random() < friction_prob:
                    ft = random.choice(friction_types)
                    friction_counts = {ft: random.randint(1, 4)}
                    if random.random() < 0.7:
                        friction_detail = random.choice(friction_details.get(ft, ["Unspecified"]))

                # First prompt
                first_prompt = random.choice(FIRST_PROMPTS[session_type])

                # Summary (80% of sessions have one)
                summary = _generate_summary(session_type) if random.random() < 0.8 else None

                facets = None
                if force_facets or random.random() < 0.85:
                    facets = _build_facets(
                        session_type=session_type,
                        outcome=outcome,
                        project_name=project_name,
                        summary=summary,
                        friction_counts=friction_counts,
                        friction_detail=friction_detail,
                        include_user_satisfaction=random.random() < 0.6,
                    )

                # Generate transcript messages (agent-specific)
                session_messages = _generate_messages(
                    session_type, msg_count, model, agent_type=agent_type
                )

                # Git data
                git_branch = _generate_branch(session_type)
                git_remote_url = GIT_REPOS.get(project_name)
                eng_name = eng_data["engineer"]["name"]
                commits = _generate_commits(
                    session_type, started_at, ended_at, eng_name, git_branch
                )

                # Agent-specific version and permission mode
                agent_version = random.choice(agent_cfg["versions"])
                perm_modes = agent_cfg["permission_modes"]
                permission_mode = random.choice(perm_modes)

                payload = {
                    "session_id": session_id,
                    "api_key": api_key,
                    "agent_type": agent_type,
                    "project_name": project_name,
                    "git_branch": git_branch,
                    "git_remote_url": git_remote_url,
                    "commits": commits,
                    "agent_version": agent_version,
                    "permission_mode": permission_mode,
                    "end_reason": (
                        random.choice(END_REASONS)
                        if outcome != "success"
                        else random.choices(END_REASONS, weights=[60, 30, 5, 5], k=1)[0]
                    ),
                    "started_at": started_at.isoformat(),
                    "ended_at": ended_at.isoformat(),
                    "duration_seconds": duration,
                    "message_count": msg_count,
                    "user_message_count": user_msgs,
                    "assistant_message_count": assistant_msgs,
                    "tool_call_count": tool_count,
                    "input_tokens": inp_tokens,
                    "output_tokens": out_tokens,
                    "cache_read_tokens": cache_read,
                    "cache_creation_tokens": cache_creation,
                    "primary_model": model,
                    "first_prompt": first_prompt,
                    "summary": summary,
                    "tool_usages": tool_usages,
                    "model_usages": model_usages,
                    "messages": session_messages,
                    "facets": facets,
                }
                r = httpx.post(f"{SERVER_URL}/api/v1/ingest/session", json=payload)
                if r.status_code == 200:
                    eng_sessions += 1
                    total_sessions += 1
                    agent_type_totals[agent_type] += 1

        eng_name = eng_data["engineer"]["name"]
        print(f"Seeded {eng_sessions} sessions for {eng_name} ({eng_data['persona']})")

    print(f"\nSeed complete! Total sessions: {total_sessions}")
    print(f"  claude_code: {agent_type_totals['claude_code']}")
    print(f"  codex_cli:   {agent_type_totals['codex_cli']}")
    print(f"  gemini_cli:  {agent_type_totals['gemini_cli']}")

    # ── Seed FinOps budgets (idempotent) ──────────────────────────────
    seed_budgets(teams)


def seed_budgets(teams: list[dict]) -> None:
    """Create sample budgets. Skips any that already exist (matched by name)."""
    # Fetch existing budget names so we can skip duplicates
    r = httpx.get(f"{SERVER_URL}/api/v1/finops/budgets", headers=ADMIN_HEADERS)
    existing_names: set[str] = set()
    if r.status_code == 200:
        existing_names = {b["name"] for b in r.json()}

    team_by_name = {t["name"]: t["id"] for t in teams}

    budget_defs = [
        # Org-wide budgets (no team_id)
        {
            "name": "Org Monthly API Budget",
            "amount": 5000.0,
            "period": "monthly",
            "alert_threshold_pct": 80,
        },
        {
            "name": "Org Quarterly API Budget",
            "amount": 12000.0,
            "period": "quarterly",
            "alert_threshold_pct": 75,
        },
        # Per-team budgets
        {
            "name": "Platform Team Monthly",
            "team_id": team_by_name.get("Platform"),
            "amount": 2000.0,
            "period": "monthly",
            "alert_threshold_pct": 85,
        },
        {
            "name": "Backend Team Monthly",
            "team_id": team_by_name.get("Backend"),
            "amount": 1800.0,
            "period": "monthly",
            "alert_threshold_pct": 80,
        },
        {
            "name": "Frontend Team Monthly",
            "team_id": team_by_name.get("Frontend"),
            "amount": 1200.0,
            "period": "monthly",
            "alert_threshold_pct": 90,
        },
        {
            "name": "Mobile Team Monthly",
            "team_id": team_by_name.get("Mobile"),
            "amount": 800.0,
            "period": "monthly",
            "alert_threshold_pct": 85,
        },
        {
            "name": "Data Team Monthly",
            "team_id": team_by_name.get("Data"),
            "amount": 2500.0,
            "period": "monthly",
            "alert_threshold_pct": 75,
        },
        {
            "name": "DevEx Team Monthly",
            "team_id": team_by_name.get("DevEx"),
            "amount": 1500.0,
            "period": "monthly",
            "alert_threshold_pct": 80,
        },
    ]

    created = 0
    for bdef in budget_defs:
        if bdef["name"] in existing_names:
            print(f"Budget '{bdef['name']}' already exists — skipping")
            continue
        r = httpx.post(
            f"{SERVER_URL}/api/v1/finops/budgets",
            json=bdef,
            headers=ADMIN_HEADERS,
        )
        if r.status_code == 201:
            created += 1
            print(f"Created budget: {bdef['name']} (${bdef['amount']:.0f}/{bdef['period']})")
        else:
            print(f"Failed to create budget '{bdef['name']}': {r.status_code} {r.text}")

    print(f"\nBudgets: {created} created, {len(existing_names)} already existed")


if __name__ == "__main__":
    main()
