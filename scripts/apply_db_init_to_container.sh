#!/usr/bin/env bash
set -euo pipefail
# Helper: copy DB init SQL files into supabase-db container and run them if needed
CONTAINER=${1:-supabase-db}
INIT_DIR_HOST=${2:-./supabase/docker/volumes/db/init}

if ! docker compose ps "$CONTAINER" >/dev/null 2>&1; then
  echo "Container $CONTAINER not running. Start the stack first."
  exit 2
fi

for f in "$INIT_DIR_HOST"/*.sql; do
  [ -e "$f" ] || continue
  echo "Applying $f to $CONTAINER"
  docker cp "$f" "$CONTAINER":/tmp/ || true
  docker compose exec -T "$CONTAINER" psql -U postgres -d postgres -f "/tmp/$(basename "$f")"
  docker compose exec -T "$CONTAINER" rm -f "/tmp/$(basename "$f")" || true
done

echo "DB init files applied"
