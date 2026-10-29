#!/usr/bin/env bash
# Verifie qu une sauvegarde est reellement restaurable, en la rejouant dans un
# PostgreSQL jetable. Une sauvegarde jamais restauree n est pas une sauvegarde.
set -euo pipefail

BACKUP_FILE="${1:-}"
OUTPUT_DIR="${2:-artifacts/backups}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ -z "$BACKUP_FILE" ]]; then
  BACKUP_FILE="$(find "$OUTPUT_DIR" -maxdepth 1 -name 'beevarium-*.sql.gz' -type f | sort | tail -1)"
fi

if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo "[verify] Aucune sauvegarde trouvee" >&2
  exit 1
fi

container="beevarium_restore_check_$$"
password="$(openssl rand -hex 16)"

cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[verify] Restauration de $BACKUP_FILE dans un conteneur jetable"
docker run -d --name "$container" \
  -e POSTGRES_USER=verify \
  -e POSTGRES_PASSWORD="$password" \
  -e POSTGRES_DB=verify \
  postgres:16-alpine >/dev/null

for _ in $(seq 1 30); do
  if docker exec "$container" pg_isready -U verify -d verify >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

gunzip -c "$BACKUP_FILE" | docker exec -i "$container" psql -U verify -d verify -q >/dev/null

counts="$(docker exec "$container" psql -U verify -d verify -tA -c \
  "SELECT (SELECT count(*) FROM users) || '|' || (SELECT count(*) FROM ruchers) || '|' || (SELECT count(*) FROM ruches) || '|' || (SELECT count(*) FROM visites_ruche);")"

users="${counts%%|*}"
rest="${counts#*|}"
ruchers="${rest%%|*}"
rest="${rest#*|}"
ruches="${rest%%|*}"
visites="${rest##*|}"

if (( users < 1 )); then
  echo "[verify] Restauration invalide: aucun utilisateur" >&2
  exit 1
fi

report="$OUTPUT_DIR/last-restore-check.json"
cat > "$report" <<JSON
{
  "status": "ok",
  "backup_file": "$BACKUP_FILE",
  "users": $users,
  "ruchers": $ruchers,
  "ruches": $ruches,
  "visites_ruche": $visites,
  "verified_at": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
}
JSON

echo "[verify] OK: ${users} utilisateurs, ${ruchers} ruchers, ${ruches} ruches, ${visites} visites"
