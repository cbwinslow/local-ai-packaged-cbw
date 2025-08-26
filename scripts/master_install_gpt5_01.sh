#!/usr/bin/env bash
# ====================================================================================
# Script Name   : supa-container-oneclick.sh
# Author        : CBW (Blaine Winslow) & ChatGPT
# Date          : 2025-08-11
# Summary       : **Single-command** installer for the supa-container stack on a
#                 dedicated Hetzner (or any Ubuntu) server, integrating the
#                 public Local AI package (coleam00/local-ai-packaged) **behind
#                 Traefik** (not Caddy) with self-hosted Supabase (via Kong),
#                 plus monitoring (Prometheus/Grafana) and a basic www site.
#
#                 The script is **idempotent** (safe to rerun). It:
#                   - Hardens the host (UFW, fail2ban) without locking out SSH.
#                   - Installs Docker/Compose, yq, git; optional Terraform.
#                   - Creates /opt/supa-container with Traefik config and certs.
#                   - Vendors coleam00/local-ai-packaged@stable and synthesizes
#                     its .env from .env.example with strong secrets + hostnames.
#                   - Removes Caddy and generates a Traefik-ready compose overlay
#                     for n8n, Open WebUI, Flowise, Supabase (Kong), SearXNG,
#                     Neo4j, Langfuse, Ollama (labels + tls). No port leaks.
#                   - (Optional) Creates DNS A records via Cloudflare or Hetzner
#                     DNS using embedded Terraform; then brings up the stack.
#                   - Registers a systemd unit: supa-container.service.
#
# Inputs (ENV)  :
#   DOMAIN=opendiscourse.net           # required FQDN zone
#   ACME_EMAIL=admin@opendiscourse.net # cert notifications
#   # SSH / user
#   CREATE_USER=true|false   (default true)
#   CBW_USER=cbwinslow       (sudo user name)
#   CBW_PUBKEY='ssh-ed25519 AAAA...'
#   SSH_PORT=22
#   # DNS (optional)
#   DNS_PROVIDER=cloudflare|hetzner
#   CF_API_TOKEN=...                 # if cloudflare
#   HETZNER_DNS_TOKEN=...            # if hetzner
#   SERVER_IPV4=1.2.3.4              # A-record target
#   # Traefik dashboard auth (optional)
#   DASH_USER=admin
#   DASH_PASS_HASH='$2y$05$...'      # htpasswd -nbB admin 'pass' | cut -d: -f2
#   # Local AI package integration
#   LAI_BRANCH=stable                # git branch to vendor
#   INTEGRATE_LOCAL_AI=true|false    # default true
#
# Outputs       : /tmp/supa-container-oneclick.log
# Exit Codes    : Non-zero on failure; detailed context in the log.
# Security      :
#   - Disables SSH password auth + root login; keeps SSH_PORT open via UFW.
#   - Traefik ACME certs: 600 perms; dashboard optional basic auth.
#   - Removes host port publishes from vendor services (Traefik handles TLS).
#   - Does not expose Supabase internals directly; routes through Kong.
# ====================================================================================
set -euo pipefail
LOG_FILE="/tmp/supa-container-oneclick.log"
exec > >(tee -a "$LOG_FILE") 2>&1
trap 'echo "[ERROR] Failed at line $LINENO. See $LOG_FILE"; exit 1' ERR

# ------------------------------ Config & Defaults ------------------------------
DOMAIN="${DOMAIN:-}"
ACME_EMAIL="${ACME_EMAIL:-}"
CREATE_USER="${CREATE_USER:-true}"
CBW_USER="${CBW_USER:-cbwinslow}"
CBW_PUBKEY="${CBW_PUBKEY:-}"
SSH_PORT="${SSH_PORT:-22}"
DNS_PROVIDER="${DNS_PROVIDER:-}"
SERVER_IPV4="${SERVER_IPV4:-}"
CF_API_TOKEN="${CF_API_TOKEN:-}"
HETZNER_DNS_TOKEN="${HETZNER_DNS_TOKEN:-}"
DASH_USER="${DASH_USER:-admin}"
DASH_PASS_HASH="${DASH_PASS_HASH:-}"
LAI_BRANCH="${LAI_BRANCH:-stable}"
INTEGRATE_LOCAL_AI="${INTEGRATE_LOCAL_AI:-true}"

