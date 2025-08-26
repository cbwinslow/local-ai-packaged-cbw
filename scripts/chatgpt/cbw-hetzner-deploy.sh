#!/usr/bin/env bash
#===============================================================================
# Script Name   : cbw-hetzner-deploy.sh
# Author        : CBW & ChatGPT
# Date          : 2025-08-10
# Summary       : Wrapper to deploy the hetzner_app stack idempotently.
#                 - Clones/updates repo
#                 - Validates .env/config
#                 - Runs repo's deploy.sh
#                 - Writes systemd unit for docker compose
#                 - Performs health checks on key endpoints
# Inputs        : ENV:
#                   REPO_URL="https://github.com/cbwinslow/hetzner_app.git"
#                   BRANCH="master"
#                   APP_DIR="/opt/hetzner_app"
#                   COMPOSE_DIR="/opt/hetzner_app"
#                   HEALTH_URLS="https://your-domain.com;/api/health;https://api.your-domain.com/docs"
# Outputs       : /tmp/CBW-hetzner-deploy.log
# Parameters    : None
# Modification Log:
#   2025-08-10  Initial version
#===============================================================================
set -euo pipefail
LOG_FILE="/tmp/CBW-hetzner-deploy.log"
exec > >(tee -a "$LOG_FILE") 2>&1
trap 'echo "[ERROR] Line $LINENO failed. See $LOG_FILE"; exit 1' ERR

REPO_URL="${REPO_URL:-https://github.com/cbwinslow/hetzner_app.git}"
BRANCH="${BRANCH:-master}"
APP_DIR="${APP_DIR:-/opt/hetzner_app}"
COMPOSE_DIR="${COMPOSE_DIR:-$APP_DIR}"
HEALTH_URLS="${HEALTH_URLS:-}"

echo "[INFO] Deploy start: $(date -Is)"
command -v docker >/dev/null || { echo "[FATAL] docker missing"; exit 2; }
docker compose version >/dev/null || { echo "[FATAL] docker compose plugin missing"; exit 2; }

echo "[STEP] Ensure target dir $APP_DIR"
mkdir -p "$APP_DIR"
if [[ -d "$APP_DIR/.git" ]]; then
  echo "[INFO] Repo exists; pull latest"
  git -C "$APP_DIR" fetch origin "$BRANCH" --depth 1
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  echo "[INFO] Cloning $REPO_URL"
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$APP_DIR"
fi

echo "[STEP] Clean editor backup files"
rm -f "$APP_DIR"/#*# "$APP_DIR"/.#* 2>/dev/null || true

echo "[STEP] Validate config & env"
[[ -f "$APP_DIR/.env" ]] || { 
  if [[ -f "$APP_DIR/.env.example" ]]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "[WARN] .env was missing; created from example. Edit and re-run."
  else
    echo "[FATAL] .env missing and no example provided."
    exit 3
  fi
}
if [[ -f "$APP_DIR/config.sh" ]]; then
  # shellcheck disable=SC1091
  source "$APP_DIR/config.sh" || { echo "[WARN] Could not source config.sh"; }
fi

echo "[STEP] Run repo deploy.sh if present"
if [[ -x "$APP_DIR/deploy.sh" ]]; then
  (cd "$APP_DIR" && sudo bash ./deploy.sh)
else
  echo "[WARN] deploy.sh not executable or missing. Skipping."
fi

echo "[STEP] Compose up (detached)"
cd "$COMPOSE_DIR"
if [[ -f docker-compose.yml || -f compose.yml || -f docker-compose.yaml ]]; then
  docker compose up -d
else
  echo "[FATAL] No compose file found in $COMPOSE_DIR"
  exit 4
fi

echo "[STEP] Create systemd unit for the stack"
UNIT="/etc/systemd/system/hetzner_app.service"
cat | sudo tee "$UNIT" >/dev/null <<EOF
[Unit]
Description=hetzner_app docker compose stack
Requires=docker.service
After=docker.service

[Service]
WorkingDirectory=$COMPOSE_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
RemainAfterExit=yes
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now hetzner_app.service

echo "[STEP] Basic health checks"
IFS=';' read -ra URLS <<< "$HEALTH_URLS"
for u in "${URLS[@]}"; do
  [[ -z "$u" ]] && continue
  echo " - Checking $u"
  code=$(curl -ks -o /dev/null -w "%{http_code}" "$u" || echo "000")
  if [[ "$code" =~ ^2|3 ]]; then
    echo "   [OK] $u -> HTTP $code"
  else
    echo "   [WARN] $u -> HTTP $code"
  fi
done

echo "[SUCCESS] Deploy complete. Log: $LOG_FILE"
