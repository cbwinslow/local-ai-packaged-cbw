#!/usr/bin/env bash
set -euo pipefail

# Quickstart with selectable reverse proxy (caddy_ext or traefik) using override compose
# Usage: BASE_DOMAIN=example.com REVERSE_PROXY=traefik ./quickstart_proxy.sh --profile cpu
# Defaults: REVERSE_PROXY=caddy_ext, BASE_DOMAIN=localhost

REVERSE_PROXY="${REVERSE_PROXY:-caddy_ext}" # caddy_ext | traefik
BASE_DOMAIN="${BASE_DOMAIN:-localhost}"
EXTRA_PROFILES=()

# Pass any --profile args through; ensure proxy profile added
for arg in "$@"; do
  case "$arg" in
    --profile)
      # include following value too
      EXTRA_PROFILES+=("$arg")
      shift || true
      ;;
    *)
      EXTRA_PROFILES+=("$arg")
      ;;
  esac
  shift || true
  break
done

if [[ ! -f .env ]]; then
  echo "[quickstart] .env not found; generating minimal .env (non-destructive)." >&2
  echo "BASE_DOMAIN=$BASE_DOMAIN" > .env
  echo "# Add secrets or copy from .env.example as needed" >> .env
fi

if [[ "$REVERSE_PROXY" != "caddy_ext" && "$REVERSE_PROXY" != "traefik" ]]; then
  echo "[quickstart] Invalid REVERSE_PROXY=$REVERSE_PROXY (must be caddy_ext|traefik)" >&2
  exit 1
fi

PROXY_PROFILE="$REVERSE_PROXY"

echo "[quickstart] Starting stack with proxy profile: $PROXY_PROFILE (BASE_DOMAIN=$BASE_DOMAIN)"

docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.proxies.yml \
  --profile cpu \
  --profile public \
  --profile "$PROXY_PROFILE" \
  up -d

echo "[quickstart] Services launching. Portal will be available (after DNS/ACME) at:"
if [[ "$REVERSE_PROXY" == "caddy_ext" ]]; then
  echo "  https://portal.$BASE_DOMAIN"
else
  echo "  https://portal.$BASE_DOMAIN"
fi
