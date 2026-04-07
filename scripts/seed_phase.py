"""Single-machine seed orchestration for the demo entrypoint.

Holds a Postgres advisory lock across the entire seed-decision phase so
that two machines deploying simultaneously cannot both observe an empty
DB and start seeding. Backfills run after the lock is released because
they are idempotent and safe to run concurrently.

Usage (from demo-entrypoint.sh):

    python scripts/seed_phase.py

Exits 0 in all normal scenarios. Errors during the seed are logged but
do not abort the script — the unconditional backfill phase will repair
any partial state.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker

from primer.common.config import settings
from primer.common.models import Session as SessionModel

LOCK_KEY = 51820  # arbitrary; must match across machines
LOCK_WAIT_SECONDS = 900  # 15 min ceiling
SERVER_URL = "http://localhost:8000"


def _wait_for_server(timeout: int = 60) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"{SERVER_URL}/health", timeout=2)  # noqa: S310
            return True
        except Exception:
            time.sleep(1)
    return False


def _run_seed() -> None:
    """Start a temp uvicorn, run seed_demo against it, then stop uvicorn."""
    env = os.environ.copy()
    env["PRIMER_RATE_LIMIT_ENABLED"] = "false"
    env["PRIMER_DEMO_MODE"] = "false"

    print("  starting temp server for seeding...")
    server = subprocess.Popen(
        ["uvicorn", "primer.server.app:app", "--host", "0.0.0.0", "--port", "8000"],
        env=env,
    )
    try:
        if not _wait_for_server():
            print("  temp server did not become healthy; aborting seed", file=sys.stderr)
            return

        print("  running seed_demo.py...")
        result = subprocess.run(
            [sys.executable, "scripts/seed_demo.py"],
            env=env,
            check=False,
        )
        if result.returncode != 0:
            print(
                f"  seed_demo exited with {result.returncode} (continuing — backfill will repair)",
                file=sys.stderr,
            )
    finally:
        print("  stopping temp server...")
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


def main() -> int:
    engine = create_engine(settings.database_url)

    # Hold the advisory lock for the entire seed-decision phase by keeping
    # this connection open until we've finished (or skipped) seeding.
    with engine.connect() as conn:
        start = time.monotonic()
        while True:
            got = conn.execute(text(f"SELECT pg_try_advisory_lock({LOCK_KEY})")).scalar()
            if got:
                print(f"Acquired seed advisory lock ({LOCK_KEY})")
                break
            if time.monotonic() - start > LOCK_WAIT_SECONDS:
                print(
                    f"Timed out waiting for seed lock after {LOCK_WAIT_SECONDS}s; "
                    "another machine likely seeded — proceeding without lock",
                    file=sys.stderr,
                )
                break
            print("  another machine holds the seed lock; waiting 10s...")
            time.sleep(10)

        # Re-check session count *while holding the lock*
        session_factory = sessionmaker(bind=engine)
        with session_factory() as db:
            session_count = db.query(func.count(SessionModel.id)).scalar() or 0

        if session_count == 0:
            print("Database is empty — running seed under lock")
            _run_seed()
        else:
            print(f"Database already has {session_count} sessions — skipping seed")

        # Lock is released when this `with engine.connect()` block exits

    return 0


if __name__ == "__main__":
    sys.exit(main())
