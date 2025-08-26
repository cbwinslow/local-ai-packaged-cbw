#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
echo "Checking common host ports for listeners and conflicts..."

ports=(80 443 3000 5432 6379 8000 8001 4000 7687 7474)

for p in "${ports[@]}"; do
  if ss -ltn "sport = :$p" | grep -q LISTEN; then
    echo "Port $p: in use" 
    ss -ltnp "sport = :$p" 2>/dev/null | sed -n '1,4p'
  else
    echo "Port $p: free"
  fi
done

echo "host_port_conflicts check completed"
