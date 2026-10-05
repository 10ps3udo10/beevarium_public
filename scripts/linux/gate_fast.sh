#!/usr/bin/env bash
# Gate de validation : assets client, smoke strict, tests d'integration et
# parcours navigateur (@critical, ou complets avec --full-integration).
set -euo pipefail

FULL_INTEGRATION=0
API_BASE_URL="http://localhost:8000"
E2E_MODE="critical"

run_pytest() {
  local repo_root
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

  if [[ -x "$repo_root/backend/.venv/bin/python" ]] && "$repo_root/backend/.venv/bin/python" -c "import pytest" >/dev/null 2>&1; then
    "$repo_root/backend/.venv/bin/python" -m pytest "$@"
    return
  fi

  if python3 -c "import pytest" >/dev/null 2>&1; then
    python3 -m pytest "$@"
    return
  fi

  if command -v python >/dev/null 2>&1; then
    python -c "import pytest" >/dev/null 2>&1 && python -m pytest "$@" && return
  fi

  if command -v /c/Windows/py.exe >/dev/null 2>&1; then
    /c/Windows/py.exe -3.10 -m pytest "$@"
    return
  fi

  # Fallback useful on Windows+Git Bash where pytest can be installed in py launcher env.
  if command -v py >/dev/null 2>&1; then
    py -3.10 -m pytest "$@"
    return
  fi

  if command -v docker >/dev/null 2>&1; then
    docker run --rm --network host -v "$repo_root:/w" -w /w \
      -e BEEVARIUM_API_URL="$API_BASE_URL" \
      python:3.11-slim sh -c "pip install -q -r backend/requirements-dev.txt && python -m pytest \"\$@\"" sh "$@"
    return
  fi

  echo "pytest introuvable et docker indisponible." >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full-integration)
      FULL_INTEGRATION=1
      E2E_MODE="full"
      shift
      ;;
    --e2e-mode)
      E2E_MODE="$2"
      shift 2
      ;;
    --api-base-url)
      API_BASE_URL="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

echo "[gate] Step 1/5 - Client assets"
scripts/linux/check_client_assets.sh

echo "[gate] Step 2/5 - Strict smoke"
scripts/linux/smoke_api.sh --api-base-url "$API_BASE_URL" --strict-revocation --output-json-path artifacts/smoke-result.json

echo "[gate] Step 3/5 - Validate smoke JSON"
scripts/linux/validate_smoke_json.sh artifacts/smoke-result.json

echo "[gate] Step 4/5 - Tests"
if [[ "$FULL_INTEGRATION" -eq 1 ]]; then
  run_pytest backend/tests/integration -q
else
  run_pytest backend/tests/integration -q -k "auth or rucher or ia or visites_synthese"
fi

case "$E2E_MODE" in
  full)
  echo "[gate] Step 5/5 - Parcours navigateur"
  scripts/linux/e2e_test.sh "$API_BASE_URL"
    ;;
  critical)
    echo "[gate] Step 5/5 - Parcours navigateur critiques"
    scripts/linux/e2e_test.sh "$API_BASE_URL" --grep "@critical"
    ;;
  skip)
    echo "[gate] Step 5/5 - Parcours navigateur ignores"
    ;;
  *)
    echo "Mode E2E invalide: $E2E_MODE (attendu: critical, full ou skip)" >&2
    exit 1
    ;;
esac

echo "[gate] OK"
