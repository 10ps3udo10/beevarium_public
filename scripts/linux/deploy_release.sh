#!/usr/bin/env bash
# Deploie une image versionnee sur la stack cible et ecrit le rapport de deploiement
# (image precedente conservee pour le rollback).
set -euo pipefail

TAG="${1:-v1.0.1-rc1}"
ENV_FILE="${2:-.env.target}"
IMAGE="beevarium-api:${TAG}"
ARTIFACTS_DIR="${ARTIFACTS_DIR:-artifacts}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

stack_name="$(grep -E '^STACK_NAME=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"
api_container="${stack_name:-beevarium}_api_target"

prev_image=""
if docker inspect "$api_container" >/dev/null 2>&1; then
  prev_image="$(docker inspect --format='{{.Config.Image}}' "$api_container" || true)"
fi

echo "[deploy] Build image: $IMAGE"
docker build -t "$IMAGE" backend

echo "[deploy] Start target stack"
API_IMAGE="$IMAGE" docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" up -d db_target api_target

set -a
source "$ENV_FILE"
set +a
api_base="${TARGET_API_BASE_URL:-http://localhost:${TARGET_API_PORT:-18000}}"

scripts/linux/wait_for_api.sh --api-base-url "$api_base"

mkdir -p "$ARTIFACTS_DIR"
python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
Path('$ARTIFACTS_DIR/deploy-report.json').write_text(json.dumps({
  'status': 'ok',
  'image': '$IMAGE',
  'previous_image': '''$prev_image''',
  'target_api_base_url': '$api_base',
  'deployed_at': datetime.now(timezone.utc).isoformat()
}, indent=2), encoding='utf-8')
PY

echo "[deploy] Target deploy OK: $ARTIFACTS_DIR/deploy-report.json"