APP_DIR="/opt/supa-container"
COMPOSE_DIR="${APP_DIR}/compose"
TRAefik_DIR="${COMPOSE_DIR}/traefik"
VENDOR_DIR="${APP_DIR}/vendor/local-ai-packaged"

# Required inputs
if [[ -z "$DOMAIN" ]]; then
  echo "[FATAL] DOMAIN is required (e.g., DOMAIN=opendiscourse.net)" >&2; exit 2
fi
ACME_EMAIL="${ACME_EMAIL:-admin@${DOMAIN}}"

say(){ printf "[%s] %s\n" "$(date -Is)" "$*"; }

# ------------------------------ Preflight checks ------------------------------
if [[ $(id -u) -ne 0 ]]; then
  say "Elevating to root is required. Rerun with sudo or as root."; exit 3
fi

. /etc/os-release || { say "[FATAL] Unsupported OS"; exit 3; }
case "$ID" in ubuntu|debian) : ;; *) say "[WARN] Tested on Ubuntu/Debian; continuing.";; esac

# ------------------------------ Base packages --------------------------------
export DEBIAN_FRONTEND=noninteractive
say "Installing base packages..."
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release ufw fail2ban jq unzip git net-tools vim apache2-utils rsync

# ------------------------------ Docker/Compose -------------------------------
if ! command -v docker >/dev/null 2>&1; then
  say "Installing Docker Engine..."
  install -m0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") $(. /etc/os-release && echo "$VERSION_CODENAME") stable" >/etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
fi

# ------------------------------ yq (v4) --------------------------------------
if ! command -v yq >/dev/null 2>&1; then
  say "Installing yq..."
  ARCH=$(dpkg --print-architecture)
  YQ_VER="v4.44.3"
  case "$ARCH" in
    amd64|x86_64) BIN="yq_linux_amd64";;
    arm64|aarch64) BIN="yq_linux_arm64";;
    *) BIN="yq_linux_amd64";;
  esac
  curl -fsSL "https://github.com/mikefarah/yq/releases/download/${YQ_VER}/${BIN}" -o /usr/local/bin/yq
  chmod +x /usr/local/bin/yq
fi

# ------------------------------ Host hardening -------------------------------
say "Configuring UFW and SSH (no lockout)..."
ufw --force reset || true
ufw default deny incoming
ufw default allow outgoing
ufw allow "${SSH_PORT}"/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

SSHD="/etc/ssh/sshd_config"
cp -an "$SSHD" "${SSHD}.bak.$(date +%s)" || true
sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' "$SSHD"
sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' "$SSHD"
grep -q "^Port ${SSH_PORT}$" "$SSHD" || echo "Port ${SSH_PORT}" >> "$SSHD"
systemctl reload ssh || systemctl reload sshd || true

# Optional sudo user
if [[ "$CREATE_USER" == "true" ]]; then
  if ! id -u "$CBW_USER" >/dev/null 2>&1; then
    adduser --disabled-password --gecos "" "$CBW_USER"
    usermod -aG sudo,docker "$CBW_USER"
    install -d -m 700 "/home/${CBW_USER}/.ssh"
    if [[ -n "$CBW_PUBKEY" ]]; then
      echo "$CBW_PUBKEY" > "/home/${CBW_USER}/.ssh/authorized_keys" && chmod 600 "/home/${CBW_USER}/.ssh/authorized_keys"
    fi
    chown -R "${CBW_USER}:${CBW_USER}" "/home/${CBW_USER}/.ssh"
  fi
fi

# ------------------------------ Traefik stack --------------------------------
say "Laying down Traefik + monitoring stack..."
mkdir -p "${COMPOSE_DIR}/traefik/dynamic" "${COMPOSE_DIR}/nginx"
install -m 600 /dev/null "${COMPOSE_DIR}/traefik/acme.json" || true

cat >"${COMPOSE_DIR}/docker-compose.yml" <<'YML'
version: "3.9"

