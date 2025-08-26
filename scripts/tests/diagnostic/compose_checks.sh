#!/usr/bin/env bash
set -euo pipefail

# Lightweight compose validation that understands the repo's include: pattern
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "Running compose_checks..."

if [ -x "$(pwd)/docker-compose" ]; then
  DCMD="$(pwd)/docker-compose"
else
  # Prefer docker compose; fall back to docker-compose CLI if present
  if command -v docker &> /dev/null; then
    DCMD="docker compose"
  elif command -v docker-compose &> /dev/null; then
    DCMD="docker-compose"
  else
    echo "No docker compose CLI found in PATH" >&2
    exit 2
  fi
fi

echo "Using compose command: $DCMD"

# If the top-level compose file uses include:, detect it and try to expand
if grep -q "^include:" docker-compose.yml 2>/dev/null || grep -q "^include:" docker-compose.all-in-one.yml 2>/dev/null; then
  echo "Top-level 'include:' key detected in compose files. Attempting to run via wrapper or with -f files..."
fi

set +e
# Try a basic config validation on the combined all-in-one files (non-invasive)
${DCMD} -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml config > /dev/null 2> /tmp/compose_config_err.log
status=$?
if [ $status -eq 0 ]; then
  echo "Compose config OK (all-in-one + traefik)"
  rm -f /tmp/compose_config_err.log
  exit 0
else
  echo "Compose config FAILED. Showing the last 200 chars of error output:" >&2
  tail -c 200 /tmp/compose_config_err.log || true
  echo
  echo "Full error saved to /tmp/compose_config_err.log"
  exit $status
fi
