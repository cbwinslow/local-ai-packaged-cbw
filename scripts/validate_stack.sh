#!/usr/bin/env bash
set -Eeuo pipefail
log(){ printf "[%s] %s\n" "$(date +%F\ %T)" "$*"; }
require(){ command -v "$1" >/dev/null 2>&1 || { log "Missing dep: $1"; exit 1; }; }
require docker; require curl; require awk
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE" || true
: "${DOMAIN:=}"
fail=0
log "Checking container health..."
while read -r n s; do
  if [[ "$s" != "healthy" ]]; then
    log "UNHEALTHY: $n ($s)"; docker logs --tail=80 "$n" || true; fail=1
  else
    log "OK: $n"
  fi
done < <(docker ps --format '{{.Names}} {{.Status}}' | awk '{print $1, $3}' | sed 's/(//;s/)//')
if [[ -n "$DOMAIN" ]]; then
  for url in \
    "https://$DOMAIN/" \
    "https://api.$DOMAIN/healthz" \
    "https://openwebui.$DOMAIN/" \
    "https://flowise.$DOMAIN/" \
    "https://n8n.$DOMAIN/" \
    "https://grafana.$DOMAIN/"; do
      if curl -fsS --max-time 10 "$url" >/dev/null; then log "OK: $url"; else log "WARN: $url unreachable"; fail=1; fi
  done
else
  log "DOMAIN not set, skipping HTTP probes."
fi
[[ $fail -eq 0 ]] && { log "Validation passed."; exit 0; } || { log "Validation found issues."; exit 2; }
