#!/usr/bin/env bash
#===============================================================================
# Script Name   : integrate-local-ai-packaged.sh
# Author        : CBW (Blaine Winslow) & ChatGPT
# Date          : 2025-08-11
# Summary       : Vendors coleam00/local-ai-packaged and produces a Traefik-ready
#                 overlay compose (docker-compose.localai.yml). Also synthesizes
#                 the vendor .env from .env.example (strong secrets + hostnames).
#                 Idempotent; safe to re-run. Requires: git, yq, openssl.
# Inputs (ENV)  : DOMAIN (required), EMAIL (optional)
# Outputs       : /opt/supa-container/compose/docker-compose.localai.yml
#                 /opt/supa-container/vendor/local-ai-packaged/.env
#===============================================================================
set -euo pipefail
APP_DIR="/opt/supa-container"
COMPOSE_DIR="${APP_DIR}/compose"
VENDOR_DIR="${APP_DIR}/vendor/local-ai-packaged"
REPO_URL="https://github.com/coleam00/local-ai-packaged.git"
BRANCH="stable"
DOMAIN="${DOMAIN:?DOMAIN is required}"
EMAIL="${EMAIL:-admin@${DOMAIN}}"

log(){ printf "[LAI] %s\n" "$*"; }

mkdir -p "${VENDOR_DIR}" "${COMPOSE_DIR}"
if [[ ! -d "${VENDOR_DIR}/.git" ]]; then
  log "Cloning ${REPO_URL} (${BRANCH}) ..."
  git clone -b "$BRANCH" "$REPO_URL" "$VENDOR_DIR"
else
  log "Updating vendor repo..."
  git -C "$VENDOR_DIR" fetch --all --prune || true
  git -C "$VENDOR_DIR" checkout "$BRANCH" || true
  git -C "$VENDOR_DIR" pull --rebase || true
fi

# --- Generate vendor .env from .env.example ---
if [[ -f "${VENDOR_DIR}/.env.example" ]]; then
  cp -f "${VENDOR_DIR}/.env.example" "${VENDOR_DIR}/.env"
  # hostnames -> your domain
  sed -i "s#^\s*\(N8N_HOSTNAME\)=.*#\1=n8n.${DOMAIN}#"           "${VENDOR_DIR}/.env" || true
  sed -i "s#^\s*\(WEBUI_HOSTNAME\)=.*#\1=openwebui.${DOMAIN}#"   "${VENDOR_DIR}/.env" || true
  sed -i "s#^\s*\(FLOWISE_HOSTNAME\)=.*#\1=flowise.${DOMAIN}#"   "${VENDOR_DIR}/.env" || true
  sed -i "s#^\s*\(SUPABASE_HOSTNAME\)=.*#\1=supabase.${DOMAIN}#" "${VENDOR_DIR}/.env" || true
  sed -i "s#^\s*\(SEARXNG_HOSTNAME\)=.*#\1=searxng.${DOMAIN}#"   "${VENDOR_DIR}/.env" || true
  sed -i "s#^\s*\(NEO4J_HOSTNAME\)=.*#\1=neo4j.${DOMAIN}#"       "${VENDOR_DIR}/.env" || true
  sed -i "s#^\s*\(OLLAMA_HOSTNAME\)=.*#\1=ollama.${DOMAIN}#"     "${VENDOR_DIR}/.env" || true
  sed -i "s#^\s*\(LETSENCRYPT_EMAIL\)=.*#\1=${EMAIL}#"           "${VENDOR_DIR}/.env" || true

  # strong secrets if missing
  gen(){ openssl rand -hex 32; }
  ensure(){ local k="$1"; grep -q "^${k}=" "${VENDOR_DIR}/.env" || echo "${k}=$(gen)" >> "${VENDOR_DIR}/.env"; }
  ensure N8N_ENCRYPTION_KEY
  ensure N8N_USER_MANAGEMENT_JWT_SECRET
  ensure POSTGRES_PASSWORD
  ensure JWT_SECRET
  ensure NEXTAUTH_SECRET
  ensure ENCRYPTION_KEY
  ensure CLICKHOUSE_PASSWORD
  ensure MINIO_ROOT_PASSWORD
  ensure LANGFUSE_SALT
  grep -q '^ANON_KEY='         "${VENDOR_DIR}/.env" || echo "ANON_KEY=$(gen)"          >> "${VENDOR_DIR}/.env"
  grep -q '^SERVICE_ROLE_KEY=' "${VENDOR_DIR}/.env" || echo "SERVICE_ROLE_KEY=$(gen)"  >> "${VENDOR_DIR}/.env"
  grep -q '^POOLER_TENANT_ID=' "${VENDOR_DIR}/.env" || uuidgen | awk '{print "POOLER_TENANT_ID="$1}' >> "${VENDOR_DIR}/.env"
else
  log "[WARN] .env.example not found in vendor repo; skipping .env synthesis"
fi

# --- Merge vendor compose & Traefik-ize ---
TMP="/tmp/localai_full.yml"
if [[ -f "${VENDOR_DIR}/docker-compose.yml" ]]; then
  FILES=("${VENDOR_DIR}/docker-compose.yml")
  [[ -f "${VENDOR_DIR}/docker-compose.override.public.yml" ]] && FILES+=("${VENDOR_DIR}/docker-compose.override.public.yml")
  [[ -f "${VENDOR_DIR}/docker-compose.override.public.supabase.yml" ]] && FILES+=("${VENDOR_DIR}/docker-compose.override.public.supabase.yml")

  # merge
  yq ea '. as $item ireduce ({}; . * $item)' "${FILES[@]}" > "$TMP"
  # drop caddy if present
  yq -i 'del(.services.caddy)' "$TMP" || true
  # add reverse-proxy network
  yq -i '.networks."reverse-proxy".external = false' "$TMP"

  add_labels() {
    local svc="$1" host="$2"
    yq -i ".services.${svc}.labels += [\"traefik.enable=true\", \"traefik.http.routers.${svc}.rule=Host(\`${host}\`)\", \"traefik.http.routers.${svc}.entrypoints=websecure\", \"traefik.http.routers.${svc}.tls.certresolver=le\"]" "$TMP" 2>/dev/null || true
    yq -i ".services.${svc}.networks += [\"reverse-proxy\"]" "$TMP" 2>/dev/null || true
    yq -i "del(.services.${svc}.ports)" "$TMP" 2>/dev/null || true
  }
  add_labels n8n            "n8n.${DOMAIN}"
  add_labels open-webui     "openwebui.${DOMAIN}"
  add_labels flowise        "flowise.${DOMAIN}"
  add_labels searxng        "searxng.${DOMAIN}"
  add_labels neo4j          "neo4j.${DOMAIN}"
  add_labels supabase-kong  "supabase.${DOMAIN}"
  add_labels langfuse       "langfuse.${DOMAIN}"

  cp "$TMP" "${COMPOSE_DIR}/docker-compose.localai.yml"
  log "Wrote compose/docker-compose.localai.yml"
else
  log "[WARN] vendor docker-compose.yml missing; overlay not generated"
fi

log "Integration complete."
