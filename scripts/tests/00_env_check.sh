#!/usr/bin/env bash
set -euo pipefail
# Quick environment validation for required keys used by the compose files.
REQUIRED=(
  BASE_DOMAIN
  CLOUDFLARE_API_TOKEN
  SUPABASE_DB_PASSWORD
  SECRET_KEY_BASE
  VAULT_ENC_KEY
  SERVICE_ROLE_KEY
  ANON_KEY
  POSTGRES_PASSWORD
)

missing=0
for k in "${REQUIRED[@]}"; do
  if ! grep -q "^$k=" ../.env 2>/dev/null; then
    echo "MISSING: $k (not present in .env)"
    missing=1
  else
    v=$(grep "^$k=" ../.env | sed -E 's/^.*=(.*)$/\1/')
    if [[ -z "$v" || "$v" =~ change_me ]]; then
      echo "MISSING: $k (empty or placeholder)"
      missing=1
    fi
  fi
done

if [[ $missing -eq 1 ]]; then
  echo "One or more required env vars are missing; fix .env and re-run."
  exit 2
fi

echo "Env check OK"
