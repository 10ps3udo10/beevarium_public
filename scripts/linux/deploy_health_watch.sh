#!/usr/bin/env bash
# Interroge /health plusieurs fois apres un deploiement et ecrit un rapport JSON.
set -euo pipefail

API_BASE_URL="${1:-http://localhost:18000}"
CHECKS="${2:-6}"
OUTPUT_PATH="${3:-artifacts/health-watch.json}"

API_BASE_URL="${API_BASE_URL%/}"
mkdir -p "$(dirname "$OUTPUT_PATH")"

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

echo '[' > "$tmp_file"
for i in $(seq 1 "$CHECKS"); do
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if health="$(curl -fsS "${API_BASE_URL}/health" 2>/dev/null)"; then
    detail="$(python3 - <<PY
import json
obj=json.loads('''$health''')
print(f"database={obj.get('database','unknown')}")
PY
)"
    status="ok"
  else
    detail="health request failed"
    status="ko"
  fi

  printf '  {"index": %s, "timestamp": "%s", "status": "%s", "detail": "%s"}' "$i" "$ts" "$status" "$detail" >> "$tmp_file"
  if [[ "$i" != "$CHECKS" ]]; then
    echo ',' >> "$tmp_file"
  else
    echo >> "$tmp_file"
  fi
done
echo ']' >> "$tmp_file"

overall="ok"
if grep -q '"status": "ko"' "$tmp_file"; then
  overall="degraded"
fi

python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
results = json.loads(Path('$tmp_file').read_text(encoding='utf-8'))
report = {
  'status': '$overall',
  'api_base_url': '$API_BASE_URL',
  'checks': int('$CHECKS'),
  'results': results,
  'generated_at': datetime.now(timezone.utc).isoformat()
}
Path('$OUTPUT_PATH').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
PY

echo "[deploy] Health watch completed: $OUTPUT_PATH"
