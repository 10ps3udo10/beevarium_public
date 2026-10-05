#!/usr/bin/env bash
# Gate complet avant tag de livraison, avec rapport de readiness JSON.
set -euo pipefail

OUTPUT_JSON_PATH="${1:-artifacts/v1-readiness.json}"
API_BASE_URL="${2:-http://localhost:8000}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

start_ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
start_epoch="$(date +%s)"

git_sha="$(git rev-parse --short HEAD)"

scripts/linux/gate_fast.sh --full-integration --api-base-url "$API_BASE_URL"

end_ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
end_epoch="$(date +%s)"
duration="$((end_epoch - start_epoch))"

mkdir -p "$(dirname "$OUTPUT_JSON_PATH")"
python3 - <<PY
import json
from pathlib import Path
report = {
  'status': 'ok',
  'api_base_url': '$API_BASE_URL',
  'git_sha': '$git_sha',
  'started_at': '$start_ts',
  'ended_at': '$end_ts',
  'duration_seconds': $duration,
  'gate': 'gate_fast_full_integration',
  'error': ''
}
Path('$OUTPUT_JSON_PATH').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
PY

echo "[release-candidate] Readiness report written: $OUTPUT_JSON_PATH"
