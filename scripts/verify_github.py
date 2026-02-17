"""Verify GitHub integration configuration and connectivity.

Usage:
    python scripts/verify_github.py           # Check all GitHub config
    python scripts/verify_github.py --sync    # Also trigger a test repo sync
"""

import argparse
import sys

import httpx

SERVER_URL = "http://localhost:8000"
ADMIN_KEY = "primer-admin-dev-key"


def check(label: str, ok: bool, detail: str = "") -> bool:
    status = "OK" if ok else "FAIL"
    msg = f"  [{status}] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return ok


def verify_oauth():
    """Verify GitHub OAuth is configured and reachable."""
    print("\n== GitHub OAuth (Dashboard Login) ==")

    r = httpx.get(f"{SERVER_URL}/api/v1/auth/github/login", timeout=10)
    if r.status_code == 501:
        check("OAuth configured", False, "PRIMER_GITHUB_CLIENT_ID not set")
        return False
    if r.status_code == 200:
        data = r.json()
        url = data.get("url", "")
        has_client_id = "client_id=" in url
        check("OAuth configured", has_client_id, url[:80] + "...")
        return has_client_id

    check("OAuth endpoint", False, f"Unexpected status {r.status_code}")
    return False


def verify_github_app():
    """Verify GitHub App is configured and can authenticate."""
    print("\n== GitHub App (PR Sync & Repo Access) ==")

    r = httpx.get(
        f"{SERVER_URL}/api/v1/analytics/github/status",
        headers={"x-admin-key": ADMIN_KEY},
        timeout=10,
    )
    if r.status_code != 200:
        check("Status endpoint", False, f"HTTP {r.status_code}")
        return False

    data = r.json()
    configured = data.get("configured", False)
    check("App configured", configured, f"app_id={data.get('app_id')}")

    if configured:
        repos = data.get("repos_count", 0)
        prs = data.get("prs_count", 0)
        check("Repos tracked", True, f"{repos} repos, {prs} PRs")

    return configured


def verify_app_connectivity(repo: str | None = None):
    """Test actual GitHub API access by fetching a known repo."""
    print("\n== GitHub API Connectivity ==")

    if not repo:
        print("  [SKIP] No repo specified. Use --repo owner/name to test.")
        return True

    r = httpx.post(
        f"{SERVER_URL}/api/v1/analytics/github/sync",
        params={"repository": repo, "since_days": 7},
        headers={"x-admin-key": ADMIN_KEY},
        timeout=30,
    )
    if r.status_code == 200:
        data = r.json()
        check(
            f"Sync {repo}",
            True,
            f"PRs: {data.get('prs_found', 0)}, commits linked: {data.get('commits_correlated', 0)}",
        )
        return True

    check(f"Sync {repo}", False, f"HTTP {r.status_code}: {r.text[:200]}")
    return False


def verify_user(username: str | None = None):
    """Check if a GitHub user is linked to an engineer."""
    if not username:
        return True

    print(f"\n== Engineer Lookup: @{username} ==")
    r = httpx.get(
        f"{SERVER_URL}/api/v1/engineers",
        headers={"x-admin-key": ADMIN_KEY},
        timeout=10,
    )
    if r.status_code != 200:
        check("Engineers endpoint", False, f"HTTP {r.status_code}")
        return False

    engineers = r.json()
    found = [e for e in engineers if e.get("github_username") == username]
    if found:
        eng = found[0]
        check(
            f"Found @{username}",
            True,
            f"id={eng['id']}, name={eng.get('name')}, role={eng.get('role')}",
        )
        has_avatar = bool(eng.get("avatar_url"))
        check("Avatar URL", has_avatar, eng.get("avatar_url", "none")[:60])
        return True

    check(f"Found @{username}", False, "No engineer linked to this GitHub username")
    print("  Hint: Login via GitHub OAuth to auto-provision, or use:")
    print(f"    python scripts/provision_user.py {username}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Verify Primer GitHub integration")
    parser.add_argument("--repo", help="Test sync against a specific repo (owner/name)")
    parser.add_argument("--user", help="Check if a GitHub username is linked")
    parser.add_argument("--sync", action="store_true", help="Also test repo sync")
    args = parser.parse_args()

    print("Primer GitHub Integration Verification")
    print("=" * 42)

    # Check server is running
    try:
        r = httpx.get(f"{SERVER_URL}/health", timeout=5)
        check("Server reachable", r.status_code == 200, SERVER_URL)
    except httpx.ConnectError:
        check("Server reachable", False, f"Cannot connect to {SERVER_URL}")
        print("\n  Start the server first: uvicorn primer.server.app:app --reload")
        sys.exit(1)

    results = []
    results.append(verify_oauth())
    results.append(verify_github_app())

    if args.sync or args.repo:
        results.append(verify_app_connectivity(args.repo))

    if args.user:
        results.append(verify_user(args.user))

    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 42}")
    print(f"Results: {passed}/{total} checks passed")

    if not all(results):
        print("\nSetup guide: see .env.example for configuration instructions")
        sys.exit(1)


if __name__ == "__main__":
    main()
