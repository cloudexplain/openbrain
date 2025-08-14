#!/bin/bash
# Script to ensure database tables exist

echo "Checking if database tables exist..."

# Wait for PostgreSQL to be ready
until pg_isready -U secondbrain -d secondbrain -h localhost; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

# Check if tables exist
TABLE_COUNT=$(psql -U secondbrain -d secondbrain -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")

if [ "$TABLE_COUNT" -eq "0" ] || [ "$TABLE_COUNT" -lt "4" ]; then
  echo "Tables missing or incomplete. Creating database schema..."
  
  # Run initialization scripts
  for script in /docker-entrypoint-initdb.d/*.sql; do
    echo "Running $script..."
    psql -U secondbrain -d secondbrain < "$script"
  done
  
  echo "Database initialization complete!"
else
  echo "Database tables already exist (found $TABLE_COUNT tables)"
fi