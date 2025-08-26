#!/usr/bin/env bash
set -Eeuo pipefail
log(){ printf "[%s] %s\n" "$(date +%F\ %T)" "$*"; }
die(){ log "ERROR: $*"; exit 1; }
require(){ command -v "$1" >/dev/null 2>&1 || die "Missing dep: $1"; }
require curl; require jq
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"
[[ -f "$ENV_FILE" ]] || die ".env not found"
# shellcheck disable=SC1090
source "$ENV_FILE"
: "${DOMAIN:?DOMAIN required}"
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN required}"
: "${CLOUDFLARE_ZONE_ID:?CLOUDFLARE_ZONE_ID required}"
API="https://api.cloudflare.com/client/v4"
H=(-H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" -H "Content-Type: application/json")
PUBLIC_IP="${PUBLIC_IP:-$(curl -fsS https://ipv4.icanhazip.com || true)}"
[[ -n "$PUBLIC_IP" ]] || die "Could not detect PUBLIC_IP. Set it in .env"
subs=( "@" "api" "flowise" "n8n" "openwebui" "grafana" "neo4j" "traefik" )
upsert(){ local name="$1" target="$2" type="$3" proxied="$4"; local fqdn; [[ "$name" == "@" ]] && fqdn="$DOMAIN" || fqdn="$name.$DOMAIN"
  local rid payload; rid="$(curl -fsS "${API}/zones/${CLOUDFLARE_ZONE_ID}/dns_records?type=${type}&name=${fqdn}" "${H[@]}" | jq -r '.result[0].id // empty')"
  payload=$(jq -n --arg name "$fqdn" --arg content "$target" --argjson proxied "$proxied" '{type:"A",name:$name,content:$content,ttl:1,proxied:$proxied}')
  if [[ -n "$rid" ]]; then
    curl -fsS -X PUT "${API}/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${rid}" "${H[@]}" --data "$payload" >/dev/null && log "Updated A $fqdn -> $target"
  else
    curl -fsS -X POST "${API}/zones/${CLOUDFLARE_ZONE_ID}/dns_records" "${H[@]}" --data "$payload" >/dev/null && log "Created A $fqdn -> $target"
  fi
}
upsert "@" "$PUBLIC_IP" "A" true
for s in "${subs[@]}"; do [[ "$s" == "@" ]] && continue; upsert "$s" "$PUBLIC_IP" "A" true; done
log "Cloudflare DNS sync complete for $DOMAIN."
