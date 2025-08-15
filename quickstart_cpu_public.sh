#!/usr/bin/env bash
set -euo pipefail
echo "== Local AI Package CPU Public Quickstart =="
if [ ! -f .env ]; then
  echo "No .env found. Generating one (you can edit later)." >&2
  python3 scripts/generate_env.py --base-domain "${BASE_DOMAIN:-localhost}" --email "${EMAIL:-admin@example.com}" > .env
fi
python3 start_services.py --profile cpu --environment public
echo "Portal (if domain configured): https://${PORTAL_HOSTNAME:-portal.localhost}" 
echo "Done. Use 'docker compose -p localai ps' to view services."
