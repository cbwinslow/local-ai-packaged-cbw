#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "Checking for Neo4j data lock files in compose volumes and local dirs..."

# Look for common neo4j data volume names in docker volumes
vols=$(docker volume ls --format '{{.Name}}' 2>/dev/null || true)
found=0
for v in $vols; do
  if echo "$v" | grep -qi "neo4j"; then
    echo "Inspecting volume: $v"
  docker run --rm -v ${v}:/data alpine sh -c 'ls -la /data || true; echo "---- find store_lock files:"; find /data -name store_lock -print || true'
    found=1
  fi
done

if [ $found -eq 0 ]; then
  echo "No docker volumes with 'neo4j' in the name found. Checking local neo4j mount paths (if any)".
  # Check common local path
  if [ -d ./neo4j/data ]; then
    echo "Found ./neo4j/data"
    find ./neo4j/data -name store_lock -ls || true
  else
    echo "No obvious local neo4j data dir found." 
  fi
fi

echo "neo4j_lock_check completed"
