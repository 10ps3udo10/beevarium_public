#!/usr/bin/env bash
# Revient a l'image precedente notee dans le dernier rapport de deploiement.
set -euo pipefail

ENV_FILE="${1:-.env.target}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ ! -f artifacts/deploy-report.json ]]; then
  echo "Missing artifacts/deploy-report.json" >&2
  exit 1
fi

previous_image="$(python3 - <<'PY'
import json
from pathlib import Path
obj = json.loads(Path('artifacts/deploy-report.json').read_text(encoding='utf-8'))
print(obj.get('previous_image',''))
PY
)"

if [[ -z "${previous_image// }" ]]; then
  echo "No previous image available for rollback" >&2
  exit 1
fi

echo "[deploy] Rollback to ${previous_image}"
API_IMAGE="$previous_image" docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" up -d api_target

echo "[deploy] Rollback completed"
