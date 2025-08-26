# scripts/supa-container-htpasswd.sh
#!/usr/bin/env bash
set -euo pipefail
if ! command -v htpasswd >/dev/null 2>&1; then
  apt-get update -y && apt-get install -y apache2-utils
fi
USER="${1:-admin}"
PASS="${2:-$(openssl rand -base64 18)}"
HASH=$(htpasswd -nbB "$USER" "$PASS" | cut -d: -f2)
echo "User: $USER"
echo "Pass: $PASS"
echo "Hash: $HASH"
