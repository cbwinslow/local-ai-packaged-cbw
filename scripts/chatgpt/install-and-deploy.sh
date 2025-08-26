#!/usr/bin/env bash
#===============================================================================
# Script Name   : install-and-deploy.sh
# Author        : CBW (Blaine Winslow) & ChatGPT
# Date          : 2025-08-11
# Summary       : One-command setup for supa-container on a Hetzner dedicated box.
#                 Idempotent, SSH-safe (won't lock you out), validates along the way.
# Inputs        : ENV (override as needed)
#   DOMAIN=opendiscourse.net
#   ACME_EMAIL=admin@opendiscourse.net
#   CREATE_USER=true|false       (default true)
#   CBW_USER=cbwinslow
#   CBW_PUBKEY="ssh-ed25519 AAAA...your key..."
#   SSH_PORT=22
#   DNS_PROVIDER=cloudflare|hetzner (optional; if unset, DNS step is skipped)
#   CF_API_TOKEN=...             (for cloudflare)
#   HETZNER_DNS_TOKEN=...        (for hetzner DNS)
#   SERVER_IPV4=YOUR.SERVER.IP   (required if running DNS step)
#   DASH_USER=admin
#   DASH_PASS_HASH='$2y$05$...'  (use scripts/supa-container-htpasswd.sh to generate)
# Outputs       : /tmp/SC-install.log
# Return        : 0 on success; non-zero on failure
#===============================================================================
set -euo pipefail
LOG_FILE="/tmp/SC-install.log"
exec > >(tee -a "$LOG_FILE") 2>&1
trap 'echo "[ERROR] Line $LINENO failed. See $LOG_FILE"; exit 1' ERR

# --- Defaults
DOMAIN="${DOMAIN:-opendiscourse.net}"
ACME_EMAIL="${ACME_EMAIL:-admin@${DOMAIN}}"
CREATE_USER="${CREATE_USER:-true}"
CBW_USER="${CBW_USER:-cbwinslow}"
CBW_PUBKEY="${CBW_PUBKEY:-}"
SSH_PORT="${SSH_PORT:-22}"
DNS_PROVIDER="${DNS_PROVIDER:-}" # empty => skip DNS
SERVER_IPV4="${SERVER_IPV4:-}"
DASH_USER="${DASH_USER:-admin}"
DASH_PASS_HASH="${DASH_PASS_HASH:-}"

# --- 0) Sanity
command -v sudo >/dev/null || { echo "[FATAL] sudo required"; exit 2; }
command -v git >/dev/null || { echo "[INFO] installing git"; sudo apt-get update -y && sudo apt-get install -y git; }

# --- 1) Bootstrap (safe, idempotent)
sudo bash ./scripts/supa-container-bootstrap.sh \
  CREATE_USER="$CREATE_USER" CBW_USER="$CBW_USER" CBW_PUBKEY="$CBW_PUBKEY" SSH_PORT="$SSH_PORT"

# --- 2) (Optional) DNS via Terraform
if [[ -n "$DNS_PROVIDER" ]]; then
  if [[ -z "$SERVER_IPV4" ]]; then
    echo "[FATAL] SERVER_IPV4 is required for DNS step"; exit 3;
  fi
  pushd terraform/dns >/dev/null
  terraform init -input=false
  case "$DNS_PROVIDER" in
    cloudflare)
      [[ -n "${CF_API_TOKEN:-}" ]] || { echo "[FATAL] CF_API_TOKEN missing"; exit 4; }
      terraform apply -auto-approve \
        -var "dns_provider=cloudflare" \
        -var "zone=${DOMAIN}" \
        -var "ipv4=${SERVER_IPV4}" \
        -var "cloudflare_api_token=${CF_API_TOKEN}"
      ;;
    hetzner)
      [[ -n "${HETZNER_DNS_TOKEN:-}" ]] || { echo "[FATAL] HETZNER_DNS_TOKEN missing"; exit 5; }
      terraform apply -auto-approve \
        -var "dns_provider=hetzner" \
        -var "zone=${DOMAIN}" \
        -var "ipv4=${SERVER_IPV4}" \
        -var "hetzner_dns_token=${HETZNER_DNS_TOKEN}"
      ;;
    *)
      echo "[FATAL] DNS_PROVIDER must be 'cloudflare' or 'hetzner'"; exit 6;;
  esac
  popd >/dev/null
else
  echo "[INFO] DNS step skipped (DNS_PROVIDER not set)."
fi

# --- 3) Deploy stack (Traefik + whoami + Grafana + Prometheus)
sudo DOMAIN="$DOMAIN" EMAIL="$ACME_EMAIL" DASH_USER="$DASH_USER" DASH_PASS_HASH="$DASH_PASS_HASH" \
  ./scripts/supa-container-deploy.sh

# --- 4) Post checks
echo "[STEP] Running quick checks..."
set +e
for url in \
  "https://traefik.${DOMAIN}" \
  "https://whoami.${DOMAIN}" \
  "https://grafana.${DOMAIN}" \
  "https://prometheus.${DOMAIN}"; do
  code=$(curl -ks -o /dev/null -w "%{http_code}" "$url")
  echo "  [$code] $url"
done
set -e
echo "[SUCCESS] Install & deploy complete. Log: $LOG_FILE"
