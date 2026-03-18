#!/bin/bash
# FlightMatch quick-start script
# Run after setting up PostgreSQL and Redis per README

set -e
cd "$(dirname "$0")"

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Starting FlightMatch API on http://localhost:8000"
echo "    Docs: http://localhost:8000/docs"
echo "    API Key (dev): change-me-in-production"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
