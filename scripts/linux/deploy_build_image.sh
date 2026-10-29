#!/usr/bin/env bash
# Construit l'image Docker versionnee de l'API (beevarium-api:<tag>).
set -euo pipefail

TAG="${1:-v1.0.1-rc1}"
IMAGE="beevarium-api:${TAG}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

echo "[deploy] Build image $IMAGE"
docker build -t "$IMAGE" backend

mkdir -p artifacts
python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
Path('artifacts/deploy-image.json').write_text(json.dumps({
    'status': 'ok',
    'image': '$IMAGE',
    'built_at': datetime.now(timezone.utc).isoformat()
}, indent=2), encoding='utf-8')
PY

echo "[deploy] Image ready: $IMAGE"
