"""Seed the database with test data for development."""

import uuid
from datetime import datetime, timedelta

import httpx

SERVER_URL = "http://localhost:8000"
ADMIN_KEY = "primer-admin-dev-key"

ADMIN_HEADERS = {"x-admin-key": ADMIN_KEY}


def main():
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
    engineer_data = [
        ("Alice Chen", "alice@example.com", 0, "admin", "alicechen", 1001),
        ("Bob Smith", "bob@example.com", 0, "team_lead", "bobsmith", 1002),
        ("Carol Davis", "carol@example.com", 1, "team_lead", "caroldavis", 1003),
        ("Dan Wilson", "dan@example.com", 1, "engineer", "danwilson", 1004),
        ("Eve Martinez", "eve@example.com", 2, "engineer", "evemartinez", 1005),
    ]
    for name, email, team_idx, role, _github_user, _github_id in engineer_data:
        team_id = teams[team_idx]["id"] if teams else None
        r = httpx.post(
            f"{SERVER_URL}/api/v1/engineers",
            json={"name": name, "email": email, "team_id": team_id},
            headers=ADMIN_HEADERS,
        )
        if r.status_code == 200:
            data = r.json()
            engineers.append(data)
            print(f"Created engineer: {name} (key: {data['api_key'][:20]}...)")

            # Set role and GitHub fields via PATCH
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

    # Seed sessions for each engineer
    outcomes = ["success", "partial", "failure", "abandoned"]
    session_types = ["feature", "debugging", "refactoring", "exploration", "documentation"]
    tools = ["Read", "Edit", "Write", "Bash", "Grep", "Glob", "Task"]
    models = ["claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001"]
    friction_types = ["tool_error", "permission_denied", "timeout", "context_limit"]

    import random

    random.seed(42)

    now = datetime.utcnow()
    for eng_data in engineers:
        api_key = eng_data["api_key"]
        for day_offset in range(30):
            n_sessions = random.randint(1, 5)
            for _ in range(n_sessions):
                session_id = str(uuid.uuid4())
                duration = random.randint(60, 3600)
                msg_count = random.randint(5, 50)
                tool_count = random.randint(1, 30)

                # Random tool usages
                session_tools = random.sample(tools, k=random.randint(1, min(4, len(tools))))
                tool_usages = [
                    {"tool_name": t, "call_count": random.randint(1, 15)} for t in session_tools
                ]

                # Random model usage
                model = random.choice(models)
                inp_tokens = random.randint(500, 50000)
                out_tokens = random.randint(200, 20000)

                facets = None
                if random.random() < 0.6:  # 60% have facets
                    outcome = random.choice(outcomes)
                    friction = {}
                    if random.random() < 0.3:
                        ft = random.choice(friction_types)
                        friction = {ft: random.randint(1, 5)}
                    goal = random.choice(["feature", "bug fix", "refactor", "docs"])
                    facets = {
                        "underlying_goal": f"Working on {goal}",
                        "outcome": outcome,
                        "session_type": random.choice(session_types),
                        "brief_summary": f"Session on day -{day_offset}",
                        "friction_counts": friction if friction else None,
                    }

                payload = {
                    "session_id": session_id,
                    "api_key": api_key,
                    "project_name": random.choice(
                        ["api-service", "web-app", "cli-tool", "shared-lib"]
                    ),
                    "started_at": (
                        now - timedelta(days=day_offset, hours=random.randint(0, 8))
                    ).isoformat(),
                    "duration_seconds": duration,
                    "message_count": msg_count,
                    "user_message_count": msg_count // 2,
                    "assistant_message_count": msg_count - msg_count // 2,
                    "tool_call_count": tool_count,
                    "input_tokens": inp_tokens,
                    "output_tokens": out_tokens,
                    "primary_model": model,
                    "first_prompt": "Help me with this task",
                    "tool_usages": tool_usages,
                    "model_usages": [
                        {
                            "model_name": model,
                            "input_tokens": inp_tokens,
                            "output_tokens": out_tokens,
                        }
                    ],
                    "facets": facets,
                }
                r = httpx.post(f"{SERVER_URL}/api/v1/ingest/session", json=payload)

        print(f"Seeded sessions for {eng_data['engineer']['name']}")

    print("\nSeed complete!")


if __name__ == "__main__":
    main()
