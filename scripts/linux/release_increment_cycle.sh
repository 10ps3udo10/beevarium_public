#!/usr/bin/env bash
# Enchaine gate rapide, gate complet et notes de version pour un increment.
set -euo pipefail

API_BASE_URL="${1:-http://localhost:8000}"
FROM_REF="${2:-v1.0.0}"
TO_REF="${3:-HEAD}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

scripts/linux/gate_fast.sh --api-base-url "$API_BASE_URL"
scripts/linux/gate_release_candidate.sh artifacts/v1-readiness-linux.json "$API_BASE_URL"
scripts/linux/prepare_patch_release.sh "$FROM_REF" "$TO_REF" artifacts/patch-release-notes-linux.md

echo "[release_cycle] OK - fast gate + release candidate + patch notes"
