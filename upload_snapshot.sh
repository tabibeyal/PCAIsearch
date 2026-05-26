#!/bin/bash
# Uploads /tmp/pali_canon.snapshot to the live Qdrant collection.
# Credentials are loaded from .env — never hardcode them here.
set -euo pipefail
set -a
# shellcheck source=.env
source "$(dirname "$0")/.env"
set +a

[ -f /tmp/pali_canon.snapshot ] || { echo "snapshot not found at /tmp/pali_canon.snapshot"; exit 1; }

curl -f -X POST "${QDRANT_URL}/collections/pali_canon/snapshots/upload?priority=snapshot" \
  -H "api-key: ${QDRANT_API_KEY}" \
  -H "Content-Type: multipart/form-data" \
  -F "snapshot=@/tmp/pali_canon.snapshot"
