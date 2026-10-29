#!/usr/bin/env bash
# Simulation d'usage par un apiculteur professionnel (tests/e2e/simulation-apiculteur.spec.js).
# Cree des donnees : cibler le local ou app-dev, jamais la beta.
# Sortie : artifacts/simulation/journal.md et captures 1440/390 px.
set -euo pipefail

APP_URL="${1:-http://localhost:8000}"
case "$APP_URL" in
  *beta.beevarium.fr*) echo "[simulation] Refus : la beta n'est jamais une cible de simulation." >&2; exit 1 ;;
esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"
rm -rf artifacts/simulation
BEEVARIUM_SIMULATION=1 bash scripts/linux/e2e_test.sh "$APP_URL" --grep "@simulation"
