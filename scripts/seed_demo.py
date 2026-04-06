"""Extended demo seed script that builds on seed_data.py.

Creates a narrative-quality demo dataset with all data types:
- Cursor sessions as a 4th agent type
- GitRepository records with AI readiness data
- PullRequests linked to sessions and engineers
- ReviewFindings from automated code review bots
- SessionCustomization snapshots (MCP, skills, subagents)
- Interventions and experiments
- Alerts and AlertConfigs
- Post-seed derived data (workflow profiles, facet normalization, anomaly detection)

Usage:
    # Start the Primer server first, then:
    python scripts/seed_demo.py

    # Or skip the base seed if already run:
    PRIMER_SEED_SKIP_BASE=1 python scripts/seed_demo.py
"""

import os
import random
import sys
import uuid
from datetime import datetime, timedelta

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so we can import primer and seed_data
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if os.path.join(PROJECT_ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from primer.common.config import settings  # noqa: E402, I001
from primer.common.models import (  # noqa: E402
    Alert,
    AlertConfig,
    Engineer,
    GitRepository,
    Intervention,
    PullRequest,
    ReviewFinding,
    Session as SessionModel,
    SessionCommit,
    SessionCustomization,
    SessionFacets,
    Team,
    ToolUsage,
)

# Re-use constants from the base seed script
from seed_data import (  # noqa: E402
    ADMIN_HEADERS,
    COMMIT_MESSAGES,
    ENGINEERS,
    FIRST_PROMPTS,
    HOUR_WEIGHTS,
    PERSONAS,
    PROJECTS,
    SERVER_URL,
    _build_facets,
    _generate_branch,
    _generate_summary,
    _lognormal_tokens,
    _weighted_choice,
)

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
random.seed(42)

# ---------------------------------------------------------------------------
# Database setup (direct SQLAlchemy access for records the API cannot create)
# ---------------------------------------------------------------------------
DATABASE_URL = settings.database_url


def _make_engine_and_session():
    connect_args = {}
    if "sqlite" in DATABASE_URL:
        connect_args["check_same_thread"] = False
    engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine, factory


ENGINE, DBSessionFactory = _make_engine_and_session()


def _skip_base_seed() -> bool:
    raw = os.environ.get("PRIMER_SEED_SKIP_BASE", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# ============================================================================
# 1. Cursor agent type configuration
# ============================================================================

CURSOR_AGENT_CONFIG = {
    "model_weights": {
        "power_user": {
            "claude-sonnet-4-5": 40,
            "gpt-4o": 30,
            "gemini-2.5-pro": 20,
            "claude-opus-4": 10,
        },
        "moderate": {
            "claude-sonnet-4-5": 45,
            "gpt-4o": 35,
            "gemini-2.5-pro": 15,
            "claude-opus-4": 5,
        },
        "occasional": {
            "claude-sonnet-4-5": 40,
            "gpt-4o": 40,
            "gemini-2.5-pro": 15,
            "claude-opus-4": 5,
        },
        "new_hire": {
            "claude-sonnet-4-5": 50,
            "gpt-4o": 35,
            "gemini-2.5-pro": 10,
            "claude-opus-4": 5,
        },
        "ramping_up": {
            "claude-sonnet-4-5": 45,
            "gpt-4o": 30,
            "gemini-2.5-pro": 20,
            "claude-opus-4": 5,
        },
    },
    "tools": [
        "composer_edit",
        "composer_read",
        "terminal_command",
        "ai_fix",
        "codebase_search",
        "file_search",
        "web_search",
    ],
    "versions": ["0.48.7", "0.48.5", "0.47.9", "0.47.4"],
    "permission_modes": ["normal", "agent"],
}

CURSOR_PROJECT_TOOL_WEIGHTS = {
    "api-service": {
        "composer_edit": 25,
        "composer_read": 20,
        "terminal_command": 25,
        "ai_fix": 10,
        "codebase_search": 10,
        "file_search": 5,
        "web_search": 5,
    },
    "web-app": {
        "composer_edit": 30,
        "composer_read": 20,
        "terminal_command": 10,
        "ai_fix": 15,
        "codebase_search": 10,
        "file_search": 10,
        "web_search": 5,
    },
    "cli-tool": {
        "composer_edit": 20,
        "composer_read": 15,
        "terminal_command": 35,
        "ai_fix": 10,
        "codebase_search": 10,
        "file_search": 5,
        "web_search": 5,
    },
    "shared-lib": {
        "composer_edit": 20,
        "composer_read": 25,
        "terminal_command": 15,
        "ai_fix": 10,
        "codebase_search": 15,
        "file_search": 10,
        "web_search": 5,
    },
    "data-pipeline": {
        "composer_edit": 20,
        "composer_read": 15,
        "terminal_command": 30,
        "ai_fix": 10,
        "codebase_search": 10,
        "file_search": 5,
        "web_search": 10,
    },
    "mobile-app": {
        "composer_edit": 25,
        "composer_read": 20,
        "terminal_command": 15,
        "ai_fix": 15,
        "codebase_search": 10,
        "file_search": 10,
        "web_search": 5,
    },
    "infra-config": {
        "composer_edit": 15,
        "composer_read": 10,
        "terminal_command": 35,
        "ai_fix": 10,
        "codebase_search": 15,
        "file_search": 10,
        "web_search": 5,
    },
    "ml-pipeline": {
        "composer_edit": 20,
        "composer_read": 15,
        "terminal_command": 25,
        "ai_fix": 10,
        "codebase_search": 10,
        "file_search": 5,
        "web_search": 15,
    },
}

CURSOR_FRICTION_TYPES = ["composer_error", "timeout", "context_limit", "ai_fix_failure"]
CURSOR_FRICTION_DETAILS = {
    "composer_error": [
        "Composer edit failed: could not locate symbol in file",
        "Composer read timed out reading large file",
        "Composer edit produced invalid diff",
    ],
    "timeout": [
        "Terminal command timed out after 120s: npm install",
        "AI request timed out waiting for model response",
    ],
    "context_limit": [
        "Context window exhausted mid-conversation",
        "File too large for inline context",
    ],
    "ai_fix_failure": [
        "AI fix suggested incorrect import path",
        "Suggested fix introduced type error",
    ],
}

CURSOR_TOOL_CALL_TEMPLATES = [
    {"name": "composer_edit", "input_preview": '{"file": "src/main.py", "instruction": "..."}'},
    {"name": "composer_read", "input_preview": '{"file": "src/main.py"}'},
    {"name": "terminal_command", "input_preview": '{"command": "pytest -v tests/"}'},
    {"name": "ai_fix", "input_preview": '{"error": "TypeError: ...", "file": "src/main.py"}'},
    {"name": "codebase_search", "input_preview": '{"query": "def handle_request"}'},
    {"name": "file_search", "input_preview": '{"pattern": "*.py"}'},
    {"name": "web_search", "input_preview": '{"query": "python async patterns"}'},
]

CURSOR_TOOL_RESULT_TEMPLATES = [
    {"name": "composer_edit", "output_preview": "Applied edit to src/main.py successfully."},
    {"name": "composer_read", "output_preview": "import os\nimport sys\n\ndef main():\n    ..."},
    {"name": "terminal_command", "output_preview": "PASSED 12 tests in 0.5s"},
    {"name": "ai_fix", "output_preview": "Applied fix: added missing import statement."},
    {"name": "codebase_search", "output_preview": "Found 5 results across 3 files."},
    {"name": "file_search", "output_preview": "src/main.py\nsrc/utils.py\nsrc/handler.py"},
    {"name": "web_search", "output_preview": "Found 3 relevant results."},
]

CURSOR_ASSISTANT_RESPONSES = [
    "I'll edit the file using Composer.",
    "Let me read the current file first.",
    "Running the terminal command to verify.",
    "I'll search the codebase for that pattern.",
    "Applying the AI fix to resolve the error.",
    "Let me search for the relevant files.",
    "The edit has been applied successfully.",
    "Here's what I found in the codebase.",
    "Let me check the web for the latest approach.",
    "Changes applied. Here's the summary.",
]

# Engineers who also use Cursor (a subset — mostly frontend and moderate+ users)
CURSOR_ENGINEER_EMAILS = {
    "alice@example.com",  # power_user — tries everything
    "frank@example.com",  # power_user, already codex-heavy → also uses cursor
    "eve@example.com",  # team_lead, frontend
    "lily@example.com",  # ramping_up, frontend
    "oscar@example.com",  # new_hire, already gemini-heavy
    "sofia@example.com",  # moderate, mobile
    "chris@example.com",  # moderate, data
    "kenji@example.com",  # team_lead, devex
    "fatima@example.com",  # ramping_up, devex
}

# ============================================================================
# 2. GitRepository records with AI readiness data
# ============================================================================

REPO_CONFIGS = {
    "api-service": {
        "full_name": "acme-corp/api-service",
        "primary_language": "Python",
        "language_breakdown": {"Python": 78, "Shell": 10, "Dockerfile": 7, "YAML": 5},
        "repo_size_kb": 45200,
        "has_claude_md": True,
        "has_agents_md": True,
        "has_claude_dir": True,
        "ai_readiness_score": 92.0,
        "has_test_harness": True,
        "has_ci_pipeline": True,
        "test_maturity_score": 88.0,
    },
    "web-app": {
        "full_name": "acme-corp/web-app",
        "primary_language": "TypeScript",
        "language_breakdown": {"TypeScript": 72, "CSS": 15, "HTML": 8, "JavaScript": 5},
        "repo_size_kb": 62300,
        "has_claude_md": True,
        "has_agents_md": False,
        "has_claude_dir": True,
        "ai_readiness_score": 78.0,
        "has_test_harness": True,
        "has_ci_pipeline": True,
        "test_maturity_score": 72.0,
    },
    "cli-tool": {
        "full_name": "acme-corp/cli-tool",
        "primary_language": "Python",
        "language_breakdown": {"Python": 88, "Shell": 8, "Makefile": 4},
        "repo_size_kb": 12400,
        "has_claude_md": True,
        "has_agents_md": True,
        "has_claude_dir": False,
        "ai_readiness_score": 85.0,
        "has_test_harness": True,
        "has_ci_pipeline": True,
        "test_maturity_score": 91.0,
    },
    "shared-lib": {
        "full_name": "acme-corp/shared-lib",
        "primary_language": "Python",
        "language_breakdown": {"Python": 92, "TOML": 5, "Markdown": 3},
        "repo_size_kb": 8700,
        "has_claude_md": True,
        "has_agents_md": False,
        "has_claude_dir": False,
        "ai_readiness_score": 65.0,
        "has_test_harness": True,
        "has_ci_pipeline": True,
        "test_maturity_score": 95.0,
    },
    "data-pipeline": {
        "full_name": "acme-corp/data-pipeline",
        "primary_language": "Python",
        "language_breakdown": {"Python": 70, "SQL": 18, "Shell": 7, "YAML": 5},
        "repo_size_kb": 34500,
        "has_claude_md": False,
        "has_agents_md": False,
        "has_claude_dir": False,
        "ai_readiness_score": 35.0,
        "has_test_harness": True,
        "has_ci_pipeline": True,
        "test_maturity_score": 58.0,
    },
    "mobile-app": {
        "full_name": "acme-corp/mobile-app",
        "primary_language": "TypeScript",
        "language_breakdown": {
            "TypeScript": 65,
            "Objective-C": 12,
            "Kotlin": 12,
            "JSON": 6,
            "YAML": 5,
        },
        "repo_size_kb": 78900,
        "has_claude_md": True,
        "has_agents_md": False,
        "has_claude_dir": False,
        "ai_readiness_score": 52.0,
        "has_test_harness": True,
        "has_ci_pipeline": True,
        "test_maturity_score": 64.0,
    },
    "infra-config": {
        "full_name": "acme-corp/infra-config",
        "primary_language": "HCL",
        "language_breakdown": {"HCL": 55, "YAML": 25, "Shell": 15, "Python": 5},
        "repo_size_kb": 15600,
        "has_claude_md": True,
        "has_agents_md": True,
        "has_claude_dir": True,
        "ai_readiness_score": 88.0,
        "has_test_harness": False,
        "has_ci_pipeline": True,
        "test_maturity_score": 30.0,
    },
    "ml-pipeline": {
        "full_name": "acme-corp/ml-pipeline",
        "primary_language": "Python",
        "language_breakdown": {"Python": 75, "Jupyter": 12, "Shell": 8, "YAML": 5},
        "repo_size_kb": 52100,
        "has_claude_md": False,
        "has_agents_md": False,
        "has_claude_dir": False,
        "ai_readiness_score": 28.0,
        "has_test_harness": True,
        "has_ci_pipeline": False,
        "test_maturity_score": 42.0,
    },
}

# ============================================================================
# 3. PR title templates
# ============================================================================

PR_TITLE_TEMPLATES = {
    "feature": [
        "feat: add {slug} support",
        "feat: implement {slug} endpoint",
        "feat({project}): add {slug} handler",
        "Add {slug} functionality",
        "feat: {slug} integration",
    ],
    "debugging": [
        "fix: resolve {slug} issue",
        "fix({project}): correct {slug} behavior",
        "Hotfix: {slug} regression",
        "fix: handle edge case in {slug}",
        "fix: {slug} null pointer",
    ],
    "refactoring": [
        "refactor: simplify {slug} logic",
        "chore: clean up {slug} module",
        "refactor({project}): extract {slug} service",
        "Improve {slug} code quality",
        "refactor: modernize {slug} patterns",
    ],
}

# ============================================================================
# 4. ReviewFinding title/description templates
# ============================================================================

REVIEW_FINDING_TEMPLATES = {
    "high": [
        {
            "title": "Unchecked null dereference in {file_stem}",
            "description": (
                "Potential null pointer exception when accessing object"
                " property without guard. Could cause runtime crash."
            ),
        },
        {
            "title": "SQL injection risk in query builder",
            "description": (
                "User input interpolated directly into SQL query string"
                " without parameterization. Use parameterized queries."
            ),
        },
        {
            "title": "Hardcoded secret in {file_stem}",
            "description": (
                "API key or credential appears to be hardcoded."
                " Move to environment variables or secret manager."
            ),
        },
        {
            "title": "Missing authentication check on {file_stem}",
            "description": (
                "Endpoint handler does not verify user authentication"
                " before processing request. Add auth middleware."
            ),
        },
        {
            "title": "Race condition in concurrent handler",
            "description": (
                "Shared mutable state accessed without synchronization."
                " Could lead to data corruption under load."
            ),
        },
    ],
    "medium": [
        {
            "title": "Missing error handling in {file_stem}",
            "description": (
                "Exception from downstream call is not caught and may"
                " propagate to the caller as an unhandled 500."
            ),
        },
        {
            "title": "Deprecated API usage in {file_stem}",
            "description": (
                "Function uses a deprecated API scheduled for removal. Migrate to the replacement."
            ),
        },
        {
            "title": "Unbounded query without pagination",
            "description": (
                "Database query fetches all rows without limit."
                " For large tables this could cause memory issues."
            ),
        },
        {
            "title": "Missing input validation in {file_stem}",
            "description": (
                "Request body fields are not validated before use."
                " Add schema validation to prevent unexpected data."
            ),
        },
        {
            "title": "Overly broad exception catch in {file_stem}",
            "description": (
                "Catching generic Exception hides specific errors."
                " Use targeted exception types for debugging."
            ),
        },
        {
            "title": "Missing retry logic for external API call",
            "description": (
                "HTTP request to external service has no retry."
                " Transient failures will propagate immediately."
            ),
        },
    ],
    "low": [
        {
            "title": "Unused import in {file_stem}",
            "description": (
                "Module imports a symbol that is never referenced. Remove to keep imports clean."
            ),
        },
        {
            "title": "Magic number in {file_stem}",
            "description": (
                "Numeric literal without explanation. Extract to a named constant for readability."
            ),
        },
        {
            "title": "Inconsistent naming convention in {file_stem}",
            "description": (
                "Variable name does not follow project conventions. Rename for consistency."
            ),
        },
        {
            "title": "Missing docstring on public function",
            "description": (
                "Public function lacks a docstring."
                " Add docs describing parameters and return value."
            ),
        },
        {
            "title": "TODO comment without tracking issue",
            "description": (
                "TODO comment found without a linked issue reference."
                " Create a ticket or resolve the TODO."
            ),
        },
        {
            "title": "Unnecessary type cast in {file_stem}",
            "description": ("Explicit type conversion is redundant. Remove for clarity."),
        },
    ],
}

# Realistic file paths per project type
PROJECT_FILE_PATHS = {
    "api-service": [
        "src/api/routes/auth.py",
        "src/api/routes/sessions.py",
        "src/api/routes/users.py",
        "src/api/middleware/rate_limit.py",
        "src/services/auth_service.py",
        "src/services/session_service.py",
        "src/models/user.py",
        "src/models/session.py",
        "src/utils/validators.py",
        "src/config.py",
        "tests/test_auth.py",
    ],
    "web-app": [
        "src/pages/Dashboard.tsx",
        "src/pages/Login.tsx",
        "src/components/Header.tsx",
        "src/hooks/useAuth.ts",
        "src/lib/api.ts",
        "src/lib/utils.ts",
        "src/components/SessionList.tsx",
        "src/components/Charts.tsx",
        "src/types/api.ts",
        "src/styles/globals.css",
    ],
    "cli-tool": [
        "src/cli/main.py",
        "src/cli/commands/run.py",
        "src/cli/commands/init.py",
        "src/cli/output.py",
        "src/cli/config.py",
        "src/cli/utils.py",
        "tests/test_commands.py",
        "tests/test_output.py",
    ],
    "shared-lib": [
        "src/lib/core.py",
        "src/lib/types.py",
        "src/lib/validators.py",
        "src/lib/serializers.py",
        "src/lib/exceptions.py",
        "src/lib/compat.py",
        "tests/test_core.py",
        "tests/test_validators.py",
    ],
    "data-pipeline": [
        "src/pipeline/extract.py",
        "src/pipeline/transform.py",
        "src/pipeline/load.py",
        "src/pipeline/config.py",
        "src/connectors/postgres.py",
        "src/connectors/s3.py",
        "sql/migrations/001_init.sql",
        "tests/test_pipeline.py",
    ],
    "mobile-app": [
        "src/screens/Home.tsx",
        "src/screens/Profile.tsx",
        "src/screens/Settings.tsx",
        "src/navigation/AppNavigator.tsx",
        "src/services/api.ts",
        "src/hooks/useTheme.ts",
        "src/components/Card.tsx",
        "ios/AppDelegate.m",
        "android/MainActivity.kt",
    ],
    "infra-config": [
        "terraform/main.tf",
        "terraform/variables.tf",
        "terraform/modules/vpc/main.tf",
        "terraform/modules/ecs/main.tf",
        "k8s/deployment.yaml",
        "k8s/service.yaml",
        "scripts/deploy.sh",
        "scripts/rollback.sh",
    ],
    "ml-pipeline": [
        "src/models/train.py",
        "src/models/evaluate.py",
        "src/models/predict.py",
        "src/data/preprocess.py",
        "src/data/features.py",
        "src/utils/metrics.py",
        "notebooks/exploration.ipynb",
        "tests/test_train.py",
        "config/model_config.yaml",
    ],
}

# ============================================================================
# 5. SessionCustomization templates
# ============================================================================

MCP_SERVERS = [
    ("primer", "primer", "repo_defined"),
    ("github", "github", "user_local"),
    ("linear", "linear", "user_local"),
    ("postgres", "postgres", "repo_defined"),
    ("filesystem", "filesystem", "user_local"),
    ("slack", "slack", "user_local"),
    ("sentry", "sentry", "repo_defined"),
    ("datadog", "datadog", "repo_defined"),
]

SKILLS = [
    ("commit", "Skill:commit", "repo_defined"),
    ("review-pr", "Skill:review-pr", "repo_defined"),
    ("test-driven-development", "Skill:test-driven-development", "marketplace"),
    ("debugging-strategies", "Skill:debugging-strategies", "marketplace"),
    ("code-review", "Skill:code-review", "marketplace"),
    ("refactor-safe", "Skill:refactor-safe", "user_local"),
]

SUBAGENTS = [
    ("explore", "Task:explore", "repo_defined"),
    ("python-pro", "Task:python-pro", "repo_defined"),
    ("frontend-developer", "Task:frontend-developer", "repo_defined"),
    ("typescript-pro", "Task:typescript-pro", "user_local"),
    ("rust-engineer", "Task:rust-engineer", "marketplace"),
]

COMMANDS = [
    ("/compact", "command", "repo_defined"),
    ("/review", "command", "repo_defined"),
    ("/test", "command", "user_local"),
    ("/deploy", "command", "repo_defined"),
]

# ============================================================================
# 6. Intervention templates
# ============================================================================

INTERVENTION_DEFS = [
    {
        "category": "workflow",
        "title": "Standardize commit workflow across Backend team",
        "description": (
            "Backend team has inconsistent commit patterns. Some engineers commit at the end "
            "of each session, others batch commits. Standardize on atomic commits with the "
            "Skill:commit customization enabled for all engineers."
        ),
        "status": "completed",
        "severity": "warning",
        "project_name": "api-service",
        "team_name": "Backend",
        "baseline_metrics": {
            "window_start": "2026-01-15T00:00:00",
            "window_end": "2026-02-01T00:00:00",
            "total_sessions": 185,
            "success_rate": 0.58,
            "avg_cost_per_session": 0.42,
            "friction_events": 38,
        },
        "evidence": {
            "avg_commits_per_session": 2.8,
            "sessions_with_commits_pct": 78.0,
            "improvement_pct": 73.3,
        },
    },
    {
        "category": "tooling",
        "title": "Deploy MCP server for database access",
        "description": (
            "Data team spends significant time manually querying databases during sessions. "
            "Deploying the postgres MCP server will reduce context switches and improve "
            "data exploration efficiency."
        ),
        "status": "completed",
        "severity": "info",
        "project_name": "data-pipeline",
        "team_name": "Data",
        "baseline_metrics": {
            "window_start": "2026-01-10T00:00:00",
            "window_end": "2026-02-01T00:00:00",
            "total_sessions": 142,
            "success_rate": 0.52,
            "avg_cost_per_session": 0.85,
            "friction_events": 40,
        },
        "evidence": {
            "avg_session_duration_min": 31.2,
            "friction_rate": 0.15,
            "improvement_pct": 26.6,
        },
    },
    {
        "category": "enablement",
        "title": "Add CLAUDE.md to data-pipeline repository",
        "description": (
            "The data-pipeline repo has no CLAUDE.md or AGENTS.md, resulting in a low AI "
            "readiness score (35). Adding project context will improve agent effectiveness "
            "and reduce friction from incorrect assumptions."
        ),
        "status": "in_progress",
        "severity": "warning",
        "project_name": "data-pipeline",
        "team_name": "Data",
        "baseline_metrics": {
            "window_start": "2026-02-15T00:00:00",
            "window_end": "2026-03-15T00:00:00",
            "total_sessions": 98,
            "success_rate": 0.52,
            "avg_cost_per_session": 0.78,
            "friction_events": 28,
        },
        "evidence": None,
    },
    {
        "category": "training",
        "title": "Onboarding acceleration program for new hires",
        "description": (
            "New hires (Yuki, Raj, Oscar, Zara) show 40% lower success rates in their first "
            "30 days. Implement a structured onboarding program with curated prompt templates "
            "and pair programming sessions with power users."
        ),
        "status": "in_progress",
        "severity": "info",
        "project_name": None,
        "team_name": None,
        "baseline_metrics": {
            "window_start": "2026-02-01T00:00:00",
            "window_end": "2026-03-01T00:00:00",
            "total_sessions": 320,
            "success_rate": 0.45,
            "avg_cost_per_session": 0.55,
            "friction_events": 64,
        },
        "evidence": None,
        "is_experiment": True,
        "experiment_type": "training_rollout",
        "experiment_hypothesis": (
            "Structured AI onboarding with prompt templates will reduce ramp-up time by 30% "
            "and increase new hire success rate by 20 percentage points within 30 days."
        ),
        "experiment_target_cohort": "new_hire",
        "experiment_success_criteria": (
            "Success rate >= 0.60 AND avg_ramp_days <= 20 within 30 days of program start."
        ),
    },
    {
        "category": "cost_optimization",
        "title": "Shift Frontend team to Sonnet for routine tasks",
        "description": (
            "Frontend team uses Opus for 35% of sessions including simple edits and exploration. "
            "Shifting routine tasks to Sonnet could reduce costs by ~$400/month while maintaining "
            "quality for complex tasks."
        ),
        "status": "completed",
        "severity": "info",
        "project_name": "web-app",
        "team_name": "Frontend",
        "baseline_metrics": {
            "window_start": "2026-01-01T00:00:00",
            "window_end": "2026-02-01T00:00:00",
            "total_sessions": 410,
            "success_rate": 0.67,
            "avg_cost_per_session": 0.52,
            "friction_events": 22,
        },
        "evidence": {
            "opus_usage_pct": 12.0,
            "monthly_cost": 1420.0,
            "cost_savings": 430.0,
            "quality_impact": "none_detected",
        },
    },
    {
        "category": "workflow",
        "title": "Implement plan-mode-first workflow for complex tasks",
        "description": (
            "Platform team power users who use EnterPlanMode first have 15% higher success "
            "rates on complex tasks. Roll out as a team-wide best practice."
        ),
        "status": "planned",
        "severity": "info",
        "project_name": "api-service",
        "team_name": "Platform",
        "baseline_metrics": None,
        "evidence": None,
    },
    {
        "category": "enablement",
        "title": "Create AGENTS.md for mobile-app repository",
        "description": (
            "Mobile app repo has CLAUDE.md but no AGENTS.md or .claude directory. Adding "
            "agent-specific instructions will improve multi-agent workflow quality."
        ),
        "status": "planned",
        "severity": "info",
        "project_name": "mobile-app",
        "team_name": "Mobile",
        "baseline_metrics": None,
        "evidence": None,
    },
    {
        "category": "tooling",
        "title": "Evaluate Cursor adoption for Frontend team",
        "description": (
            "Several Frontend engineers have started using Cursor alongside Claude Code. "
            "Run a controlled evaluation to compare productivity metrics across agents "
            "and determine optimal tool allocation."
        ),
        "status": "in_progress",
        "severity": "info",
        "project_name": "web-app",
        "team_name": "Frontend",
        "baseline_metrics": {
            "window_start": "2026-02-10T00:00:00",
            "window_end": "2026-03-10T00:00:00",
            "total_sessions": 265,
            "success_rate": 0.64,
            "avg_cost_per_session": 0.41,
            "friction_events": 35,
        },
        "evidence": None,
        "is_experiment": True,
        "experiment_type": "tool_change",
        "experiment_hypothesis": (
            "Cursor may offer faster session completion for frontend-specific tasks (CSS, "
            "component scaffolding) while Claude Code remains superior for complex refactoring."
        ),
        "experiment_target_cohort": "frontend_team",
        "experiment_success_criteria": (
            "Identify task categories where each agent excels, with statistical significance "
            "(p < 0.05) on success rate and duration metrics."
        ),
    },
    {
        "category": "cost_optimization",
        "title": "Implement prompt caching strategy for ml-pipeline",
        "description": (
            "ML pipeline sessions have very low cache hit rates (8%). Restructuring prompts "
            "to use consistent system prompts and context blocks should increase cache "
            "utilization and reduce costs."
        ),
        "status": "planned",
        "severity": "warning",
        "project_name": "ml-pipeline",
        "team_name": "Data",
        "baseline_metrics": None,
        "evidence": None,
    },
    {
        "category": "workflow",
        "title": "Reduce friction in infra-config Bash-heavy sessions",
        "description": (
            "Infra-config sessions have 35% Bash tool weight and elevated permission_denied "
            "friction. Pre-approve common infrastructure commands to reduce interruptions."
        ),
        "status": "completed",
        "severity": "warning",
        "project_name": "infra-config",
        "team_name": "DevEx",
        "baseline_metrics": {
            "window_start": "2026-01-20T00:00:00",
            "window_end": "2026-02-20T00:00:00",
            "total_sessions": 156,
            "success_rate": 0.71,
            "avg_cost_per_session": 0.38,
            "friction_events": 50,
        },
        "evidence": {
            "friction_rate": 0.14,
            "permission_denied_pct": 0.04,
            "sessions_analyzed": 156,
        },
    },
]

# ============================================================================
# 7. Alert definitions
# ============================================================================

ALERT_DEFS = [
    {
        "alert_type": "friction_spike",
        "severity": "high",
        "title": "Friction spike detected in Backend team",
        "message": (
            "Backend team friction rate jumped from 0.15 to 0.38 over the past 24 hours. "
            "Primary friction type: tool_error (Edit tool failures on api-service)."
        ),
        "metric_name": "friction_rate",
        "expected_value": 0.15,
        "actual_value": 0.38,
        "threshold": 0.30,
        "team_name": "Backend",
        "status": "active",
    },
    {
        "alert_type": "cost_spike",
        "severity": "medium",
        "title": "Cost spike: Data team exceeding daily average by 2.5x",
        "message": (
            "Data team daily cost reached $142.50, compared to 7-day average of $57.00. "
            "Driven by increased Opus usage in ml-pipeline sessions."
        ),
        "metric_name": "daily_cost",
        "expected_value": 57.0,
        "actual_value": 142.5,
        "threshold": 200.0,
        "team_name": "Data",
        "status": "acknowledged",
    },
    {
        "alert_type": "success_rate_drop",
        "severity": "high",
        "title": "Success rate drop for new hires",
        "message": (
            "New hire success rate dropped from 0.48 to 0.31 this week. "
            "Particularly impacted: Oscar Mendez (0.25) and Zara Ahmed (0.28)."
        ),
        "metric_name": "success_rate",
        "expected_value": 0.48,
        "actual_value": 0.31,
        "threshold": 0.50,
        "team_name": None,
        "status": "active",
    },
    {
        "alert_type": "friction_spike",
        "severity": "medium",
        "title": "Elevated friction in mobile-app sessions",
        "message": (
            "Mobile app sessions showing 0.28 friction rate, up from baseline of 0.12. "
            "Context limit errors are the primary contributor."
        ),
        "metric_name": "friction_rate",
        "expected_value": 0.12,
        "actual_value": 0.28,
        "threshold": 0.30,
        "team_name": "Mobile",
        "status": "active",
    },
    {
        "alert_type": "cost_spike",
        "severity": "low",
        "title": "Platform team weekly cost trending up",
        "message": (
            "Platform team weekly cost is $890, up from $720 average. "
            "Likely due to increased feature work on api-service."
        ),
        "metric_name": "weekly_cost",
        "expected_value": 720.0,
        "actual_value": 890.0,
        "threshold": 200.0,
        "team_name": "Platform",
        "status": "dismissed",
    },
    {
        "alert_type": "success_rate_drop",
        "severity": "medium",
        "title": "ml-pipeline success rate below threshold",
        "message": (
            "ML pipeline sessions have a 0.42 success rate over the past 14 days, "
            "below the 0.50 threshold. Consider adding CLAUDE.md for better context."
        ),
        "metric_name": "success_rate",
        "expected_value": 0.55,
        "actual_value": 0.42,
        "threshold": 0.50,
        "team_name": "Data",
        "status": "acknowledged",
    },
    {
        "alert_type": "friction_spike",
        "severity": "low",
        "title": "Minor friction increase in cli-tool sessions",
        "message": (
            "CLI tool sessions showing slight friction increase from 0.08 to 0.15. "
            "Timeout errors from long-running test suites."
        ),
        "metric_name": "friction_rate",
        "expected_value": 0.08,
        "actual_value": 0.15,
        "threshold": 0.30,
        "team_name": "Platform",
        "status": "dismissed",
    },
]


# ============================================================================
# Helper utilities
# ============================================================================


def _uid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ============================================================================
# Seeding functions
# ============================================================================


NEW_HIRE_EMAILS = {
    "yuki@example.com",
    "raj@example.com",
    "oscar@example.com",
    "zara@example.com",
}
RAMPING_EMAILS = {
    "lily@example.com",
    "fatima@example.com",
    "liam@example.com",
}


def trim_sessions_for_cohorts(db: Session) -> None:
    """Delete old sessions for new-hire and ramping engineers.

    The onboarding analytics classify engineers by their first session date:
    - new_hire: first session within last 20 days
    - ramping: first session within last 50 days
    - experienced: first session >90 days ago

    The base seed creates 90 days of sessions for everyone, so we trim the
    older sessions for new_hire and ramping personas so their cohort
    classification works correctly.
    """
    print("\n=== Trimming sessions for onboarding cohorts ===")
    now = _now()
    cutoffs = {
        "new_hire": now - timedelta(days=20),
        "ramping": now - timedelta(days=50),
    }

    all_engineers = db.execute(select(Engineer)).scalars().all()
    email_to_eng = {e.email: e for e in all_engineers}

    for persona, emails in [("new_hire", NEW_HIRE_EMAILS), ("ramping", RAMPING_EMAILS)]:
        cutoff = cutoffs[persona]
        for email in emails:
            eng = email_to_eng.get(email)
            if not eng:
                continue
            deleted = (
                db.query(SessionModel)
                .filter(
                    SessionModel.engineer_id == eng.id,
                    SessionModel.started_at < cutoff,
                )
                .delete(synchronize_session="fetch")
            )
            if deleted:
                print(f"  {eng.name} ({persona}): removed {deleted} sessions before cutoff")

    db.commit()


def seed_git_repositories(db: Session) -> dict[str, str]:
    """Create GitRepository records for each project. Returns {project_name: repo_id}."""
    print("\n=== Seeding Git Repositories ===")
    repo_map: dict[str, str] = {}

    for project_name, config in REPO_CONFIGS.items():
        existing = db.execute(
            select(GitRepository).where(GitRepository.full_name == config["full_name"])
        ).scalar_one_or_none()

        if existing:
            # Update existing repo with readiness data
            existing.primary_language = config["primary_language"]
            existing.language_breakdown = config["language_breakdown"]
            existing.repo_size_kb = config["repo_size_kb"]
            existing.has_claude_md = config["has_claude_md"]
            existing.has_agents_md = config["has_agents_md"]
            existing.has_claude_dir = config["has_claude_dir"]
            existing.ai_readiness_score = config["ai_readiness_score"]
            existing.ai_readiness_checked_at = _now() - timedelta(days=random.randint(1, 7))
            existing.has_test_harness = config["has_test_harness"]
            existing.has_ci_pipeline = config["has_ci_pipeline"]
            existing.test_maturity_score = config["test_maturity_score"]
            existing.repo_context_checked_at = _now() - timedelta(days=random.randint(1, 7))
            if not existing.default_branch:
                existing.default_branch = "main"
            if not existing.github_id:
                existing.github_id = random.randint(100000, 999999)
            repo_map[project_name] = existing.id
            readiness = config["ai_readiness_score"]
            print(f"  Updated repository: {config['full_name']} (readiness={readiness})")
            continue

        repo = GitRepository(
            id=_uid(),
            full_name=config["full_name"],
            github_id=random.randint(100000, 999999),
            default_branch="main",
            primary_language=config["primary_language"],
            language_breakdown=config["language_breakdown"],
            repo_size_kb=config["repo_size_kb"],
            has_claude_md=config["has_claude_md"],
            has_agents_md=config["has_agents_md"],
            has_claude_dir=config["has_claude_dir"],
            ai_readiness_score=config["ai_readiness_score"],
            ai_readiness_checked_at=_now() - timedelta(days=random.randint(1, 7)),
            has_test_harness=config["has_test_harness"],
            has_ci_pipeline=config["has_ci_pipeline"],
            test_maturity_score=config["test_maturity_score"],
            repo_context_checked_at=_now() - timedelta(days=random.randint(1, 7)),
        )
        db.add(repo)
        repo_map[project_name] = repo.id
        readiness = config["ai_readiness_score"]
        print(f"  Created repository: {config['full_name']} (readiness={readiness})")

    db.commit()
    print(f"  Total repositories: {len(repo_map)}")
    return repo_map


def link_sessions_to_repositories(db: Session, repo_map: dict[str, str]) -> None:
    """Link existing sessions to their GitRepository records via project_name."""
    print("\n=== Linking Sessions to Repositories ===")
    updated = 0
    sessions = (
        db.execute(select(SessionModel).where(SessionModel.repository_id.is_(None))).scalars().all()
    )

    for session in sessions:
        if session.project_name and session.project_name in repo_map:
            session.repository_id = repo_map[session.project_name]
            updated += 1

    db.commit()
    print(f"  Linked {updated} sessions to repositories")


def seed_cursor_sessions(db: Session, repo_map: dict[str, str]) -> int:
    """Create Cursor sessions for a subset of engineers.

    Returns the number of sessions created.
    """
    print("\n=== Seeding Cursor Sessions ===")

    # Lookup engineers who should get cursor sessions
    engineers_with_cursor = (
        db.execute(select(Engineer).where(Engineer.email.in_(CURSOR_ENGINEER_EMAILS)))
        .scalars()
        .all()
    )

    if not engineers_with_cursor:
        print("  No engineers found for cursor sessions. Skipping.")
        return 0

    # Build an engineer lookup by email from ENGINEERS constant for persona info
    eng_persona_map: dict[str, str] = {}
    for _name, email, _ti, _role, _gh, _ghid, persona_type, _mix in ENGINEERS:
        eng_persona_map[email] = persona_type

    # Build preferred projects per engineer (same logic as base seed)
    project_names = list(PROJECTS.keys())
    engineer_projects: dict[str, list[str]] = {}
    for eng in engineers_with_cursor:
        n_projects = random.randint(2, 4)
        engineer_projects[eng.id] = random.sample(
            project_names, k=min(n_projects, len(project_names))
        )

    now = datetime.utcnow()
    session_types = list(FIRST_PROMPTS.keys())
    session_type_weights = [35, 25, 15, 15, 10]
    total_created = 0

    for eng in engineers_with_cursor:
        persona_type = eng_persona_map.get(eng.email, "moderate")
        persona = PERSONAS[persona_type]
        preferred_projects = engineer_projects[eng.id]
        eng_sessions = 0

        # Cursor sessions are typically ~15-25% of an engineer's total sessions
        cursor_session_ratio = 0.2 if persona_type == "power_user" else 0.15

        # Limit date range for new-hire and ramping engineers so cohort
        # classification works (first session date determines cohort)
        max_days = 90
        if eng.email in NEW_HIRE_EMAILS:
            max_days = 20
        elif eng.email in RAMPING_EMAILS:
            max_days = 50

        for day_offset in range(max_days):
            day = now - timedelta(days=day_offset)
            is_weekend = day.weekday() >= 5

            if is_weekend and random.random() > persona["weekend_factor"]:
                continue

            lo, hi = persona["sessions_per_day"]
            if is_weekend:
                lo, hi = 0, max(1, hi // 3)
            n_sessions = random.randint(lo, hi)
            # Only a fraction become cursor sessions
            n_cursor = max(0, int(n_sessions * cursor_session_ratio + random.gauss(0, 0.5)))
            if n_cursor == 0 and random.random() < 0.15:
                n_cursor = 1  # occasional cursor session even on low days

            for _ in range(n_cursor):
                session_id = _uid()

                # Pick time weighted toward working hours
                hour = random.choices(range(24), weights=HOUR_WEIGHTS, k=1)[0]
                minute = random.randint(0, 59)
                started_at = day.replace(hour=hour, minute=minute, second=random.randint(0, 59))

                # Cursor sessions tend to be slightly shorter (IDE-integrated)
                import math

                dur_lo, dur_hi = persona["duration_range"]
                duration = max(
                    dur_lo,
                    min(int(dur_hi * 0.85), int(random.lognormvariate(math.log(480), 0.75))),
                )
                ended_at = started_at + timedelta(seconds=duration)

                msg_count = max(3, int(duration / 35 + random.gauss(0, 3)))
                user_msgs = max(1, msg_count // 2 + random.randint(-2, 2))
                assistant_msgs = msg_count - user_msgs

                session_type = random.choices(session_types, weights=session_type_weights, k=1)[0]

                if random.random() < 0.8:
                    project_name = random.choice(preferred_projects)
                else:
                    project_name = random.choice(project_names)
                project = PROJECTS[project_name]

                # Model selection (cursor uses mixed models)
                model_weights = CURSOR_AGENT_CONFIG["model_weights"][persona_type]
                model = _weighted_choice(model_weights)

                # Tokens
                token_scale = persona["token_scale"]
                if "opus" in model:
                    token_scale *= 1.8
                elif "sonnet" in model:
                    token_scale *= 1.0
                elif "gpt-4o" in model:
                    token_scale *= 1.2
                elif "gemini" in model:
                    token_scale *= 1.3
                inp_tokens = _lognormal_tokens(8.3, 0.9, token_scale)
                out_tokens = _lognormal_tokens(7.3, 0.9, token_scale)

                cache_read = 0
                cache_creation = 0
                if random.random() < 0.25:  # Cursor has lower cache rates
                    cache_read = int(inp_tokens * random.uniform(0.05, 0.3))
                    cache_creation = int(inp_tokens * random.uniform(0.01, 0.08))

                # Outcome
                outcome_weights = {}
                for k, v in persona["outcome_weights"].items():
                    outcome_weights[k] = v + project["outcome_bias"].get(k, 0)
                outcome = _weighted_choice(outcome_weights)

                # Friction
                friction_counts = None
                friction_detail = None
                friction_prob = (
                    0.10 if outcome == "success" else 0.28 if outcome == "partial" else 0.42
                )
                if random.random() < friction_prob:
                    ft = random.choice(CURSOR_FRICTION_TYPES)
                    friction_counts = {ft: random.randint(1, 3)}
                    if random.random() < 0.7:
                        friction_detail = random.choice(
                            CURSOR_FRICTION_DETAILS.get(ft, ["Unspecified"])
                        )

                first_prompt = random.choice(FIRST_PROMPTS[session_type])
                summary = _generate_summary(session_type) if random.random() < 0.8 else None
                git_branch = _generate_branch(session_type)
                agent_version = random.choice(CURSOR_AGENT_CONFIG["versions"])
                permission_mode = random.choice(CURSOR_AGENT_CONFIG["permission_modes"])

                # Tool usages
                available_tools = CURSOR_AGENT_CONFIG["tools"]
                proj_weights = CURSOR_PROJECT_TOOL_WEIGHTS.get(project_name, {})
                n_tools = random.randint(2, min(5, len(available_tools)))
                selected_tools = random.sample(available_tools, k=n_tools)
                tool_count = 0

                # Create session record
                session = SessionModel(
                    id=session_id,
                    engineer_id=eng.id,
                    repository_id=repo_map.get(project_name),
                    agent_type="cursor",
                    project_path=f"/home/{eng.email.split('@')[0]}/code/{project_name}",
                    project_name=project_name,
                    git_branch=git_branch,
                    agent_version=agent_version,
                    permission_mode=permission_mode,
                    end_reason=(
                        random.choice(["user_exit", "conversation_end", "timeout", "error"])
                        if outcome != "success"
                        else random.choices(
                            ["user_exit", "conversation_end", "timeout", "error"],
                            weights=[60, 30, 5, 5],
                            k=1,
                        )[0]
                    ),
                    started_at=started_at,
                    ended_at=ended_at,
                    duration_seconds=float(duration),
                    message_count=msg_count,
                    user_message_count=user_msgs,
                    assistant_message_count=assistant_msgs,
                    tool_call_count=0,  # will update below
                    input_tokens=inp_tokens,
                    output_tokens=out_tokens,
                    cache_read_tokens=cache_read,
                    cache_creation_tokens=cache_creation,
                    primary_model=model,
                    first_prompt=first_prompt,
                    summary=summary,
                    has_facets=False,
                )
                db.add(session)

                # Tool usages
                for tool in selected_tools:
                    base_weight = proj_weights.get(tool, 5)
                    call_count = max(1, int(random.gauss(base_weight / 2, base_weight / 4)))
                    tool_count += call_count
                    db.add(
                        ToolUsage(
                            session_id=session_id,
                            tool_name=tool,
                            call_count=call_count,
                        )
                    )

                session.tool_call_count = tool_count

                # Facets
                if random.random() < 0.85:
                    facets_data = _build_facets(
                        session_type=session_type,
                        outcome=outcome,
                        project_name=project_name,
                        summary=summary,
                        friction_counts=friction_counts,
                        friction_detail=friction_detail,
                        include_user_satisfaction=random.random() < 0.6,
                    )
                    facets = SessionFacets(
                        session_id=session_id,
                        underlying_goal=facets_data.get("underlying_goal"),
                        goal_categories=facets_data.get("goal_categories"),
                        outcome=facets_data.get("outcome"),
                        confidence_score=facets_data.get("confidence_score"),
                        session_type=facets_data.get("session_type"),
                        primary_success=facets_data.get("primary_success"),
                        brief_summary=facets_data.get("brief_summary"),
                        user_satisfaction_counts=facets_data.get("user_satisfaction_counts"),
                        friction_counts=facets_data.get("friction_counts"),
                        friction_detail=facets_data.get("friction_detail"),
                    )
                    db.add(facets)
                    session.has_facets = True

                # Commits for coding sessions
                if (
                    session_type in ("feature", "debugging", "refactoring")
                    and random.random() > 0.3
                ):
                    n_commits = random.randint(1, 4)
                    dur_secs = (ended_at - started_at).total_seconds()
                    for _ci in range(n_commits):
                        offset_secs = random.uniform(dur_secs * 0.2, dur_secs * 0.95)
                        committed_at = started_at + timedelta(seconds=offset_secs)
                        slug = git_branch.split("/")[-1] if "/" in git_branch else git_branch
                        msg_templates = COMMIT_MESSAGES.get(
                            session_type, COMMIT_MESSAGES["feature"]
                        )
                        commit_msg = random.choice(msg_templates).format(slug=slug)
                        db.add(
                            SessionCommit(
                                id=_uid(),
                                session_id=session_id,
                                repository_id=repo_map.get(project_name),
                                commit_sha=uuid.uuid4().hex + uuid.uuid4().hex[:8],
                                commit_message=commit_msg,
                                author_name=eng.name,
                                author_email=eng.email,
                                committed_at=committed_at,
                                files_changed=random.randint(1, 10),
                                lines_added=random.randint(5, 250),
                                lines_deleted=random.randint(0, 120),
                            )
                        )

                eng_sessions += 1
                total_created += 1

        print(f"  {eng.name}: {eng_sessions} cursor sessions")

    db.commit()
    print(f"  Total cursor sessions created: {total_created}")
    return total_created


def seed_pull_requests(db: Session, repo_map: dict[str, str]) -> dict[str, str]:
    """Create PullRequest records for sessions with commits.

    Returns {session_id: pr_id} for sessions that got PRs.
    """
    print("\n=== Seeding Pull Requests ===")

    # Check for existing PRs to avoid duplicates
    existing_pr_count = db.execute(select(PullRequest)).scalars().all()
    if existing_pr_count:
        print(f"  {len(existing_pr_count)} PRs already exist. Checking for gaps...")

    # Get sessions that have commits and a project name
    sessions_with_commits = (
        db.execute(
            select(SessionModel)
            .where(SessionModel.project_name.isnot(None))
            .join(SessionCommit, SessionCommit.session_id == SessionModel.id)
        )
        .scalars()
        .unique()
        .all()
    )

    # Track PR numbers per repo to avoid duplicate constraint violations
    pr_numbers: dict[str, int] = {}
    for repo_id in repo_map.values():
        max_pr = db.execute(
            select(PullRequest.github_pr_number)
            .where(PullRequest.repository_id == repo_id)
            .order_by(PullRequest.github_pr_number.desc())
            .limit(1)
        ).scalar()
        pr_numbers[repo_id] = max_pr or 0

    # Build engineer persona lookup
    eng_persona_map: dict[str, str] = {}
    for _name, email, _ti, _role, _gh, _ghid, persona_type, _mix in ENGINEERS:
        eng_persona_map[email] = persona_type
    eng_email_by_id: dict[str, str] = {}
    all_engs = db.execute(select(Engineer)).scalars().all()
    for eng in all_engs:
        eng_email_by_id[eng.id] = eng.email

    pr_map: dict[str, str] = {}
    created_count = 0

    # Group sessions by engineer+branch to create one PR per branch
    branch_sessions: dict[tuple[str, str, str], list] = {}
    for session in sessions_with_commits:
        if not session.git_branch or not session.project_name:
            continue
        repo_id = repo_map.get(session.project_name)
        if not repo_id:
            continue
        key = (session.engineer_id, repo_id, session.git_branch)
        branch_sessions.setdefault(key, []).append(session)

    for (engineer_id, repo_id, branch), sessions in branch_sessions.items():
        # Check if PR already exists for this repo+branch
        existing = db.execute(
            select(PullRequest).where(
                PullRequest.repository_id == repo_id,
                PullRequest.head_branch == branch,
            )
        ).scalar_one_or_none()
        if existing:
            for s in sessions:
                pr_map[s.id] = existing.id
            continue

        # Use earliest session for PR creation time
        earliest = min(sessions, key=lambda s: s.started_at)
        project_name = earliest.project_name or "unknown"

        email = eng_email_by_id.get(engineer_id, "")
        persona_type = eng_persona_map.get(email, "moderate")

        # Power users have higher merge rates
        if persona_type == "power_user":
            state_weights = {"merged": 80, "open": 12, "closed": 8}
        elif persona_type in ("moderate", "ramping_up"):
            state_weights = {"merged": 65, "open": 20, "closed": 15}
        else:
            state_weights = {"merged": 50, "open": 30, "closed": 20}

        state = _weighted_choice(state_weights)

        pr_numbers[repo_id] = pr_numbers.get(repo_id, 0) + 1
        pr_number = pr_numbers[repo_id]

        # PR title
        slug = branch.split("/")[-1] if "/" in branch else branch
        session_type = earliest.facets.session_type if earliest.facets else "feature"
        if session_type not in PR_TITLE_TEMPLATES:
            session_type = "feature"
        title = random.choice(PR_TITLE_TEMPLATES[session_type]).format(
            slug=slug, project=project_name
        )

        pr_created_at = earliest.started_at + timedelta(minutes=random.randint(5, 60))

        # Time to merge correlates with persona
        if state == "merged":
            if persona_type == "power_user":
                merge_hours = random.uniform(0.5, 8)
            elif persona_type in ("moderate", "ramping_up"):
                merge_hours = random.uniform(2, 24)
            else:
                merge_hours = random.uniform(4, 48)
            merged_at = pr_created_at + timedelta(hours=merge_hours)
            closed_at = merged_at
        elif state == "closed":
            closed_at = pr_created_at + timedelta(hours=random.uniform(1, 72))
            merged_at = None
        else:
            merged_at = None
            closed_at = None

        # Aggregate stats from commits
        total_additions = 0
        total_deletions = 0
        total_files = 0
        total_commits = 0
        for s in sessions:
            for commit in s.commits:
                total_additions += commit.lines_added
                total_deletions += commit.lines_deleted
                total_files += commit.files_changed
                total_commits += 1

        review_comments = random.randint(0, 8)
        if persona_type == "power_user":
            review_comments = random.randint(0, 4)  # cleaner PRs

        pr = PullRequest(
            id=_uid(),
            repository_id=repo_id,
            engineer_id=engineer_id,
            github_pr_number=pr_number,
            title=title,
            state=state,
            head_branch=branch,
            additions=total_additions,
            deletions=total_deletions,
            changed_files=max(1, total_files // max(1, total_commits)),
            review_comments_count=review_comments,
            commits_count=total_commits,
            merged_at=merged_at,
            closed_at=closed_at,
            pr_created_at=pr_created_at,
        )
        db.add(pr)
        created_count += 1

        for s in sessions:
            pr_map[s.id] = pr.id

        # Link commits to PR
        for s in sessions:
            for commit in s.commits:
                commit.pull_request_id = pr.id

    db.commit()
    print(f"  Created {created_count} pull requests")
    return pr_map


def seed_review_findings(db: Session, pr_map: dict[str, str]) -> int:
    """Create ReviewFinding records for ~40% of PRs."""
    print("\n=== Seeding Review Findings ===")

    # Get unique PR IDs
    pr_ids = list(set(pr_map.values()))
    if not pr_ids:
        print("  No PRs to create findings for. Skipping.")
        return 0

    # Build engineer persona lookup for PRs
    prs = db.execute(select(PullRequest).where(PullRequest.id.in_(pr_ids))).scalars().all()

    eng_email_by_id: dict[str, str] = {}
    all_engs = db.execute(select(Engineer)).scalars().all()
    for eng in all_engs:
        eng_email_by_id[eng.id] = eng.email

    eng_persona_map: dict[str, str] = {}
    for _name, email, _ti, _role, _gh, _ghid, persona_type, _mix in ENGINEERS:
        eng_persona_map[email] = persona_type

    created_count = 0
    severity_distribution = {"high": 15, "medium": 45, "low": 40}

    for pr in prs:
        # ~40% of PRs get findings
        if random.random() > 0.40:
            continue

        # Check for existing findings
        existing = (
            db.execute(select(ReviewFinding).where(ReviewFinding.pull_request_id == pr.id))
            .scalars()
            .all()
        )
        if existing:
            continue

        email = eng_email_by_id.get(pr.engineer_id, "")
        persona_type = eng_persona_map.get(email, "moderate")

        # Power users get fewer high-severity findings
        if persona_type == "power_user":
            adj_severity = {"high": 5, "medium": 40, "low": 55}
        elif persona_type in ("new_hire", "occasional"):
            adj_severity = {"high": 25, "medium": 45, "low": 30}
        else:
            adj_severity = severity_distribution

        n_findings = random.randint(1, 5)
        if persona_type == "power_user":
            n_findings = random.randint(1, 3)
        elif persona_type in ("new_hire",):
            n_findings = random.randint(2, 6)

        # Determine project for file paths
        project_name = None
        repo = pr.repository
        if repo:
            for pn, cfg in REPO_CONFIGS.items():
                if cfg["full_name"] == repo.full_name:
                    project_name = pn
                    break

        file_paths = PROJECT_FILE_PATHS.get(project_name, PROJECT_FILE_PATHS["api-service"])

        for _ in range(n_findings):
            severity = _weighted_choice(adj_severity)
            templates = REVIEW_FINDING_TEMPLATES[severity]
            template = random.choice(templates)

            file_path = random.choice(file_paths)
            file_stem = file_path.split("/")[-1].split(".")[0]
            title = template["title"].format(file_stem=file_stem)
            description = template["description"]

            detected_at = (
                pr.pr_created_at + timedelta(minutes=random.randint(10, 120))
                if pr.pr_created_at
                else _now() - timedelta(days=random.randint(1, 30))
            )

            # Higher severity findings are more likely to be resolved
            if severity == "high":
                resolved = random.random() < 0.85
            elif severity == "medium":
                resolved = random.random() < 0.65
            else:
                resolved = random.random() < 0.40

            status = "resolved" if resolved else "open"
            resolved_at = detected_at + timedelta(hours=random.uniform(1, 48)) if resolved else None

            finding = ReviewFinding(
                id=_uid(),
                pull_request_id=pr.id,
                source="bugbot",
                external_id=_uid(),
                severity=severity,
                title=title,
                description=description,
                file_path=file_path,
                line_number=random.randint(1, 500),
                status=status,
                detected_at=detected_at,
                resolved_at=resolved_at,
            )
            db.add(finding)
            created_count += 1

    db.commit()
    print(f"  Created {created_count} review findings")
    return created_count


def seed_session_customizations(db: Session) -> int:
    """Create SessionCustomization records for Claude Code and Cursor sessions."""
    print("\n=== Seeding Session Customizations ===")

    sessions = (
        db.execute(
            select(SessionModel).where(SessionModel.agent_type.in_(["claude_code", "cursor"]))
        )
        .scalars()
        .all()
    )

    if not sessions:
        print("  No Claude Code or Cursor sessions found.")
        return 0

    eng_email_by_id: dict[str, str] = {}
    all_engs = db.execute(select(Engineer)).scalars().all()
    for eng in all_engs:
        eng_email_by_id[eng.id] = eng.email

    eng_persona_map: dict[str, str] = {}
    for _name, email, _ti, _role, _gh, _ghid, persona_type, _mix in ENGINEERS:
        eng_persona_map[email] = persona_type

    created_count = 0

    for session in sessions:
        # Check if customizations already exist
        existing = (
            db.execute(
                select(SessionCustomization).where(SessionCustomization.session_id == session.id)
            )
            .scalars()
            .all()
        )
        if existing:
            continue

        email = eng_email_by_id.get(session.engineer_id, "")
        persona_type = eng_persona_map.get(email, "moderate")

        # Probability of having customizations varies by persona
        if persona_type == "power_user":
            cust_prob = 0.75
        elif persona_type in ("moderate", "ramping_up"):
            cust_prob = 0.45
        elif persona_type == "new_hire":
            cust_prob = 0.20
        else:
            cust_prob = 0.30

        if random.random() > cust_prob:
            continue

        # Determine how many customizations
        if persona_type == "power_user":
            n_mcps = random.randint(2, 5)
            n_skills = random.randint(1, 4)
            n_subagents = random.randint(1, 3)
            n_commands = random.randint(0, 2)
        elif persona_type in ("moderate", "ramping_up"):
            n_mcps = random.randint(1, 3)
            n_skills = random.randint(0, 2)
            n_subagents = random.randint(0, 2)
            n_commands = random.randint(0, 1)
        else:
            n_mcps = random.randint(0, 2)
            n_skills = random.randint(0, 1)
            n_subagents = random.randint(0, 1)
            n_commands = 0

        # MCP servers
        selected_mcps = random.sample(MCP_SERVERS, k=min(n_mcps, len(MCP_SERVERS)))
        for identifier, display_name, provenance in selected_mcps:
            state = random.choices(["enabled", "invoked"], weights=[30, 70], k=1)[0]
            invocation_count = random.randint(1, 15) if state == "invoked" else 0
            db.add(
                SessionCustomization(
                    session_id=session.id,
                    customization_type="mcp",
                    state=state,
                    identifier=identifier,
                    provenance=provenance,
                    source_classification="custom",
                    display_name=display_name,
                    invocation_count=invocation_count,
                )
            )
            created_count += 1

        # Skills
        selected_skills = random.sample(SKILLS, k=min(n_skills, len(SKILLS)))
        for identifier, display_name, provenance in selected_skills:
            state = random.choices(["enabled", "invoked"], weights=[40, 60], k=1)[0]
            invocation_count = random.randint(1, 8) if state == "invoked" else 0
            db.add(
                SessionCustomization(
                    session_id=session.id,
                    customization_type="skill",
                    state=state,
                    identifier=identifier,
                    provenance=provenance,
                    source_classification="custom",
                    display_name=display_name,
                    invocation_count=invocation_count,
                )
            )
            created_count += 1

        # Subagents
        selected_subagents = random.sample(SUBAGENTS, k=min(n_subagents, len(SUBAGENTS)))
        for identifier, display_name, provenance in selected_subagents:
            state = random.choices(["enabled", "invoked"], weights=[35, 65], k=1)[0]
            invocation_count = random.randint(1, 6) if state == "invoked" else 0
            db.add(
                SessionCustomization(
                    session_id=session.id,
                    customization_type="subagent",
                    state=state,
                    identifier=identifier,
                    provenance=provenance,
                    source_classification="custom",
                    display_name=display_name,
                    invocation_count=invocation_count,
                )
            )
            created_count += 1

        # Commands
        selected_commands = random.sample(COMMANDS, k=min(n_commands, len(COMMANDS)))
        for identifier, display_name, provenance in selected_commands:
            state = random.choices(["enabled", "invoked"], weights=[50, 50], k=1)[0]
            invocation_count = random.randint(1, 5) if state == "invoked" else 0
            db.add(
                SessionCustomization(
                    session_id=session.id,
                    customization_type="command",
                    state=state,
                    identifier=identifier,
                    provenance=provenance,
                    source_classification="custom",
                    display_name=display_name,
                    invocation_count=invocation_count,
                )
            )
            created_count += 1

    db.commit()
    print(f"  Created {created_count} session customizations")
    return created_count


def seed_interventions(db: Session) -> int:
    """Create Intervention records across teams."""
    print("\n=== Seeding Interventions ===")

    # Build lookup maps
    teams = db.execute(select(Team)).scalars().all()
    team_by_name = {t.name: t for t in teams}

    engineers = db.execute(select(Engineer)).scalars().all()
    eng_by_email: dict[str, Engineer] = {e.email: e for e in engineers}

    # Map team leads as owners
    team_lead_emails = {
        "Platform": "marcus@example.com",
        "Backend": "bob@example.com",
        "Frontend": "eve@example.com",
        "Mobile": "grace@example.com",
        "Data": "james@example.com",
        "DevEx": "kenji@example.com",
    }

    now = _now()
    created_count = 0

    for idef in INTERVENTION_DEFS:
        # Check if intervention already exists (by title)
        existing = db.execute(
            select(Intervention).where(Intervention.title == idef["title"])
        ).scalar_one_or_none()
        if existing:
            print(f"  Intervention '{idef['title'][:50]}...' already exists")
            continue

        team_name = idef.get("team_name")
        team = team_by_name.get(team_name) if team_name else None
        team_id = team.id if team else None

        # Owner is the team lead or a random admin
        owner_email = (
            team_lead_emails.get(team_name, "alice@example.com")
            if team_name
            else "alice@example.com"
        )
        owner = eng_by_email.get(owner_email)

        # Timestamps
        if idef["status"] == "completed":
            created_at = now - timedelta(days=random.randint(30, 60))
            completed_at = now - timedelta(days=random.randint(3, 20))
            baseline_start = created_at - timedelta(days=14)
            baseline_end = created_at
            due_date = (created_at + timedelta(days=random.randint(14, 30))).date()
        elif idef["status"] == "in_progress":
            created_at = now - timedelta(days=random.randint(7, 21))
            completed_at = None
            baseline_start = created_at - timedelta(days=14)
            baseline_end = created_at
            due_date = (now + timedelta(days=random.randint(7, 21))).date()
        else:  # planned
            created_at = now - timedelta(days=random.randint(1, 7))
            completed_at = None
            baseline_start = None
            baseline_end = None
            due_date = (now + timedelta(days=random.randint(14, 45))).date()

        intervention = Intervention(
            id=_uid(),
            team_id=team_id,
            owner_engineer_id=owner.id if owner else None,
            created_by_engineer_id=owner.id if owner else None,
            project_name=idef.get("project_name"),
            category=idef["category"],
            severity=idef["severity"],
            status=idef["status"],
            title=idef["title"],
            description=idef["description"],
            due_date=due_date,
            completed_at=completed_at,
            source_type="recommendation",
            source_title=f"Auto-generated from analytics: {idef['category']}",
            evidence=idef.get("evidence"),
            baseline_start_at=baseline_start,
            baseline_end_at=baseline_end,
            baseline_metrics=idef.get("baseline_metrics"),
        )

        # Experiment fields
        if idef.get("is_experiment"):
            intervention.experiment_type = idef.get("experiment_type")
            intervention.experiment_hypothesis = idef.get("experiment_hypothesis")
            intervention.experiment_target_cohort = idef.get("experiment_target_cohort")
            intervention.experiment_success_criteria = idef.get("experiment_success_criteria")

        db.add(intervention)
        created_count += 1
        status_emoji = {"completed": "done", "in_progress": "active", "planned": "planned"}
        print(f"  [{status_emoji[idef['status']]}] {idef['title'][:60]}")

    db.commit()
    print(f"  Created {created_count} interventions")
    return created_count


def seed_alert_configs(db: Session) -> int:
    """Create AlertConfig records for each team."""
    print("\n=== Seeding Alert Configs ===")

    teams = db.execute(select(Team)).scalars().all()
    team_by_name = {t.name: t for t in teams}

    configs = [
        ("friction_spike", 0.30),
        ("cost_spike", 200.0),
        ("success_rate_drop", 0.50),
    ]

    created_count = 0

    # Global configs (team_id = None)
    for alert_type, threshold in configs:
        existing = db.execute(
            select(AlertConfig).where(
                AlertConfig.team_id.is_(None),
                AlertConfig.alert_type == alert_type,
            )
        ).scalar_one_or_none()
        if existing:
            continue

        db.add(
            AlertConfig(
                id=_uid(),
                team_id=None,
                alert_type=alert_type,
                enabled=True,
                threshold=threshold,
            )
        )
        created_count += 1

    # Per-team configs with slight variations
    team_thresholds = {
        "Platform": {"friction_spike": 0.25, "cost_spike": 250.0, "success_rate_drop": 0.55},
        "Backend": {"friction_spike": 0.30, "cost_spike": 200.0, "success_rate_drop": 0.50},
        "Frontend": {"friction_spike": 0.35, "cost_spike": 150.0, "success_rate_drop": 0.45},
        "Mobile": {"friction_spike": 0.30, "cost_spike": 120.0, "success_rate_drop": 0.50},
        "Data": {"friction_spike": 0.25, "cost_spike": 300.0, "success_rate_drop": 0.50},
        "DevEx": {"friction_spike": 0.20, "cost_spike": 180.0, "success_rate_drop": 0.55},
    }

    for team_name, thresholds in team_thresholds.items():
        team = team_by_name.get(team_name)
        if not team:
            continue
        for alert_type, threshold in thresholds.items():
            existing = db.execute(
                select(AlertConfig).where(
                    AlertConfig.team_id == team.id,
                    AlertConfig.alert_type == alert_type,
                )
            ).scalar_one_or_none()
            if existing:
                continue

            db.add(
                AlertConfig(
                    id=_uid(),
                    team_id=team.id,
                    alert_type=alert_type,
                    enabled=True,
                    threshold=threshold,
                )
            )
            created_count += 1

    db.commit()
    print(f"  Created {created_count} alert configs")
    return created_count


def seed_alerts(db: Session) -> int:
    """Create Alert records with various states."""
    print("\n=== Seeding Alerts ===")

    teams = db.execute(select(Team)).scalars().all()
    team_by_name = {t.name: t for t in teams}

    now = _now()
    created_count = 0

    for adef in ALERT_DEFS:
        # Check for existing alert with same title
        existing = db.execute(
            select(Alert).where(Alert.title == adef["title"])
        ).scalar_one_or_none()
        if existing:
            print(f"  Alert '{adef['title'][:50]}...' already exists")
            continue

        team_name = adef.get("team_name")
        team = team_by_name.get(team_name) if team_name else None

        detected_at = now - timedelta(hours=random.randint(1, 72))

        acknowledged_at = None
        dismissed = False
        if adef["status"] == "acknowledged":
            acknowledged_at = detected_at + timedelta(hours=random.uniform(0.5, 12))
        elif adef["status"] == "dismissed":
            acknowledged_at = detected_at + timedelta(hours=random.uniform(0.5, 6))
            dismissed = True

        alert = Alert(
            id=_uid(),
            team_id=team.id if team else None,
            alert_type=adef["alert_type"],
            severity=adef["severity"],
            title=adef["title"],
            message=adef["message"],
            metric_name=adef["metric_name"],
            expected_value=adef["expected_value"],
            actual_value=adef["actual_value"],
            threshold=adef["threshold"],
            detected_at=detected_at,
            acknowledged_at=acknowledged_at,
            dismissed=dismissed,
        )
        db.add(alert)
        created_count += 1
        print(f"  [{adef['status']}] {adef['title'][:60]}")

    db.commit()
    print(f"  Created {created_count} alerts")
    return created_count


def trigger_post_seed_jobs() -> None:
    """Call admin endpoints to compute derived data."""
    print("\n=== Triggering Post-Seed Derived Data ===")

    # Backfill workflow profiles
    print("  Backfilling workflow profiles...")
    try:
        r = httpx.post(
            f"{SERVER_URL}/api/v1/admin/backfill-workflow-profiles",
            headers=ADMIN_HEADERS,
            params={"recompute": "false"},
            timeout=120.0,
        )
        if r.status_code == 200:
            data = r.json()
            print(f"    Workflow profiles: {data}")
        else:
            print(f"    Warning: backfill-workflow-profiles returned {r.status_code}")
    except Exception as e:
        print(f"    Warning: backfill-workflow-profiles failed: {e}")

    # Normalize facets
    print("  Normalizing facets...")
    try:
        r = httpx.post(
            f"{SERVER_URL}/api/v1/admin/normalize-facets",
            headers=ADMIN_HEADERS,
            timeout=120.0,
        )
        if r.status_code == 200:
            data = r.json()
            print(f"    Facet normalization: {data}")
        else:
            print(f"    Warning: normalize-facets returned {r.status_code}")
    except Exception as e:
        print(f"    Warning: normalize-facets failed: {e}")

    # Detect anomalies
    print("  Running anomaly detection...")
    try:
        r = httpx.post(
            f"{SERVER_URL}/api/v1/alerts/detect",
            headers=ADMIN_HEADERS,
            timeout=60.0,
        )
        if r.status_code == 200:
            data = r.json()
            print(f"    Anomaly detection: {data}")
        else:
            print(f"    Warning: alerts/detect returned {r.status_code}")
    except Exception as e:
        print(f"    Warning: alerts/detect failed: {e}")


# ============================================================================
# Main entry point
# ============================================================================


def main():
    random.seed(42)

    print("=" * 70)
    print("  Primer Demo Seed Script")
    print("=" * 70)
    print(f"  Database: {DATABASE_URL}")
    print(f"  Server:   {SERVER_URL}")
    print()

    # Step 0: Run base seed (unless skipped)
    if not _skip_base_seed():
        print(">>> Running base seed_data.py via API...")
        print("-" * 70)
        from seed_data import main as base_main

        base_main()
        print("-" * 70)
        print(">>> Base seed complete.\n")
        # Re-seed random for reproducibility of demo additions
        random.seed(42_000)
    else:
        print(">>> Skipping base seed (PRIMER_SEED_SKIP_BASE=1)")
        random.seed(42_000)

    # Open a DB session for direct SQLAlchemy operations
    db = DBSessionFactory()
    try:
        # Step 0.5: Trim sessions so new hires and ramping engineers have correct cohorts
        trim_sessions_for_cohorts(db)

        # Step 1: Git repositories
        repo_map = seed_git_repositories(db)

        # Step 2: Link existing sessions to repos
        link_sessions_to_repositories(db, repo_map)

        # Step 3: Cursor sessions
        cursor_count = seed_cursor_sessions(db, repo_map)

        # Step 4: Pull requests
        pr_map = seed_pull_requests(db, repo_map)

        # Step 5: Review findings
        finding_count = seed_review_findings(db, pr_map)

        # Step 6: Session customizations
        cust_count = seed_session_customizations(db)

        # Step 7: Interventions
        intervention_count = seed_interventions(db)

        # Step 8: Alert configs and alerts
        config_count = seed_alert_configs(db)
        alert_count = seed_alerts(db)

    finally:
        db.close()

    # Step 9: Post-seed derived data (via API)
    trigger_post_seed_jobs()

    # Summary
    print("\n" + "=" * 70)
    print("  Demo Seed Complete!")
    print("=" * 70)
    print(f"  Git repositories:       {len(repo_map)}")
    print(f"  Cursor sessions:        {cursor_count}")
    print(f"  Pull requests:          {len(set(pr_map.values()))}")
    print(f"  Review findings:        {finding_count}")
    print(f"  Session customizations: {cust_count}")
    print(f"  Interventions:          {intervention_count}")
    print(f"  Alert configs:          {config_count}")
    print(f"  Alerts:                 {alert_count}")
    print()


if __name__ == "__main__":
    main()
