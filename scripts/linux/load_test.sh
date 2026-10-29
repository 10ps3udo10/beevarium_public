#!/usr/bin/env bash
# Tir de charge progressif sur l environnement de test.
#
# La beta et l environnement de test partagent le meme VPS: viser la beta
# ferait tomber les deux. Le script et le scenario k6 le refusent tous les deux.
set -euo pipefail

API_URL="${1:-http://127.0.0.1:18001}"
FICHIER_COMPTES="${2:-artifacts/charge/comptes.json}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ "$API_URL" != *"127.0.0.1"* && "$API_URL" != *"localhost"* && "${AUTORISER_PRODUCTION:-0}" != "1" ]]; then
  echo "[charge] Refus de tirer sur $API_URL." >&2
  echo "[charge] Definir AUTORISER_PRODUCTION=1 si c est reellement voulu." >&2
  exit 2
fi

if [[ ! -f "$FICHIER_COMPTES" ]]; then
  echo "[charge] Comptes introuvables: $FICHIER_COMPTES" >&2
  echo "[charge] Generer d abord: python3 scripts/seed_realistic_data.py --sortie-json $FICHIER_COMPTES" >&2
  exit 1
fi

mkdir -p artifacts/charge
echo "[charge] Cible: $API_URL"
echo "[charge] Comptes: $(python3 -c "import json,sys;print(len(json.load(open('$FICHIER_COMPTES'))['comptes']))") compte(s)"

docker run --rm --network host \
  --user "$(id -u):$(id -g)" \
  -v "$repo_root:/w" -w /w \
  -e BEEVARIUM_API_URL="$API_URL" \
  -e BEEVARIUM_COMPTES="/w/$FICHIER_COMPTES" \
  -e AUTORISER_PRODUCTION="${AUTORISER_PRODUCTION:-0}" \
  -e PALIER_MAX="${PALIER_MAX:-20}" \
  grafana/k6:latest run \
  --summary-export artifacts/charge/resultat.json \
  tests/charge/parcours.js

echo "[charge] Rapport: artifacts/charge/resultat.json"
