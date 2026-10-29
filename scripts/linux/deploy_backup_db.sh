#!/usr/bin/env bash
# Sauvegarde pg_dump de la base cible avant migration ou deploiement.
set -euo pipefail

ENV_FILE="${1:-.env.target}"
OUTPUT_DIR="${2:-artifacts/backups}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

set -a
source "$ENV_FILE"
set +a

mkdir -p "$OUTPUT_DIR"
stamp="$(date '+%Y%m%d-%H%M%S')"
out="$OUTPUT_DIR/beevarium-target-${stamp}.sql"

docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" exec -T db_target sh -lc "pg_dump -U '$POSTGRES_USER' -d '$POSTGRES_DB'" > "$out"

echo "[deploy] DB backup created: $out"
