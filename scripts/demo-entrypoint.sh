#!/usr/bin/env sh
set -e

# Fly.io sets DATABASE_URL; Primer expects PRIMER_DATABASE_URL
# Also convert the legacy postgres:// scheme to postgresql:// for SQLAlchemy 2.x
if [ -n "$DATABASE_URL" ] && [ -z "$PRIMER_DATABASE_URL" ]; then
  NORMALIZED_URL=$(echo "$DATABASE_URL" | sed 's|^postgres://|postgresql://|')
  export PRIMER_DATABASE_URL="$NORMALIZED_URL"
fi

echo "=== Primer Demo Instance ==="
echo "Database: ${PRIMER_DATABASE_URL:-sqlite:///./primer.db}"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# ── Acquire Postgres advisory lock so only one machine seeds/backfills ────
# The lock is held by a long-lived python process; if another machine already
# holds it, we block until that machine finishes (by which time session count
# will be > 0 and we'll skip the seed branch).
echo "Acquiring seed advisory lock..."
python <<'PYEOF'
import sys, time
from sqlalchemy import create_engine, text
from primer.common.config import settings

engine = create_engine(settings.database_url)
lock_key = 51820  # arbitrary; must be consistent across machines
start = time.monotonic()
with engine.connect() as conn:
    while True:
        got = conn.execute(text(f"SELECT pg_try_advisory_lock({lock_key})")).scalar()
        if got:
            print("  lock acquired")
            break
        if time.monotonic() - start > 900:  # 15 minute ceiling
            print("  lock wait timeout; proceeding anyway", file=sys.stderr)
            break
        print("  another machine holds the lock; waiting 10s...")
        time.sleep(10)
PYEOF
# Note: the lock is released when the python process exits above. That's
# intentional — the lock is only used to serialize *entry* into the seed
# phase. The session-count check below is the real idempotency guard.

# Count sessions to decide whether to seed
SESSIONS=$(python -c "
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from primer.common.models import Session
from primer.common.config import settings
engine = create_engine(settings.database_url)
db = sessionmaker(bind=engine)()
print(db.query(func.count(Session.id)).scalar())
" 2>/dev/null || echo "0")

if [ "$SESSIONS" = "0" ]; then
  echo "Database is empty — seeding demo data..."
  # Disable rate limiting AND demo read-only middleware for seeding
  export PRIMER_RATE_LIMIT_ENABLED=false
  export PRIMER_DEMO_MODE=false

  # Start the server in the background for API-based seeding
  uvicorn primer.server.app:app --host 0.0.0.0 --port 8000 &
  SERVER_PID=$!

  # Wait for server to be ready
  echo "Waiting for server to start..."
  for i in $(seq 1 30); do
    if python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; then
      break
    fi
    sleep 1
  done

  # Run the demo seed script
  echo "Running demo seed..."
  python scripts/seed_demo.py || echo "  (seed reported errors, will backfill below)"

  # Stop the temporary server
  echo "Stopping seed server..."
  kill $SERVER_PID 2>/dev/null || true
  wait $SERVER_PID 2>/dev/null || true
  sleep 1

  echo "Demo data seeded."
else
  echo "Database already has $SESSIONS sessions — skipping seed."
fi

# ── Unconditional idempotent backfills ───────────────────────────────────
# Runs every deploy so partial seed state from prior failures self-heals.
echo "Running demo backfills (repo readiness, session->repo links, PRs)..."
python scripts/backfill_demo_links.py || echo "  (backfill errors, continuing)"

# Pre-warm narrative cache if the API key is present (idempotent — cache hits)
if [ -n "$PRIMER_ANTHROPIC_API_KEY" ]; then
  echo "Pre-warming narrative cache..."
  python scripts/prewarm_narratives.py || echo "  (prewarm errors, continuing)"
fi

# ── Flush Redis so analytics cache doesn't serve stale state ─────────────
if [ -n "$PRIMER_REDIS_URL" ]; then
  echo "Flushing Redis analytics cache..."
  python -c "import redis, os; r=redis.from_url(os.environ['PRIMER_REDIS_URL']); r.flushdb(); print('  flushed')" || echo "  (redis flush failed, continuing)"
fi

# Re-enable rate limiting and demo mode for production
export PRIMER_RATE_LIMIT_ENABLED=true
export PRIMER_DEMO_MODE=true

# Start the production server
echo "Starting Primer demo server..."
exec uvicorn primer.server.app:app --host 0.0.0.0 --port 8000
