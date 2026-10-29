#!/usr/bin/env bash
# Tests de parcours utilisateur dans un vrai navigateur.
# Cible l environnement de test, jamais la beta.
set -euo pipefail

APP_URL="${1:-http://127.0.0.1:18001}"
if [[ $# -gt 0 ]]; then
  shift
fi
PLAYWRIGHT_VERSION="1.55.0"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

echo "[e2e] Cible: $APP_URL"
# node_modules reste dans le depot (ignore par Git): l installation n a lieu
# qu au premier lancement.
rm -rf test-results/.playwright-artifacts-*

if [[ ! -d node_modules/@playwright/test ]]; then
  docker run --rm --network host \
    -v "$repo_root:/w" -w /w \
    "mcr.microsoft.com/playwright:v${PLAYWRIGHT_VERSION}-noble" \
    npm install --no-save --no-audit --no-fund "@playwright/test@${PLAYWRIGHT_VERSION}" >/dev/null 2>&1
fi

docker run --rm --network host \
  -v "$repo_root:/w" -w /w \
  -e BEEVARIUM_APP_URL="$APP_URL" \
  -e BEEVARIUM_SIMULATION="${BEEVARIUM_SIMULATION:-}" \
  -e CI=1 \
  "mcr.microsoft.com/playwright:v${PLAYWRIGHT_VERSION}-noble" \
  npx playwright test --config tests/e2e/playwright.config.js "$@"
