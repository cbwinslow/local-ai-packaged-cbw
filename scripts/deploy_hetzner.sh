#!/usr/bin/env bash
set -euo pipefail

# Deploy the stack onto a fresh Hetzner Ubuntu/Debian server.
# Usage: ./scripts/deploy_hetzner.sh <domain> [git_repo_url] [branch]
# Expects you already added your SSH key to the server and pointed DNS (A + wildcard if desired).

DOMAIN=${1:-opendiscourse.net}
REPO=${2:-https://github.com/coleam00/local-ai-packaged.git}
BRANCH=${3:-stable}
APP_DIR=/opt/local-ai-packaged

log() { echo -e "[deploy] $*"; }

require_root() { if [[ $EUID -ne 0 ]]; then echo "Run as root (sudo)" >&2; exit 1; fi; }

install_deps() {
  log "Updating apt & installing dependencies"
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg git ufw
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") $(. /etc/os-release; echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
}

clone_repo() {
  if [[ -d $APP_DIR/.git ]]; then
    log "Repo exists, pulling latest"
    git -C "$APP_DIR" fetch --all
    git -C "$APP_DIR" checkout "$BRANCH"
    git -C "$APP_DIR" pull --ff-only
  # Ensure submodules are initialized and updated (so supabase init scripts are present)
  git -C "$APP_DIR" submodule update --init --recursive || true
  else
    log "Cloning repo"
    git clone "$REPO" -b "$BRANCH" "$APP_DIR"
  # Initialize submodules so repo contains all nested content
    # Ensure submodules are initialized and updated (so supabase init scripts are present)
    if git -C "$APP_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      git -C "$APP_DIR" submodule update --init --recursive || true
    fi
  else
    log "Cloning repo"
    git clone "$REPO" -b "$BRANCH" "$APP_DIR"
    # Initialize submodules so repo contains all nested content
    if git -C "$APP_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      git -C "$APP_DIR" submodule update --init --recursive || true
    fi
  fi
}

configure_env() {
  cd "$APP_DIR"
  if [[ ! -f .env ]]; then
    log "Generating .env from production example"
    cp .env.production.example .env
    sed -i "s/opendiscourse.net/$DOMAIN/g" .env
    # Attempt secret randomization
    python3 scripts/gen_all_in_one_env.py || true
  # Secure the generated .env
  chmod 600 .env || true
  log "Secured .env with chmod 600"
    log "Remember to set CLOUDFLARE_API_TOKEN inside .env before enabling Traefik with DNS challenge."
  fi
}

create_systemd_unit() {
  cat >/etc/systemd/system/local-ai-packaged.service <<'UNIT'
[Unit]
Description=Local AI Packaged Stack
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=notify
WorkingDirectory=/opt/local-ai-packaged
Environment=COMPOSE_FILE=docker-compose.all-in-one.yml:docker-compose.all-in-one.traefik.yml
ExecStart=/usr/bin/docker compose up -d --remove-orphans
ExecStop=/usr/bin/docker compose down
Restart=on-failure
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  systemctl enable --now local-ai-packaged.service
}

configure_firewall() {
  if command -v ufw >/dev/null 2>&1; then
    log "Configuring UFW (allow SSH, HTTP, HTTPS)"
    ufw allow 22/tcp || true
    ufw allow 80/tcp || true
    ufw allow 443/tcp || true
    yes | ufw enable || true
  fi
}

main() {
  require_root
  install_deps
  clone_repo
  configure_env
  configure_firewall
  create_systemd_unit
  log "Deployment complete. Check 'docker ps' and journalctl -u local-ai-packaged -f"
}

main "$@"
