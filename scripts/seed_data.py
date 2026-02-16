"""Seed the database with realistic test data for development."""

import math
import random
import uuid
from datetime import datetime, timedelta

import httpx

SERVER_URL = "http://localhost:8000"
ADMIN_KEY = "primer-admin-dev-key"
ADMIN_HEADERS = {"x-admin-key": ADMIN_KEY}

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
        "tool_bias": ["Read", "Edit", "Write", "Bash", "Grep", "Glob", "Task"],
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
        "tool_bias": ["Read", "Edit", "Bash", "Grep", "Glob"],
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
        "tool_bias": ["Read", "Bash", "Grep"],
        "token_scale": 0.6,
        "duration_range": (60, 2400),
    },
}

ENGINEERS = [
    ("Alice Chen", "alice@example.com", 0, "admin", "alicechen", 1001, "power_user"),
    ("Bob Smith", "bob@example.com", 0, "team_lead", "bobsmith", 1002, "moderate"),
    ("Carol Davis", "carol@example.com", 1, "team_lead", "caroldavis", 1003, "power_user"),
    ("Dan Wilson", "dan@example.com", 1, "engineer", "danwilson", 1004, "moderate"),
    ("Eve Martinez", "eve@example.com", 2, "engineer", "evemartinez", 1005, "occasional"),
    ("Frank Lee", "frank@example.com", 0, "engineer", "franklee", 1006, "moderate"),
    ("Grace Kim", "grace@example.com", 1, "engineer", "gracekim", 1007, "new_hire"),
    ("Hiro Tanaka", "hiro@example.com", 2, "engineer", "hirotanaka", 1008, "occasional"),
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
            "Task": 5,
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
            "Task": 10,
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
            "Task": 15,
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
            "Task": 5,
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
            "Task": 10,
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
            "Task": 10,
        },
        "outcome_bias": {"success": -3, "partial": 3, "failure": 3, "abandoned": 0},
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
    "Bob Smith": "bob@example.com",
    "Carol Davis": "carol@example.com",
    "Dan Wilson": "dan@example.com",
    "Eve Martinez": "eve@example.com",
    "Frank Lee": "frank@example.com",
    "Grace Kim": "grace@example.com",
    "Hiro Tanaka": "hiro@example.com",
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

TOOL_CALL_TEMPLATES = [
    {"name": "Read", "input_preview": '{"file_path": "src/main.py"}'},
    {"name": "Edit", "input_preview": '{"file_path": "src/main.py", "old_string": "..."}'},
    {"name": "Write", "input_preview": '{"file_path": "src/new_file.py", "content": "..."}'},
    {"name": "Bash", "input_preview": '{"command": "pytest -v tests/"}'},
    {"name": "Grep", "input_preview": '{"pattern": "def handle_", "path": "src/"}'},
    {"name": "Glob", "input_preview": '{"pattern": "**/*.py"}'},
]

TOOL_RESULT_TEMPLATES = [
    {"name": "Read", "output_preview": "import os\nimport sys\n\ndef main():\n    ..."},
    {"name": "Edit", "output_preview": "File updated successfully."},
    {"name": "Bash", "output_preview": "PASSED 12 tests in 0.5s"},
    {"name": "Grep", "output_preview": "src/handler.py:15: def handle_request"},
    {"name": "Glob", "output_preview": "src/main.py\nsrc/utils.py\nsrc/handler.py"},
]


def _generate_messages(session_type: str, msg_count: int, model: str) -> list[dict]:
    """Generate synthetic transcript messages for a session."""
    messages = []
    ordinal = 0

    # First human message is always the prompt
    prompt = random.choice(FIRST_PROMPTS[session_type])
    messages.append({"ordinal": ordinal, "role": "human", "content_text": prompt})
    ordinal += 1

    remaining = msg_count - 1
    while remaining > 0:
        # Assistant turn
        text = random.choice(ASSISTANT_RESPONSES)
        tool_calls = None
        if random.random() < 0.6:
            n_tools = random.randint(1, 3)
            k = min(n_tools, len(TOOL_CALL_TEMPLATES))
            tool_calls = random.sample(TOOL_CALL_TEMPLATES, k=k)
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
                tr_match = [t for t in TOOL_RESULT_TEMPLATES if t["name"] == tc["name"]]
                tr = random.choice(tr_match) if tr_match else random.choice(TOOL_RESULT_TEMPLATES)
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


CLAUDE_VERSIONS = ["1.0.17", "1.0.16", "1.0.15", "1.0.14", "1.0.13"]
PERMISSION_MODES = ["default", "plan", "bypassPermissions"]
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


