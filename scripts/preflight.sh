#!/usr/bin/env bash
# scripts/preflight.sh
# Pre-flight environment check.
# Run before EVERY `docker compose up` — including up --build, up -d, and single-service restarts.
# Exits non-zero with the name of the first missing variable if any are absent.
#
# Usage: ./scripts/preflight.sh
# Returns: 0 if all checks pass, 1 if any check fails

set -euo pipefail

REQUIRED_VARS=(
  "DATABASE_URL"
  "REDIS_URL"
  "SECRET_KEY"
  "DARAJA_CONSUMER_KEY"
  "DARAJA_CONSUMER_SECRET"
)

echo "==> joat_stores pre-flight check"

FAILED=0

for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "MISSING: $var is not set"
    FAILED=1
  else
    echo "OK $var"
  fi
done

if [[ $FAILED -eq 1 ]]; then
  echo ""
  echo "Pre-flight FAILED. Set all missing environment variables and retry."
  exit 1
fi

echo ""
echo "Pre-flight passed. All required environment variables are set."
exit 0
