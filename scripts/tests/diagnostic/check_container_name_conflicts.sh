#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "Checking for existing containers that will conflict with compose service names..."

COMPOSE_FILE="docker-compose.all-in-one.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "Compose file $COMPOSE_FILE not found; aborting" >&2
  exit 2
fi

# Extract service names (top-level entries under 'services:')
services=()
while read -r line; do
  if [[ "$line" =~ ^[[:space:]]{2}([a-zA-Z0-9_-]+):[[:space:]]*$ ]]; then
    svc="${BASH_REMATCH[1]}"
    services+=("$svc")
  fi
done < <(sed -n '1,4000p' "$COMPOSE_FILE")

echo "Found ${#services[@]} services in $COMPOSE_FILE"

conflicts=0
for svc in "${services[@]}"; do
  # Some compose deployments prefix the compose project name; check for both raw and prefixed names
  if docker ps -a --format '{{.Names}}' | grep -q "^${svc}$"; then
    echo "Conflict: a container named '${svc}' already exists"; conflicts=1
  fi
  # check common project-prefix variants
  if docker ps -a --format '{{.Names}}' | grep -q ".*${svc}.*"; then
    # show matching containers (but avoid false positives by exact prefix match)
    matches=$(docker ps -a --format '{{.Names}}' | grep -E ".*${svc}.*" || true)
    if [ -n "$matches" ]; then
      echo "Potential conflicts for service '${svc}':"; echo "$matches"; conflicts=1
    fi
  fi
done

if [ $conflicts -ne 0 ]; then
  echo "One or more container name conflicts detected. Consider removing stale containers with 'docker rm -f <name>'"
  exit 1
else
  echo "No obvious container name conflicts detected"
fi
