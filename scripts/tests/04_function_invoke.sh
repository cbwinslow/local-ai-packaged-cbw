#!/usr/bin/env bash
set -euo pipefail
# Invoke a simple edge function endpoint to verify Edge Runtime routing
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/.env" || true

if [[ -z "${FUNCTIONS_HOSTNAME:-}" ]]; then
  echo "Require FUNCTIONS_HOSTNAME in .env"
  exit 2
fi

# Endpoint for the smoke function (assumes a function route /hello exists)
URL="https://${FUNCTIONS_HOSTNAME}/hello"

echo "Invoking $URL"
http_status=$(curl -sS -X GET "$URL" -w "%{http_code}" -o /tmp/fn.out || true)

if [[ "$http_status" == "200" || "$http_status" == "201" ]]; then
  echo "Function returned $http_status"
  cat /tmp/fn.out
  exit 0
fi

echo "Function invoke failed (http status: $http_status)"
echo "Response body:" && sed -n '1,200p' /tmp/fn.out || true
exit 1
