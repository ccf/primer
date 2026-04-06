#!/usr/bin/env sh
set -e

# Fly.io sets DATABASE_URL; Primer expects PRIMER_DATABASE_URL
if [ -n "$DATABASE_URL" ] && [ -z "$PRIMER_DATABASE_URL" ]; then
  export PRIMER_DATABASE_URL="$DATABASE_URL"
fi

echo "=== Primer Demo Instance ==="
echo "Database: ${PRIMER_DATABASE_URL:-sqlite:///./primer.db}"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Seed demo data if the database is empty
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
  # Disable rate limiting for seeding
  export PRIMER_RATE_LIMIT_ENABLED=false

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
  python scripts/seed_demo.py

  # Stop the temporary server
  echo "Stopping seed server..."
  kill $SERVER_PID 2>/dev/null || true
  wait $SERVER_PID 2>/dev/null || true
  sleep 1

  echo "Demo data seeded successfully."
else
  echo "Database already has $SESSIONS sessions — skipping seed."
fi

# Re-enable rate limiting for production
export PRIMER_RATE_LIMIT_ENABLED=true

# Start the production server
echo "Starting Primer demo server..."
exec uvicorn primer.server.app:app --host 0.0.0.0 --port 8000
