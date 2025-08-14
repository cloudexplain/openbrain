#!/bin/bash
set -e

echo "Starting SecondBrain Backend..."

# Wait for database to be ready (additional safety)
echo "Waiting for database..."
until pg_isready -h postgres -p 5432 -U secondbrain; do
  echo "Database is unavailable - sleeping"
  sleep 1
done
echo "Database is ready!"

# Install dependencies if needed
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Apply database migrations (never generate them in container)
echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI server..."
exec python run.py