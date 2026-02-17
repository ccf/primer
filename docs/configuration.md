# Configuration

All Primer settings use the `PRIMER_` environment variable prefix. Settings can be provided as environment variables or in a `.env` file in the project root.

Copy `.env.example` to `.env` to get started:

```bash
cp .env.example .env
```

## Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_DATABASE_URL` | `sqlite:///./primer.db` | Database connection string (SQLite or PostgreSQL) |
| `PRIMER_ADMIN_API_KEY` | `primer-admin-dev-key` | Shared secret for admin API access |
| `PRIMER_SERVER_HOST` | `0.0.0.0` | Server bind address |
| `PRIMER_SERVER_PORT` | `8000` | Server bind port |
| `PRIMER_LOG_LEVEL` | `info` | Logging level (debug, info, warning, error) |
| `PRIMER_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `PRIMER_BASE_URL` | `http://localhost:5173` | Base URL for cookie Secure flag |

## GitHub OAuth

Required for GitHub-based dashboard login. See [GitHub Integration](github-integration.md) for setup instructions.

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_GITHUB_CLIENT_ID` | — | OAuth App client ID |
| `PRIMER_GITHUB_CLIENT_SECRET` | — | OAuth App client secret |
| `PRIMER_GITHUB_REDIRECT_URI` | `http://localhost:5173/auth/callback` | OAuth callback URL |

## GitHub App

Required for PR sync, commit correlation, and AI-readiness scoring. See [GitHub Integration](github-integration.md) for setup instructions.

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_GITHUB_APP_ID` | — | GitHub App ID (numeric) |
| `PRIMER_GITHUB_APP_PRIVATE_KEY` | — | RSA private key (PEM format, `\n` for newlines) |
| `PRIMER_GITHUB_INSTALLATION_ID` | — | App installation ID (numeric) |
| `PRIMER_GITHUB_WEBHOOK_SECRET` | — | Webhook HMAC secret |

## JWT Authentication

Used for dashboard session tokens.

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_JWT_SECRET_KEY` | `change-me-in-production` | Secret for JWT signing (change this!) |
| `PRIMER_JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `PRIMER_JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |

Generate a secure secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_RATE_LIMIT_ENABLED` | `true` | Enable/disable rate limiting |
| `PRIMER_RATE_LIMIT_DEFAULT` | `60/minute` | Default limit for all endpoints |
| `PRIMER_RATE_LIMIT_INGEST` | `120/minute` | Limit for ingest endpoints |
| `PRIMER_RATE_LIMIT_AUTH` | `10/minute` | Limit for auth endpoints |

## Productivity Estimation

Controls the ROI calculations shown in the dashboard.

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_PRODUCTIVITY_TIME_MULTIPLIER` | `3.0` | Estimated time savings multiplier vs manual work |
| `PRIMER_PRODUCTIVITY_HOURLY_RATE` | `75.0` | Hourly rate for value calculations (USD) |

## Alert Thresholds

Default thresholds for anomaly detection. These can be overridden per-team in the admin panel.

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_ALERT_FRICTION_SPIKE_MULTIPLIER` | `2.0` | Trigger when friction is Nx the baseline |
| `PRIMER_ALERT_USAGE_DROP_RATIO` | `0.5` | Trigger when usage drops below ratio of baseline |
| `PRIMER_ALERT_COST_SPIKE_WARNING` | `2.0` | Warning when cost is Nx the baseline |
| `PRIMER_ALERT_COST_SPIKE_CRITICAL` | `3.0` | Critical when cost is Nx the baseline |
| `PRIMER_ALERT_SUCCESS_RATE_DROP_PP` | `20.0` | Trigger when success rate drops N percentage points |

## Slack Notifications

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_SLACK_WEBHOOK_URL` | — | Slack incoming webhook URL |
| `PRIMER_SLACK_ALERTS_ENABLED` | `false` | Enable alert delivery to Slack |

## Hook and MCP Client Settings

These variables are used by the SessionEnd hook and MCP sidecar running on developer machines, not the server.

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMER_SERVER_URL` | `http://localhost:8000` | URL of the Primer API server |
| `PRIMER_API_KEY` | — | Engineer API key for authentication |
| `PRIMER_ADMIN_API_KEY` | — | Admin key (MCP sidecar only, for team analytics) |
