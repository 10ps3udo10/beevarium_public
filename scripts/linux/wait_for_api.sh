#!/usr/bin/env bash
# Attend que /health reponde avant de lancer des tests.
set -euo pipefail

API_BASE_URL="http://localhost:8000"
TIMEOUT_SECONDS=60

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-base-url)
      API_BASE_URL="$2"
      shift 2
      ;;
    --timeout-seconds)
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

API_BASE_URL="${API_BASE_URL%/}"
DEADLINE=$((SECONDS + TIMEOUT_SECONDS))

echo "[wait_for_api] Checking ${API_BASE_URL}/health for ${TIMEOUT_SECONDS}s..."
while (( SECONDS < DEADLINE )); do
  if curl -fsS "${API_BASE_URL}/health" >/dev/null 2>&1; then
    echo "[wait_for_api] API ready."
    exit 0
  fi
  sleep 1
done

echo "[wait_for_api] API unavailable after ${TIMEOUT_SECONDS}s" >&2
exit 1
