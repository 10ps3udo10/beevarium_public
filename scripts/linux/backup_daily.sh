#!/usr/bin/env bash
# Sauvegarde quotidienne de la base cible, avec compression, controle de taille
# et purge des archives trop anciennes. Concu pour etre lance par cron.
# Purge d'abord le journal technique api_events au-dela de 6 mois (decision
# concepteur 2026-10-05, annoncee dans privacy.html).
set -euo pipefail

ENV_FILE="${1:-.env.target}"
OUTPUT_DIR="${2:-artifacts/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
MIN_SIZE_BYTES="${MIN_SIZE_BYTES:-10240}"
API_EVENTS_RETENTION_MONTHS="${API_EVENTS_RETENTION_MONTHS:-6}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[backup] Missing env file: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

if [[ ! "$API_EVENTS_RETENTION_MONTHS" =~ ^[1-9][0-9]*$ ]]; then
  echo "[backup] API_EVENTS_RETENTION_MONTHS invalide: $API_EVENTS_RETENTION_MONTHS" >&2
  exit 1
fi

# Un echec de purge ne doit pas empecher la sauvegarde : on le signale seulement.
purged="$(docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" exec -T db_target \
  sh -lc "psql -U '$POSTGRES_USER' -d '$POSTGRES_DB' -v ON_ERROR_STOP=1 -tA -c \"WITH supprimes AS (DELETE FROM api_events WHERE created_at < NOW() - INTERVAL '${API_EVENTS_RETENTION_MONTHS} months' RETURNING 1) SELECT count(*) FROM supprimes;\"" \
  | tr -d '[:space:]')" || {
  echo "[backup] Purge api_events en echec, sauvegarde poursuivie" >&2
  purged="erreur"
}
echo "[backup] api_events purges (> ${API_EVENTS_RETENTION_MONTHS} mois): ${purged}"

mkdir -p "$OUTPUT_DIR"
stamp="$(date -u '+%Y%m%d-%H%M%S')"
out="$OUTPUT_DIR/beevarium-${stamp}.sql.gz"

# --no-owner/--no-acl: la sauvegarde doit pouvoir se restaurer sous un autre role.
docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" exec -T db_target \
  sh -lc "pg_dump --no-owner --no-acl -U '$POSTGRES_USER' -d '$POSTGRES_DB'" | gzip -9 > "$out"

size="$(wc -c < "$out")"
if (( size < MIN_SIZE_BYTES )); then
  rm -f "$out"
  echo "[backup] Dump trop petit (${size} octets), sauvegarde rejetee" >&2
  exit 1
fi

# L archive doit etre relisible: un gzip tronque passerait autrement inapercu.
if ! gzip -t "$out"; then
  rm -f "$out"
  echo "[backup] Archive corrompue, sauvegarde rejetee" >&2
  exit 1
fi

find "$OUTPUT_DIR" -maxdepth 1 -name 'beevarium-*.sql.gz' -type f -mtime "+${RETENTION_DAYS}" -delete

kept="$(find "$OUTPUT_DIR" -maxdepth 1 -name 'beevarium-*.sql.gz' -type f | wc -l)"
report="$OUTPUT_DIR/last-backup.json"
cat > "$report" <<JSON
{
  "status": "ok",
  "file": "$out",
  "size_bytes": $size,
  "backups_kept": $kept,
  "retention_days": $RETENTION_DAYS,
  "api_events_retention_months": $API_EVENTS_RETENTION_MONTHS,
  "api_events_purged": "$purged",
  "created_at": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
}
JSON

echo "[backup] OK: $out (${size} octets, ${kept} archives conservees)"
