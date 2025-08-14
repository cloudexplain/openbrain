#!/bin/bash
set -e

echo "Starting SecondBrain Backend (Production)..."

# Wait for database to be ready
echo "Waiting for database..."
until pg_isready -h postgres -p 5432 -U secondbrain; do
  echo "Database is unavailable - sleeping"
  sleep 1
done
echo "Database is ready!"

# Apply database migrations
echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI server in production mode..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info