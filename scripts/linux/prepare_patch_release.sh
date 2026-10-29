#!/usr/bin/env bash
# Prepare les notes d'une version corrective a partir de l'historique Git.
set -euo pipefail

FROM_REF="${1:-v1.0.0}"
TO_REF="${2:-HEAD}"
OUTPUT_PATH="${3:-artifacts/patch-release-notes.md}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

to_sha="$(git rev-parse --short "$TO_REF")"
generated_at="$(date '+%Y-%m-%d %H:%M:%S %z')"

mkdir -p "$(dirname "$OUTPUT_PATH")"

{
  echo "# Patch Release Notes (Draft)"
  echo
  echo "- From: $FROM_REF"
  echo "- To: $TO_REF ($to_sha)"
  echo "- Generated at: $generated_at"
  echo
  echo "## Commits"
  echo
  if git log --no-merges --pretty=format:'- %h %s' "$FROM_REF..$TO_REF" | grep -q .; then
    git log --no-merges --pretty=format:'- %h %s' "$FROM_REF..$TO_REF"
  else
    echo "- Aucun commit detecte entre ces references."
  fi
  echo
  echo "## Last Readiness Snapshot"
  echo
  if [[ -f artifacts/v1-readiness.json ]]; then
    python3 - <<'PY'
import json
from pathlib import Path
p = Path('artifacts/v1-readiness.json')
try:
    data = json.loads(p.read_text(encoding='utf-8'))
    print(f"- Status: {data.get('status','')}")
    print(f"- Gate: {data.get('gate','')}")
    print(f"- Git SHA: {data.get('git_sha','')}")
    print(f"- Duration (s): {data.get('duration_seconds','')}")
except Exception:
    print("- Impossible de lire artifacts/v1-readiness.json")
PY
  else
    echo "- Aucun snapshot de readiness trouve."
  fi
} > "$OUTPUT_PATH"

echo "[prepare_patch_release] Notes generated: $OUTPUT_PATH"
