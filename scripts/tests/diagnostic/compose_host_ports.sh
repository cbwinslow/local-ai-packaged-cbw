#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="docker-compose.all-in-one.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "Compose file $COMPOSE_FILE not found; aborting" >&2
  exit 2
fi

echo "Scanning compose file for 'ports' with host bindings..."

declare -A host_ports
while IFS= read -r line; do
  # match lines like: - '127.0.0.1:3000:3000'
  if [[ $line =~ ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}:)?([0-9]{2,5}):([0-9]{2,5}) ]]; then
    host=${BASH_REMATCH[1]}
    port=${BASH_REMATCH[2]}
    host_ports[$port]=$(( ${host_ports[$port]:-0} + 1 ))
  fi
done < <(sed -n '1,4000p' "$COMPOSE_FILE")

echo "Host port usage summary (port:count)"
for p in "${!host_ports[@]}"; do
  echo "$p: ${host_ports[$p]}"
  if [ ${host_ports[$p]} -gt 1 ]; then
    echo "Warning: port $p is published more than once in compose file"
  fi
done

echo "compose_host_ports check completed"
