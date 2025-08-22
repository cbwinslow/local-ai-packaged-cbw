#!/usr/bin/env bash
set -euo pipefail
# Storage PUT/GET smoke test using curl
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/.env" || true

if [[ -z "${SERVICE_ROLE_KEY:-}" || -z "${SUPABASE_HOSTNAME:-}" ]]; then
  echo "Require SERVICE_ROLE_KEY and SUPABASE_HOSTNAME in .env"
  exit 2
fi

BUCKET=test-smoke
KEY=test.txt
PAYLOAD="hello-from-smoke-test-$(date +%s)"

# Create bucket (idempotent via API) - may require admin; try PUT via storage API
UPLOAD_URL="https://${SUPABASE_HOSTNAME}/storage/v1/object/${BUCKET}/${KEY}"

echo "Uploading to $UPLOAD_URL"

resp=$(curl -s -o /dev/stderr -w "%{http_code}" -X PUT "$UPLOAD_URL" \
  -H "Authorization: Bearer ${SERVICE_ROLE_KEY}" \
  -H "Content-Type: text/plain" \
  --data "$PAYLOAD" ) || true

echo "Upload HTTP status: $resp"
if [[ "$resp" != "200" && "$resp" != "201" ]]; then
  echo "Upload failed (status $resp). Check storage configuration and SERVICE_ROLE_KEY."
  exit 1
fi

# Download
GET_URL="https://${SUPABASE_HOSTNAME}/storage/v1/object/public/${BUCKET}/${KEY}"
# Try public URL first
echo "Attempting public GET: $GET_URL"
body=$(curl -fsS "$GET_URL" || true)
if [[ "$body" == "$PAYLOAD" ]]; then
  echo "Storage smoke OK (public)"
  exit 0
fi

# Fallback: authenticated GET
body=$(curl -fsS -X GET "https://${SUPABASE_HOSTNAME}/storage/v1/object/${BUCKET}/${KEY}" -H "Authorization: Bearer ${SERVICE_ROLE_KEY}" || true)
if [[ "$body" == "$PAYLOAD" ]]; then
  echo "Storage smoke OK (authenticated)"
  exit 0
fi

echo "Storage smoke test failed: content mismatch or 404"
exit 1
