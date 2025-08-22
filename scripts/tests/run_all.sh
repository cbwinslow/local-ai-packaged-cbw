#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/scripts/tests"

SCRIPTS=(
  00_env_check.sh
  01_compose_config.sh
  02_pgvector_check.sh
  03_storage_smoke.sh
  04_function_invoke.sh
  05_realtime_ws_test.py
  06_realtime_postgres_notify.py
)

failed=0
for s in "${SCRIPTS[@]}"; do
  echo
  echo "---- Running $s ----"
  if [[ "$s" == *.py ]]; then
    python3 "$s" || failed=1
  else
    bash "$s" || failed=1
  fi
done

if [[ $failed -eq 0 ]]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "ONE OR MORE TESTS FAILED"
  exit 2
fi
