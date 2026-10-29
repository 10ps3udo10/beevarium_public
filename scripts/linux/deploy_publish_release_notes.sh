#!/usr/bin/env bash
# Genere les notes de version entre deux references Git.
set -euo pipefail

FROM_REF="${1:-v1.0.0}"
TO_REF="${2:-HEAD}"
OUTPUT_DIR="${3:-artifacts/releases}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

mkdir -p "$OUTPUT_DIR"
stamp="$(date '+%Y%m%d-%H%M%S')"
out="$OUTPUT_DIR/patch-release-${stamp}.md"

scripts/linux/prepare_patch_release.sh "$FROM_REF" "$TO_REF" "$out"

echo "[deploy] Patch release published: $out"
