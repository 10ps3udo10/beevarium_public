#!/usr/bin/env bash
# Verifie le rapport JSON produit par smoke_api.sh.
set -euo pipefail

INPUT_PATH="${1:-artifacts/smoke-result.json}"

python3 - <<PY
import json
from pathlib import Path
p = Path('$INPUT_PATH')
if not p.exists():
    raise SystemExit(f"Missing file: {p}")
obj = json.loads(p.read_text(encoding='utf-8'))
if obj.get('status') != 'ok':
    raise SystemExit('Smoke JSON status is not ok')
if 'api_base_url' not in obj:
    raise SystemExit('Smoke JSON missing api_base_url')
print(f"[validate_smoke_json] Smoke recap valid: {p}")
PY
