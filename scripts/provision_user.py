"""Provision a real GitHub user as an engineer in Primer.

Fetches the user's GitHub profile (avatar, name, email) and creates
or links an engineer record. Useful for testing with real GitHub data.

Usage:
    python scripts/provision_user.py <github_username>
        [--role admin|team_lead|engineer] [--team TEAM_NAME]
"""

import argparse
import sys

import httpx

SERVER_URL = "http://localhost:8000"
ADMIN_KEY = "primer-admin-dev-key"
ADMIN_HEADERS = {"x-admin-key": ADMIN_KEY}


def fetch_github_profile(username: str) -> dict | None:
    """Fetch public profile from GitHub API (no auth needed for public users)."""
    r = httpx.get(f"https://api.github.com/users/{username}", timeout=10)
    if r.status_code == 200:
        return r.json()
    print(f"  Failed to fetch GitHub profile for @{username}: HTTP {r.status_code}")
    return None


def find_team(name: str) -> str | None:
    """Find a team by name, return its ID."""
    r = httpx.get(f"{SERVER_URL}/api/v1/teams", headers=ADMIN_HEADERS, timeout=10)
    if r.status_code != 200:
        return None
    for team in r.json():
        if team["name"].lower() == name.lower():
            return team["id"]
    return None


def find_engineer_by_github(username: str) -> dict | None:
    """Check if an engineer with this GitHub username already exists."""
    r = httpx.get(f"{SERVER_URL}/api/v1/engineers", headers=ADMIN_HEADERS, timeout=10)
    if r.status_code != 200:
        return None
    for eng in r.json():
        if eng.get("github_username") == username:
            return eng
    return None


def find_engineer_by_email(email: str) -> dict | None:
    """Check if an engineer with this email already exists."""
    r = httpx.get(f"{SERVER_URL}/api/v1/engineers", headers=ADMIN_HEADERS, timeout=10)
    if r.status_code != 200:
        return None
    for eng in r.json():
        if eng.get("email") == email:
            return eng
    return None


def create_engineer(name: str, email: str, team_id: str | None = None) -> dict | None:
    """Create a new engineer via the API."""
    payload = {"name": name, "email": email}
    if team_id:
        payload["team_id"] = team_id
    r = httpx.post(
        f"{SERVER_URL}/api/v1/engineers", json=payload, headers=ADMIN_HEADERS, timeout=10
    )
    if r.status_code == 200:
        return r.json()
    print(f"  Failed to create engineer: HTTP {r.status_code} — {r.text[:200]}")
    return None


def update_engineer(eng_id: str, updates: dict) -> bool:
    """Patch engineer fields."""
    r = httpx.patch(
        f"{SERVER_URL}/api/v1/engineers/{eng_id}",
        json=updates,
        headers=ADMIN_HEADERS,
        timeout=10,
    )
    return r.status_code == 200


def main():
    parser = argparse.ArgumentParser(description="Provision a GitHub user as a Primer engineer")
    parser.add_argument("username", help="GitHub username to provision")
    parser.add_argument("--role", default="admin", choices=["admin", "team_lead", "engineer"])
    parser.add_argument("--team", help="Team name to assign (must already exist)")
    args = parser.parse_args()

    username = args.username

    # Check server
    try:
        httpx.get(f"{SERVER_URL}/api/v1/health", timeout=5)
    except httpx.ConnectError:
        print(f"Cannot connect to {SERVER_URL}. Start the server first.")
        sys.exit(1)

    print(f"Provisioning @{username} as {args.role}...")

    # Fetch GitHub profile
    gh = fetch_github_profile(username)
    if not gh:
        sys.exit(1)

    name = gh.get("name") or username
    email = gh.get("email") or f"{username}@users.noreply.github.com"
    avatar_url = gh.get("avatar_url", "")
    github_id = gh.get("id")

    print(f"  GitHub: {name} (@{username}), id={github_id}")
    print(f"  Email: {email}")
    print(f"  Avatar: {avatar_url[:60]}...")

    # Find team if specified
    team_id = None
    if args.team:
        team_id = find_team(args.team)
        if not team_id:
            print(f"  Team '{args.team}' not found. Create it first.")
            sys.exit(1)
        print(f"  Team: {args.team} ({team_id})")

    # Check if already exists
    existing = find_engineer_by_github(username)
    if existing:
        eng_id = existing["id"]
        print(f"  Already exists: {existing['name']} (id={eng_id})")
        print("  Updating profile fields...")
        update_engineer(
            eng_id,
            {
                "role": args.role,
                "github_username": username,
                "avatar_url": avatar_url,
                "display_name": name,
            },
        )
        if team_id:
            update_engineer(eng_id, {"team_id": team_id})
        print("  Done.")
        return

    # Check by email
    existing = find_engineer_by_email(email)
    if existing:
        eng_id = existing["id"]
        print(f"  Found by email: {existing['name']} (id={eng_id})")
        print("  Linking GitHub profile...")
        update_engineer(
            eng_id,
            {
                "role": args.role,
                "github_username": username,
                "avatar_url": avatar_url,
                "display_name": name,
            },
        )
        print("  Done.")
        return

    # Create new
    print("  Creating new engineer...")
    result = create_engineer(name, email, team_id)
    if not result:
        sys.exit(1)

    eng_id = result["engineer"]["id"]
    api_key = result["api_key"]
    print(f"  Created: id={eng_id}")
    print(f"  API key: {api_key}")

    # Set role and GitHub fields
    update_engineer(
        eng_id,
        {
            "role": args.role,
            "github_username": username,
            "avatar_url": avatar_url,
            "display_name": name,
        },
    )

    print(f"\nProvisioned @{username} as {args.role}.")
    print("  They can now log in via GitHub OAuth.")
    print(f"  Or use API key for hook integration: {api_key[:20]}...")


if __name__ == "__main__":
    main()