def _build_tool_usages(persona: dict, project: dict) -> list[dict]:
    """Generate tool usages combining persona and project biases."""
    available_tools = persona["tool_bias"]
    proj_weights = project["tool_weights"]

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

    # Create teams
    teams = []
    for name in ["Platform", "Backend", "Frontend"]:
        r = httpx.post(f"{SERVER_URL}/api/v1/teams", json={"name": name}, headers=ADMIN_HEADERS)
        if r.status_code == 200:
            teams.append(r.json())
            print(f"Created team: {name} ({r.json()['id']})")
        elif r.status_code == 409:
            print(f"Team {name} already exists")

    # Create engineers
    engineers = []
    for name, email, team_idx, role, _github_user, _github_id, persona_type in ENGINEERS:
        team_id = teams[team_idx]["id"] if teams else None
        r = httpx.post(
            f"{SERVER_URL}/api/v1/engineers",
            json={"name": name, "email": email, "team_id": team_id},
            headers=ADMIN_HEADERS,
        )
        if r.status_code == 200:
            data = r.json()
            engineers.append({**data, "persona": persona_type, "team_idx": team_idx})
            key_preview = data["api_key"][:20]
            print(f"Created engineer: {name} (persona: {persona_type}, key: {key_preview}...)")
            eng_id = data["engineer"]["id"]
            httpx.patch(
                f"{SERVER_URL}/api/v1/engineers/{eng_id}",
                json={"role": role},
                headers=ADMIN_HEADERS,
            )
        elif r.status_code == 409:
            print(f"Engineer {email} already exists")

    if not engineers:
        print("No new engineers created. Skipping session seeding.")
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

    for eng_data in engineers:
        api_key = eng_data["api_key"]
        eng_id = eng_data["engineer"]["id"]
        persona = PERSONAS[eng_data["persona"]]
        preferred_projects = engineer_projects[eng_id]
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

            for _ in range(n_sessions):
                session_id = str(uuid.uuid4())

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

                # Tool usages
                tool_usages = _build_tool_usages(persona, project)
                tool_count = sum(t["call_count"] for t in tool_usages)

                # Model (persona-weighted)
                model = _weighted_choice(persona["model_weights"])

                # Tokens (log-normal, scaled by persona + model)
                token_scale = persona["token_scale"]
                if "opus" in model:
                    token_scale *= 1.8  # Opus sessions tend to be larger
                elif "haiku" in model:
                    token_scale *= 0.5

                inp_tokens = _lognormal_tokens(8.5, 1.0, token_scale)
                out_tokens = _lognormal_tokens(7.5, 1.0, token_scale)

                # Cache tokens (50% of sessions have cache)
                cache_read = 0
                cache_creation = 0
                if random.random() < 0.5:
                    cache_read = int(inp_tokens * random.uniform(0.1, 0.6))
                    cache_creation = int(inp_tokens * random.uniform(0.02, 0.15))

                # Model usages (sometimes split across models)
                model_usages = []
                if random.random() < 0.15:
                    # Multi-model session
                    secondary = random.choice([m for m in persona["model_weights"] if m != model])
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

                # Outcome (combine persona + project bias)
                outcome_weights = {}
                for k, v in persona["outcome_weights"].items():
                    outcome_weights[k] = v + project["outcome_bias"].get(k, 0)
                outcome = _weighted_choice(outcome_weights)

                # Friction (more likely on failures)
                friction_counts = None
                friction_detail = None
                friction_prob = (
                    0.08 if outcome == "success" else 0.25 if outcome == "partial" else 0.4
                )
                if random.random() < friction_prob:
                    ft = random.choice(FRICTION_TYPES)
                    friction_counts = {ft: random.randint(1, 4)}
                    if random.random() < 0.7:
                        friction_detail = random.choice(FRICTION_DETAILS.get(ft, ["Unspecified"]))

                # First prompt
                first_prompt = random.choice(FIRST_PROMPTS[session_type])

                # Summary (80% of sessions have one)
                summary = _generate_summary(session_type) if random.random() < 0.8 else None

                # Facets (85% of sessions)
                facets = None
                if random.random() < 0.85:
                    # Primary success — correlate with outcome
                    if outcome == "success":
                        ps = random.choices(PRIMARY_SUCCESS_VALUES, weights=[75, 20, 5], k=1)[0]
                    elif outcome == "partial":
                        ps = random.choices(PRIMARY_SUCCESS_VALUES, weights=[15, 60, 25], k=1)[0]
                    else:
                        ps = random.choices(PRIMARY_SUCCESS_VALUES, weights=[5, 25, 70], k=1)[0]

                    # Goal categories (1-2 per session, type-specific)
                    cats = GOAL_CATEGORIES_BY_TYPE[session_type]
                    n_cats = random.randint(1, min(2, len(cats)))
                    goal_cats = random.sample(cats, k=n_cats)

                    # User satisfaction (60% of sessions with facets)
                    satisfaction = None
                    if random.random() < 0.6:
                        if outcome == "success":
                            sat = random.choices(
                                ["satisfied", "neutral", "dissatisfied"],
                                weights=[70, 22, 8],
                                k=1,
                            )[0]
                        elif outcome == "partial":
                            sat = random.choices(
                                ["satisfied", "neutral", "dissatisfied"],
                                weights=[25, 45, 30],
                                k=1,
                            )[0]
                        else:
                            sat = random.choices(
                                ["satisfied", "neutral", "dissatisfied"],
                                weights=[5, 25, 70],
                                k=1,
                            )[0]
                        satisfaction = {sat: 1}

                    facets = {
                        "underlying_goal": f"Working on {session_type} task for {project_name}",
                        "outcome": outcome,
                        "session_type": session_type,
                        "goal_categories": goal_cats,
                        "brief_summary": summary or f"Session for {project_name}",
                        "friction_counts": friction_counts,
                        "friction_detail": friction_detail,
                        "primary_success": ps,
                        "user_satisfaction_counts": satisfaction,
                    }

                # Generate transcript messages
                session_messages = _generate_messages(session_type, msg_count, model)

                # Git data
                git_branch = _generate_branch(session_type)
                git_remote_url = GIT_REPOS.get(project_name)
                eng_name = eng_data["engineer"]["name"]
                commits = _generate_commits(
                    session_type, started_at, ended_at, eng_name, git_branch
                )

                payload = {
                    "session_id": session_id,
                    "api_key": api_key,
                    "project_name": project_name,
                    "git_branch": git_branch,
                    "git_remote_url": git_remote_url,
                    "commits": commits,
                    "claude_version": random.choice(CLAUDE_VERSIONS),
                    "permission_mode": random.choice(PERMISSION_MODES),
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

        eng_name = eng_data["engineer"]["name"]
        print(f"Seeded {eng_sessions} sessions for {eng_name} ({eng_data['persona']})")

    print(f"\nSeed complete! Total sessions: {total_sessions}")


if __name__ == "__main__":
    main()