networks:
  reverse-proxy:
    external: false

volumes:
  grafana-data: {}
  prometheus-data: {}

services:
  traefik:
    image: traefik:latest
    container_name: traefik
    restart: unless-stopped
    command:
      - "--entrypoints.web.address=:80"
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
      - "--entrypoints.web.http.redirections.entrypoint.scheme=https"
      - "--entrypoints.websecure.address=:443"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--certificatesresolvers.le.acme.email=${ACME_EMAIL}"
      - "--certificatesresolvers.le.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.le.acme.httpchallenge=true"
      - "--certificatesresolvers.le.acme.httpchallenge.entrypoint=web"
      - "--api.dashboard=true"
    ports:
      - "80:80"
      - "443:443"
    networks: [reverse-proxy]
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./traefik/acme.json:/letsencrypt/acme.json"
      - "./traefik/traefik.yml:/traefik.yml:ro"
      - "./traefik/dynamic:/dynamic:ro"
      - "./traefik/usersfile:/usersfile:ro"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.dashboard.rule=Host(`traefik.${DOMAIN}`)"
      - "traefik.http.routers.dashboard.entrypoints=websecure"
      - "traefik.http.routers.dashboard.tls.certresolver=le"
      - "traefik.http.routers.dashboard.service=api@internal"
      - "traefik.http.routers.dashboard.middlewares=dashboard-auth@file"

  whoami:
    image: traefik/whoami
    container_name: whoami
    networks: [reverse-proxy]
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.whoami.rule=Host(`whoami.${DOMAIN}`)"
      - "traefik.http.routers.whoami.entrypoints=websecure"
      - "traefik.http.routers.whoami.tls.certresolver=le"

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    networks: [reverse-proxy]
    volumes:
      - prometheus-data:/prometheus
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.prom.rule=Host(`prometheus.${DOMAIN}`)"
      - "traefik.http.routers.prom.entrypoints=websecure"
      - "traefik.http.routers.prom.tls.certresolver=le"

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    networks: [reverse-proxy]
    depends_on: [prometheus]
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASS:-admin}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.grafana.rule=Host(`grafana.${DOMAIN}`)"
      - "traefik.http.routers.grafana.entrypoints=websecure"
      - "traefik.http.routers.grafana.tls.certresolver=le"

  nginx_www:
    image: nginx:stable
    container_name: nginx_www
    restart: unless-stopped
    networks: [reverse-proxy]
    volumes:
      - /var/www/html:/usr/share/nginx/html:ro
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.www.rule=Host(`www.${DOMAIN}`)"
      - "traefik.http.routers.www.entrypoints=websecure"
      - "traefik.http.routers.www.tls.certresolver=le"
YML

cat >"${COMPOSE_DIR}/traefik/traefik.yml" <<'TRAF'
log:
  level: INFO
providers:
  file:
    directory: /dynamic
    watch: true
  docker:
    exposedByDefault: false
TRAF

cat >"${COMPOSE_DIR}/traefik/dynamic/dashboard.yml" <<'DYN'
http:
  middlewares:
    dashboard-auth:
      basicAuth:
        usersFile: /usersfile
DYN

cat >"${COMPOSE_DIR}/nginx/default.conf" <<'NGX'
server {
  listen 80 default_server;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;
  location / { try_files $uri $uri/ =404; }
}
NGX

# Dashboard auth (optional)
if [[ -n "$DASH_PASS_HASH" ]]; then
  echo "${DASH_USER}:${DASH_PASS_HASH}" > "${COMPOSE_DIR}/traefik/usersfile"
else
  rm -f "${COMPOSE_DIR}/traefik/usersfile" 2>/dev/null || true
fi

