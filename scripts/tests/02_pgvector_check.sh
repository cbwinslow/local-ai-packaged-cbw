#!/usr/bin/env bash
set -euo pipefail
# Ensure pgvector extension exists in supabase-db
# Requires docker-compose to be running

echo "Checking pgvector extension in supabase-db..."
if ! docker compose ps supabase-db >/dev/null 2>&1; then
  echo "supabase-db not running; please start the stack first"
  exit 2
fi

docker compose exec -T supabase-db psql -U postgres -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null

docker compose exec -T supabase-db psql -U postgres -d postgres -c "SELECT extname FROM pg_extension;" | grep -q vector && echo "pgvector present" || (echo "pgvector missing" && exit 1)
