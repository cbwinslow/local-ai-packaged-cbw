#!/usr/bin/env bash
set -euo pipefail
# Validate docker compose merge and report problems
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Running docker compose config validation..."
docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml config > /dev/null && echo "Compose config OK" || (echo "Compose config FAILED" && docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml config --quiet)
