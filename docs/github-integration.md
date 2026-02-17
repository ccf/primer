# GitHub Integration

Primer integrates with GitHub in two ways:

1. **GitHub OAuth** — Engineers log into the dashboard with their GitHub account
2. **GitHub App** — Primer syncs pull requests, correlates commits, and checks AI-readiness on repositories

Both are optional. You can use one without the other.

## GitHub OAuth (Dashboard Login)

OAuth lets engineers sign in with GitHub instead of using API keys for dashboard access.

### Create an OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Fill in:
   - **Application name**: Primer (or your preferred name)
   - **Homepage URL**: `http://localhost:5173`
   - **Authorization callback URL**: `http://localhost:5173/auth/callback`
4. Click **Register application**
5. Copy the **Client ID**
6. Click **Generate a new client secret** and copy it

### Configure Primer

Add to your `.env` file (or set as environment variables):

```bash
PRIMER_GITHUB_CLIENT_ID=Iv1.abc123...
PRIMER_GITHUB_CLIENT_SECRET=abc123secret...
PRIMER_GITHUB_REDIRECT_URI=http://localhost:5173/auth/callback
PRIMER_JWT_SECRET_KEY=generate-a-secure-random-string
```

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### How Login Works

1. User clicks "Sign in with GitHub" on the login page
2. Redirected to GitHub for authorization (scopes: `read:user`, `user:email`)
3. GitHub redirects back to `/auth/callback` with an authorization code
4. Primer exchanges the code for a GitHub access token
5. Fetches the user's profile (name, username, avatar, email)
6. Finds or creates an engineer record (matches by GitHub ID, then email)
7. Issues JWT access and refresh tokens as HTTP-only cookies

### Auto-Provisioning

When a GitHub user logs in for the first time:
- If an engineer with the same **GitHub ID** exists, their profile is updated
- If an engineer with the same **email** exists, their GitHub profile is linked
- Otherwise, a new engineer is created with role `engineer`

Admins can pre-provision users with `python scripts/provision_user.py <github_username>`.

## GitHub App (PR Sync & AI Readiness)

The GitHub App lets Primer:
- Sync pull request data (additions, deletions, review comments, merge status)
- Correlate session commits with PRs
- Check repositories for CLAUDE.md, AGENTS.md, and .claude/ configuration
- Receive real-time webhooks for push and PR events

### Create a GitHub App

1. Go to [GitHub App Settings](https://github.com/settings/apps)
2. Click **New GitHub App**
3. Fill in:
   - **GitHub App name**: Primer Analytics (must be globally unique)
   - **Homepage URL**: `http://localhost:5173`
   - **Webhook URL**: Leave blank for now (or use an ngrok/cloudflared tunnel URL + `/api/v1/webhooks/github`)
   - **Webhook secret**: Generate one: `python -c "import secrets; print(secrets.token_hex(32))"`
4. Set **Permissions**:
   - Repository > **Contents**: Read-only
   - Repository > **Pull requests**: Read-only
   - Repository > **Metadata**: Read-only (auto-granted)
5. Subscribe to **events** (optional, for real-time updates):
   - Pull request
   - Push
6. Set **Where can this GitHub App be installed?** to "Only on this account"
7. Click **Create GitHub App**

### Generate a Private Key

1. On the app's settings page, scroll to **Private keys**
2. Click **Generate a private key**
3. A `.pem` file is downloaded

### Install the App

1. On the app's settings page, click **Install App** in the left sidebar
2. Choose your account or organization
3. Select **All repositories** or specific repositories
4. Note the **Installation ID** from the URL: `https://github.com/settings/installations/<ID>`

### Configure Primer

Add to your `.env` file:

```bash
PRIMER_GITHUB_APP_ID=123456
PRIMER_GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
PRIMER_GITHUB_INSTALLATION_ID=78901234
PRIMER_GITHUB_WEBHOOK_SECRET=your-webhook-secret
```

For the private key, either:
- Paste the PEM content with `\n` replacing actual newlines
- Or load from file before starting: `export PRIMER_GITHUB_APP_PRIVATE_KEY=$(cat path/to/key.pem)`

### Verify the Connection

```bash
python scripts/verify_github.py
```

This checks OAuth configuration, App authentication, and API access.

To test syncing a specific repository:

```bash
python scripts/verify_github.py --repo owner/repo-name
```

### Manual Sync

Trigger a PR sync for a repository via the admin API:

```bash
curl -X POST "http://localhost:8000/api/v1/analytics/github/sync?repository=owner/repo" \
  -H "x-admin-key: primer-admin-dev-key"
```

### AI-Readiness Scoring

When a repository is synced, Primer checks for:

| File/Directory | Points | What it indicates |
|---------------|--------|-------------------|
| `CLAUDE.md` | 50 | Project instructions for Claude Code |
| `.claude/` | 30 | Claude Code configuration directory |
| `AGENTS.md` | 20 | Agent delegation instructions |

Scores are cached for 24 hours. Results appear in the AI Maturity page under "Project Readiness."

### Webhooks (Optional)

If you configure a webhook URL, Primer receives real-time notifications:

- **Push events** — Correlates commit SHAs with tracked repositories
- **Pull request events** — Creates/updates PR records on open, close, merge, and sync

For local development, use a tunnel:

```bash
# ngrok
ngrok http 8000
# Then set webhook URL to: https://abc123.ngrok.io/api/v1/webhooks/github

# cloudflared
cloudflared tunnel --url http://localhost:8000
```

## Provision a Real User

To create an engineer linked to a real GitHub account:

```bash
python scripts/provision_user.py your-github-username --role admin --team Platform
```

This fetches the user's GitHub profile (avatar, name, email) and creates or links an engineer record. The user can then log in via GitHub OAuth and see their real avatar in the dashboard.