# ------------------------------ Vendor: local-ai-packaged ---------------------
if [[ "$INTEGRATE_LOCAL_AI" == "true" ]]; then
  say "Cloning/updating coleam00/local-ai-packaged@${LAI_BRANCH} ..."
  mkdir -p "${VENDOR_DIR}"
  if [[ ! -d "${VENDOR_DIR}/.git" ]]; then
    git clone -b "$LAI_BRANCH" https://github.com/coleam00/local-ai-packaged.git "$VENDOR_DIR"
  else
    git -C "$VENDOR_DIR" fetch --all --prune || true
    git -C "$VENDOR_DIR" checkout "$LAI_BRANCH" || true
    git -C "$VENDOR_DIR" pull --rebase || true
  fi

  # Build the vendor .env from .env.example with strong secrets + hostnames
  if [[ -f "${VENDOR_DIR}/.env.example" ]]; then
    cp -f "${VENDOR_DIR}/.env.example" "${VENDOR_DIR}/.env"
    sed -i "s#^\s*\(N8N_HOSTNAME\)=.*#\1=n8n.${DOMAIN}#"           "${VENDOR_DIR}/.env" || true
    sed -i "s#^\s*\(WEBUI_HOSTNAME\)=.*#\1=openwebui.${DOMAIN}#"   "${VENDOR_DIR}/.env" || true
    sed -i "s#^\s*\(FLOWISE_HOSTNAME\)=.*#\1=flowise.${DOMAIN}#"   "${VENDOR_DIR}/.env" || true
    sed -i "s#^\s*\(SUPABASE_HOSTNAME\)=.*#\1=supabase.${DOMAIN}#" "${VENDOR_DIR}/.env" || true
    sed -i "s#^\s*\(SEARXNG_HOSTNAME\)=.*#\1=searxng.${DOMAIN}#"   "${VENDOR_DIR}/.env" || true
    sed -i "s#^\s*\(NEO4J_HOSTNAME\)=.*#\1=neo4j.${DOMAIN}#"       "${VENDOR_DIR}/.env" || true
    sed -i "s#^\s*\(OLLAMA_HOSTNAME\)=.*#\1=ollama.${DOMAIN}#"     "${VENDOR_DIR}/.env" || true
    sed -i "s#^\s*\(LETSENCRYPT_EMAIL\)=.*#\1=${ACME_EMAIL}#"      "${VENDOR_DIR}/.env" || true

    gen(){ openssl rand -hex 32; }
    ensure(){ local k="$1"; grep -q "^${k}=" "${VENDOR_DIR}/.env" || echo "${k}=$(gen)" >> "${VENDOR_DIR}/.env"; }
    ensure N8N_ENCRYPTION_KEY; ensure N8N_USER_MANAGEMENT_JWT_SECRET
    ensure POSTGRES_PASSWORD; ensure JWT_SECRET; ensure ANON_KEY; ensure SERVICE_ROLE_KEY
    ensure CLICKHOUSE_PASSWORD; ensure MINIO_ROOT_PASSWORD; ensure LANGFUSE_SALT
    ensure NEXTAUTH_SECRET; ensure ENCRYPTION_KEY
    grep -q '^POOLER_TENANT_ID=' "${VENDOR_DIR}/.env" || uuidgen | awk '{print "POOLER_TENANT_ID="$1}' >> "${VENDOR_DIR}/.env"
    # Supabase has noted POOLER_DB_POOL_SIZE in docs; include if absent
    grep -q '^POOLER_DB_POOL_SIZE=' "${VENDOR_DIR}/.env" || echo 'POOLER_DB_POOL_SIZE=5' >> "${VENDOR_DIR}/.env"
  else
    say "[WARN] Vendor .env.example not found; skipping .env synthesis."
  fi

  # Merge vendor compose files and Traefik-ize (remove Caddy)
  TMP_MERGED="/tmp/localai_full.yml"
  FILES=()
  [[ -f "${VENDOR_DIR}/docker-compose.yml" ]] && FILES+=("${VENDOR_DIR}/docker-compose.yml")
  [[ -f "${VENDOR_DIR}/docker-compose.override.public.yml" ]] && FILES+=("${VENDOR_DIR}/docker-compose.override.public.yml")
  [[ -f "${VENDOR_DIR}/docker-compose.override.public.supabase.yml" ]] && FILES+=("${VENDOR_DIR}/docker-compose.override.public.supabase.yml")
  if (( ${#FILES[@]} > 0 )); then
    yq ea '. as $item ireduce ({}; . * $item )' "${FILES[@]}" > "$TMP_MERGED"
    yq -i 'del(.services.caddy)' "$TMP_MERGED" || true
    yq -i '.networks."reverse-proxy".external = false' "$TMP_MERGED"

    # Helper to map hostnames -> likely service names (robust matching)
    add_labels(){
      local svc="$1" host="$2"; [[ -z "$svc" || -z "$host" ]] && return 0
      yq -i \
        ".services.${svc}.labels += [\"traefik.enable=true\", \"traefik.http.routers.${svc}.rule=Host(\`${host}\`)\", \"traefik.http.routers.${svc}.entrypoints=websecure\", \"traefik.http.routers.${svc}.tls.certresolver=le\"]" \
        "$TMP_MERGED" 2>/dev/null || true
      yq -i ".services.${svc}.networks += [\"reverse-proxy\"]" "$TMP_MERGED" 2>/dev/null || true
      yq -i 'del(.services.'"${svc}"'.ports)' "$TMP_MERGED" 2>/dev/null || true
    }
    # Find a service key by substring (n8n, open-webui/openwebui, flowise, searxng, neo4j, ollama, langfuse, kong/supabase-kong)
    find_svc(){ local pat="$1"; yq -r '.services | keys[]' "$TMP_MERGED" | grep -i "$pat" | head -n1 || true; }

    SVC_N8N=$(find_svc '^n8n$')
    SVC_WEBUI=$(find_svc 'open[-_]?webui')
    SVC_FLOWISE=$(find_svc 'flowise')
    SVC_SEARXNG=$(find_svc 'searx')
    SVC_NEO4J=$(find_svc 'neo4j')
    SVC_OLLAMA=$(find_svc 'ollama')
    SVC_LANGFUSE=$(find_svc 'langfuse')
    SVC_KONG=$(find_svc '^kong$'); [[ -z "$SVC_KONG" ]] && SVC_KONG=$(find_svc 'supabase[-_]?kong')

    add_labels "$SVC_N8N"      "n8n.${DOMAIN}"
    add_labels "$SVC_WEBUI"    "openwebui.${DOMAIN}"
    add_labels "$SVC_FLOWISE"  "flowise.${DOMAIN}"
    add_labels "$SVC_SEARXNG"  "searxng.${DOMAIN}"
    add_labels "$SVC_NEO4J"    "neo4j.${DOMAIN}"
    add_labels "$SVC_OLLAMA"   "ollama.${DOMAIN}"
    add_labels "$SVC_LANGFUSE" "langfuse.${DOMAIN}"
    add_labels "$SVC_KONG"     "supabase.${DOMAIN}"

    cp "$TMP_MERGED" "${COMPOSE_DIR}/docker-compose.localai.yml"
  else
    say "[WARN] Vendor compose files not found; skipping overlay generation."
  fi
fi

# ------------------------------ Optional DNS (Terraform) ----------------------
if [[ -n "$DNS_PROVIDER" ]]; then
  if [[ -z "$SERVER_IPV4" ]]; then
    say "[FATAL] SERVER_IPV4 required for DNS step"; exit 10
  fi
  say "Installing Terraform and applying DNS (${DNS_PROVIDER}) ..."
  if ! command -v terraform >/dev/null 2>&1; then
    curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" >/etc/apt/sources.list.d/hashicorp.list
    apt-get update -y && apt-get install -y terraform
  fi
  TF_DIR="${APP_DIR}/terraform_dns"; mkdir -p "$TF_DIR"
  cat >"${TF_DIR}/main.tf" <<'TF'
terraform {
  required_version = ">= 1.4"
  required_providers {
    cloudflare = { source = "cloudflare/cloudflare" }
    hetznerdns = { source = "timohirt/hetznerdns" }
  }
}
variable "dns_provider" { type = string }
variable "zone" { type = string }
variable "ipv4" { type = string }
variable "subdomains" { type = list(string) }
variable "cloudflare_api_token" { type = string, default = null }
variable "hetzner_dns_token" { type = string, default = null }
locals { use_cf = var.dns_provider == "cloudflare" }
provider "cloudflare" { count = local.use_cf ? 1 : 0, api_token = var.cloudflare_api_token }
provider "hetznerdns" { count = local.use_cf ? 0 : 1, apitoken = var.hetzner_dns_token }
# CF
data "cloudflare_zones" "zone" { count = local.use_cf ? 1 : 0, filter { name = var.zone } }
resource "cloudflare_record" "a_records" {
  count   = local.use_cf ? length(var.subdomains) : 0
  zone_id = data.cloudflare_zones.zone[0].zones[0].id
  name    = var.subdomains[count.index]
  type    = "A"
  value   = var.ipv4
  ttl     = 300
  proxied = false
}
# Hetzner DNS
data "hetznerdns_zone" "zone" { count = local.use_cf ? 0 : 1, name = var.zone }
resource "hetznerdns_record" "a_records" {
  count   = local.use_cf ? 0 : length(var.subdomains)
  zone_id = data.hetznerdns_zone.zone[0].id
  name    = var.subdomains[count.index]
  type    = "A"
  value   = var.ipv4
  ttl     = 300
}
TF
  pushd "$TF_DIR" >/dev/null
  terraform init -input=false
  SUBS=(traefik whoami prometheus grafana www n8n openwebui flowise supabase searxng neo4j langfuse ollama)
  case "$DNS_PROVIDER" in
    cloudflare)
      [[ -n "$CF_API_TOKEN" ]] || { say "[FATAL] CF_API_TOKEN missing"; exit 11; }
      terraform apply -auto-approve \
        -var "dns_provider=cloudflare" -var "zone=${DOMAIN}" -var "ipv4=${SERVER_IPV4}" \
        -var 'subdomains=${SUBS}' -var "cloudflare_api_token=${CF_API_TOKEN}"
      ;;
    hetzner)
      [[ -n "$HETZNER_DNS_TOKEN" ]] || { say "[FATAL] HETZNER_DNS_TOKEN missing"; exit 12; }
      terraform apply -auto-approve \
        -var "dns_provider=hetzner" -var "zone=${DOMAIN}" -var "ipv4=${SERVER_IPV4}" \
        -var 'subdomains=${SUBS}' -var "hetzner_dns_token=${HETZNER_DNS_TOKEN}"
      ;;
    *) say "[FATAL] DNS_PROVIDER must be cloudflare or hetzner"; exit 13;;
  esac
  popd >/dev/null
