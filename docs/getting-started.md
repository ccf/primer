# Getting Started

This guide walks you through installing Primer, setting up the dashboard, connecting the Claude Code hook, and optionally enabling GitHub integration.

## Prerequisites

- Python 3.12+
- Node.js 20+
- A running Claude Code installation

## 1. Install the Server

```bash
git clone <repo-url> && cd primer
pip install -e ".[dev]"
```

Initialize the database and start the API:

```bash
alembic upgrade head
uvicorn primer.server.app:app --reload
```

The API is now running at `http://localhost:8000`. Verify with:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## 2. Start the Dashboard

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. You'll see the login page.

For development, expand the "Admin API Key" section and enter the default key: `primer-admin-dev-key`. This gives you full admin access to all views.

## 3. Seed Sample Data (Optional)

To explore the dashboard with realistic data:

```bash
python scripts/seed_data.py
```

This creates 3 teams, 8 engineers with different usage personas, and ~90 days of session history with transcripts, tool usage, model usage, friction events, and git commits.

## 4. Install the SessionEnd Hook

The hook automatically uploads session data after each Claude Code session.

First, create an engineer and get an API key:

```bash
curl -X POST http://localhost:8000/api/v1/engineers \
  -H "x-admin-key: primer-admin-dev-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "Your Name", "email": "you@example.com"}'
```

Save the `api_key` from the response. Then install the hook:

```bash
export PRIMER_SERVER_URL=http://localhost:8000
export PRIMER_API_KEY=primer_...  # The key from above
python scripts/install_hook.py
```

This adds a `SessionEnd` entry to `~/.claude/settings.json`. After your next Claude Code session ends, the transcript is automatically uploaded to Primer.

### Verify the Hook

After completing a Claude Code session, check that it appears:

```bash
curl http://localhost:8000/api/v1/sessions \
  -H "x-admin-key: primer-admin-dev-key" | python -m json.tool
```

## 5. Register the MCP Server (Optional)

The MCP sidecar lets Claude query your team's usage data during conversations.

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "primer": {
      "command": "python",
      "args": ["-m", "primer.mcp.server"],
      "env": {
        "PRIMER_SERVER_URL": "http://localhost:8000",
        "PRIMER_API_KEY": "primer_...",
        "PRIMER_ADMIN_API_KEY": "primer-admin-dev-key"
      }
    }
  }
}
```

Claude will now have access to 5 tools: `sync`, `my_stats`, `team_overview`, `friction_report`, and `recommendations`.

## 6. Connect GitHub (Optional)

GitHub integration enables OAuth login, pull request sync, commit correlation, and AI-readiness scoring for your repositories.

See the [GitHub Integration](github-integration.md) guide for step-by-step setup.

## Next Steps

- **Invite your team** — Create engineers in the admin panel and distribute API keys
- **Configure alerts** — Set friction spike and cost thresholds in Admin > Alert Thresholds
- **Customize for production** — See [Deployment](deployment.md) for Docker Compose and PostgreSQL setup
- **Explore the API** — See [API Reference](api.md) for all endpoints and schemas
