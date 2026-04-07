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

# Seed phase: holds a Postgres advisory lock across the empty-DB check and
# the actual seed run, so two machines deploying together can't both seed.
echo "Running seed phase..."
python scripts/seed_phase.py || echo "  (seed phase reported errors, continuing)"

# Unconditional idempotent backfills — repair any partial seed state from
# prior failed deploys. Safe to run multiple times.
echo "Running demo backfills (repo readiness, session->repo links, PRs)..."
python scripts/backfill_demo_links.py || echo "  (backfill errors, continuing)"

# Pre-warm narrative cache if the API key is present (idempotent — cache hits)
if [ -n "$PRIMER_ANTHROPIC_API_KEY" ]; then
  echo "Pre-warming narrative cache..."
  python scripts/prewarm_narratives.py || echo "  (prewarm errors, continuing)"
fi

# Flush Redis so analytics cache doesn't serve stale state from before backfill
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
