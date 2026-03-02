# ── Stage 1: Build frontend ──────────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ── Stage 2: Python runtime ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# Copy Alembic migrations
COPY alembic.ini .
COPY alembic/ alembic/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

ENV PRIMER_FRONTEND_DIST=/app/frontend/dist

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["sh", "-c", "alembic upgrade head && uvicorn primer.server.app:app --host 0.0.0.0 --port 8000"]
