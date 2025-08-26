#!/usr/bin/env bash
#===============================================================================
# Script Name   : supa-container-bootstrap.sh
# Author        : CBW (Blaine Winslow) & ChatGPT
# Date          : 2025-08-10
# Summary       : Harden a fresh Ubuntu 24 server without locking out SSH.
#                 Installs Docker, UFW, fail2ban, core tools. Idempotent.
# Inputs        : ENV (optional)
#   CREATE_USER=true|false      # default: true
#   CBW_USER=cbwinslow          # name of primary sudo user
#   CBW_PUBKEY="ssh-ed25519 ..."# public key for the user
#   SSH_PORT=22                 # default: 22 (we keep 22 to avoid lockouts)
# Outputs       : /tmp/SC-bootstrap.log
#===============================================================================
set -euo pipefail
LOG_FILE="/tmp/SC-bootstrap.log"
exec > >(tee -a "$LOG_FILE") 2>&1
trap 'echo "[ERROR] Failed at line $LINENO. See $LOG_FILE"; exit 1' ERR

CREATE_USER="${CREATE_USER:-true}"
CBW_USER="${CBW_USER:-cbwinslow}"
CBW_PUBKEY="${CBW_PUBKEY:-}"
SSH_PORT="${SSH_PORT:-22}"

echo "[INFO] Bootstrap starting $(date -Is)"

# --- System prep
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release ufw fail2ban jq unzip git net-tools vim

# --- UFW: allow SSH *before* enabling, to avoid lockout (Hetzner tutorial best practice)
#          https://community.hetzner.com/tutorials/simple-firewall-management-with-ufw/
if ! command -v ufw >/dev/null; then
  echo "[FATAL] UFW missing"; exit 2
fi
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow "${SSH_PORT}"/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status verbose

# Quick local reachability test: ensure sshd is listening
if ! ss -ltnp | grep -q ":${SSH_PORT} "; then
  echo "[WARN] SSH port ${SSH_PORT} not listening yet; restarting ssh"
  systemctl restart ssh || systemctl restart sshd || true
fi

# --- SSH hardening: disable root + password auth, keep existing session safe
SSHD="/etc/ssh/sshd_config"
cp -an "$SSHD" "${SSHD}.bak.$(date +%s)"
sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' "$SSHD"
sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' "$SSHD"
grep -q "^Port ${SSH_PORT}$" "$SSHD" || echo "Port ${SSH_PORT}" >> "$SSHD"
systemctl reload ssh || systemctl reload sshd || true
# Hetzner SSH hardening refs. :contentReference[oaicite:4]{index=4}

# --- Create primary user
if [[ "${CREATE_USER}" == "true" ]]; then
  if ! id -u "$CBW_USER" >/dev/null 2>&1; then
    adduser --disabled-password --gecos "" "$CBW_USER"
    usermod -aG sudo "$CBW_USER"
    install -d -m 700 "/home/${CBW_USER}/.ssh"
    if [[ -n "$CBW_PUBKEY" ]]; then
      echo "$CBW_PUBKEY" > "/home/${CBW_USER}/.ssh/authorized_keys"
      chmod 600 "/home/${CBW_USER}/.ssh/authorized_keys"
    else
      echo "[WARN] No CBW_PUBKEY provided; add authorized_keys manually."
    fi
    chown -R "${CBW_USER}:${CBW_USER}" "/home/${CBW_USER}/.ssh"
  else
    echo "[INFO] User ${CBW_USER} already exists."
  fi
fi

# --- Fail2ban baseline
cat >/etc/fail2ban/jail.d/sshd.local <<EOF
[sshd]
enabled = true
port    = ${SSH_PORT}
backend = systemd
maxretry = 6
bantime = 1h
EOF
systemctl enable --now fail2ban || true

# --- Docker (official repo)
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
fi
usermod -aG docker "$CBW_USER" || true

# --- Validation
docker version || { echo "[FATAL] Docker not working"; exit 3; }
docker compose version || { echo "[FATAL] Compose plugin missing"; exit 3; }
echo "[OK] Bootstrap complete. Log: $LOG_FILE"
