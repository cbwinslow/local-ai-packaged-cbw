#!/usr/bin/env bash
# Minimal SSH access setup script.
# Usage: sudo ./scripts/setup_ssh_access.sh --user ops --pubkey "/tmp/id_ed25519.pub" [--password 'FallbackPass123']

set -euo pipefail

USER_NAME="ops"
PUBKEY_FILE=""
FALLBACK_PASS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user) USER_NAME="$2"; shift 2;;
    --pubkey) PUBKEY_FILE="$2"; shift 2;;
    --password) FALLBACK_PASS="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 1;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

if [[ -z "$PUBKEY_FILE" || ! -f "$PUBKEY_FILE" ]]; then
  echo "Provide --pubkey path to an existing public key file." >&2
  exit 1
fi

if ! id "$USER_NAME" &>/dev/null; then
  adduser --disabled-password --gecos "" "$USER_NAME"
fi

HOME_DIR="/home/${USER_NAME}"
SSH_DIR="${HOME_DIR}/.ssh"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
cat "$PUBKEY_FILE" >> "${SSH_DIR}/authorized_keys"
sort -u "${SSH_DIR}/authorized_keys" -o "${SSH_DIR}/authorized_keys"
chmod 600 "${SSH_DIR}/authorized_keys"
chown -R "${USER_NAME}:${USER_NAME}" "$SSH_DIR"

# Add to sudo group (different distros)
if getent group sudo >/dev/null; then
  usermod -aG sudo "$USER_NAME"
elif getent group wheel >/dev/null; then
  usermod -aG wheel "$USER_NAME"
fi

if [[ -n "$FALLBACK_PASS" ]]; then
  echo "${USER_NAME}:${FALLBACK_PASS}" | chpasswd
fi

echo "\nUser: $USER_NAME" >&2
echo "Home: $HOME_DIR" >&2
echo "Key appended from: $PUBKEY_FILE" >&2
if [[ -n "$FALLBACK_PASS" ]]; then
  echo "Fallback password set (store it securely)." >&2
else
  echo "No fallback password set." >&2
fi

echo "Test in a new terminal: ssh ${USER_NAME}@<server-ip>" >&2
