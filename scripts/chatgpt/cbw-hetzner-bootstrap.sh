#!/usr/bin/env bash
#===============================================================================
# Script Name   : cbw-hetzner-bootstrap.sh
# Author        : CBW & ChatGPT
# Date          : 2025-08-10
# Summary       : One-shot bootstrap for a fresh Ubuntu 24 Hetzner dedicated server.
#                 Creates 'cbwinslow' user (optional), hardens SSH, installs Docker,
#                 UFW/fail2ban, basic tools, and validates everything.
# Inputs        : Environment variables (optional):
#                   CREATE_USER=true|false (default true)
#                   CBW_USER=cbwinslow
#                   CBW_PUBKEY="ssh-ed25519 AAAA... your key ..."
#                   SSH_PORT=22
# Outputs       : Log at /tmp/CBW-hetzner-bootstrap.log
# Parameters    : None
# Return        : 0 on success, non-zero on failure
# Modification Log:
#   2025-08-10  Initial version
#===============================================================================
set -euo pipefail

LOG_FILE="/tmp/CBW-hetzner-bootstrap.log"
exec > >(tee -a "$LOG_FILE") 2>&1
trap 'echo "[ERROR] Line $LINENO failed. See $LOG_FILE"; exit 1' ERR

CREATE_USER="${CREATE_USER:-true}"
CBW_USER="${CBW_USER:-cbwinslow}"
CBW_PUBKEY="${CBW_PUBKEY:-}"
SSH_PORT="${SSH_PORT:-22}"

echo "[INFO] Starting bootstrap at $(date -Is)"
if ! command -v lsb_release >/dev/null 2>&1; then
  apt-get update -y && apt-get install -y lsb-release
fi
DISTRO="$(lsb_release -si || echo Ubuntu)"
RELEASE="$(lsb_release -sr || echo 24.04)"
if [[ "$DISTRO" != "Ubuntu" ]]; then
  echo "[WARN] Tested on Ubuntu. You are on: $DISTRO $RELEASE"
fi

echo "[STEP] System update & essentials"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg ufw fail2ban jq unzip git net-tools vim

echo "[STEP] Configure UFW"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow "${SSH_PORT}"/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status verbose

echo "[STEP] SSH hardening"
SSHD="/etc/ssh/sshd_config"
cp -an "$SSHD" "${SSHD}.bak.$(date +%s)"
sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' "$SSHD"
sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' "$SSHD"
grep -q "^Port ${SSH_PORT}$" "$SSHD" || echo "Port ${SSH_PORT}" >> "$SSHD"
systemctl restart ssh || systemctl restart sshd

if [[ "$CREATE_USER" == "true" ]]; then
  echo "[STEP] Create user ${CBW_USER}"
  if ! id -u "$CBW_USER" >/dev/null 2>&1; then
    adduser --disabled-password --gecos "" "$CBW_USER"
    usermod -aG sudo "$CBW_USER"
    mkdir -p "/home/${CBW_USER}/.ssh"
    chmod 700 "/home/${CBW_USER}/.ssh"
    if [[ -n "$CBW_PUBKEY" ]]; then
      echo "$CBW_PUBKEY" > "/home/${CBW_USER}/.ssh/authorized_keys"
      chmod 600 "/home/${CBW_USER}/.ssh/authorized_keys"
      chown -R "${CBW_USER}:${CBW_USER}" "/home/${CBW_USER}/.ssh"
    else
      echo "[WARN] No CBW_PUBKEY provided. You must add keys manually."
    fi
  else
    echo "[INFO] User ${CBW_USER} already exists."
  fi
fi

echo "[STEP] Install Docker (official repo)"
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
fi

if [[ "$CREATE_USER" == "true" ]]; then
  usermod -aG docker "$CBW_USER" || true
fi

echo "[STEP] Fail2ban basic profile"
cat >/etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
port    = 22
logpath = %(sshd_log)s
backend = systemd
maxretry = 5
bantime = 1h
EOF
if [[ "$SSH_PORT" != "22" ]]; then
  sed -i "s/^port *= *22/port = ${SSH_PORT}/" /etc/fail2ban/jail.d/sshd.local
fi
systemctl enable --now fail2ban || true

echo "[CHECK] Docker & compose"
docker version || { echo "[FATAL] Docker not installed properly"; exit 2; }
docker compose version || { echo "[FATAL] Compose plugin missing"; exit 2; }

echo "[SUCCESS] Bootstrap complete. Log: $LOG_FILE"
