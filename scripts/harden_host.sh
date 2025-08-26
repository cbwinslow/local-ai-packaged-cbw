#!/usr/bin/env bash
set -Eeuo pipefail
log(){ printf "[%s] %s\n" "$(date +%F\ %T)" "$*"; }
die(){ log "ERROR: $*"; exit 1; }
[[ $EUID -eq 0 ]] || die "Run as root"
apt-get update -y
apt-get install -y ufw fail2ban
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%s)
sed -i "s/^#\?PasswordAuthentication .*/PasswordAuthentication no/" /etc/ssh/sshd_config
sed -i "s/^#\?PermitRootLogin .*/PermitRootLogin no/" /etc/ssh/sshd_config
systemctl restart ssh || systemctl restart sshd || true
log "Host hardening complete (UFW, fail2ban, SSH)."