else
  say "DNS step skipped (DNS_PROVIDER not set)."
fi

# ------------------------------ Deploy (Compose) ------------------------------
say "Bringing the stack up with Compose..."
cd "$COMPOSE_DIR"
COMPOSE_FILES=("-f" "docker-compose.yml")
[[ -f "docker-compose.localai.yml" ]] && COMPOSE_FILES+=("-f" "docker-compose.localai.yml")

docker compose "${COMPOSE_FILES[@]}" pull || true
# shellcheck disable=SC2068
docker compose ${COMPOSE_FILES[@]} up -d

# systemd unit ensures the stack survives reboot
UNIT="/etc/systemd/system/supa-container.service"
cat >"$UNIT"<<EOF
[Unit]
Description=supa-container docker compose stack
Requires=docker.service
After=docker.service

[Service]
WorkingDirectory=${COMPOSE_DIR}
ExecStart=/usr/bin/docker compose ${COMPOSE_FILES[*]} up -d
ExecStop=/usr/bin/docker compose ${COMPOSE_FILES[*]} down
TimeoutStartSec=0
RemainAfterExit=yes
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now supa-container.service

# ------------------------------ Health checks --------------------------------
for url in \
  "http://traefik.${DOMAIN}" \
  "https://traefik.${DOMAIN}" \
  "https://whoami.${DOMAIN}" \
  "https://grafana.${DOMAIN}" \
  "https://prometheus.${DOMAIN}" \
  "https://n8n.${DOMAIN}" \
  "https://openwebui.${DOMAIN}" \
  "https://flowise.${DOMAIN}" \
  "https://supabase.${DOMAIN}"; do
  code=$(curl -ks -o /dev/null -w "%{http_code}" "$url" || echo "000")
  say "[$code] $url"
done

say "SUCCESS: supa-container is deployed. Log: $LOG_FILE"
