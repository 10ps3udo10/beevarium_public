#!/usr/bin/env bash
# Supprime les comptes crees par les smokes (motifs smoke*) dans la base cible.
# --dry-run liste sans supprimer.
set -euo pipefail

ENV_FILE="${1:-.env.target}"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      echo "Usage: $0 [--env-file .env.target] [--dry-run]" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[cleanup-smoke] Fichier d'environnement introuvable: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

case "${ENVIRONMENT:-}" in
  dev|test|staging|local)
    ;;
  *)
    echo "[cleanup-smoke] Refus: ENVIRONMENT=${ENVIRONMENT:-<inconnu>} n'est pas un environnement autorise pour ce script." >&2
    exit 1
    ;;
esac

regex='^(smoke|smokefree)[A-Za-z0-9._%+-]*@example\.com$'

count_sql="SELECT COUNT(*) FROM users WHERE email ~* '${regex}';"
count=$(docker compose --env-file "$ENV_FILE" -f docker-compose.target.yml exec -T db_target psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tA -c "$count_sql")
count=${count:-0}

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[cleanup-smoke] $count compte(s) smoke a supprimer." 
  exit 0
fi

if [[ "$count" -eq 0 ]]; then
  echo "[cleanup-smoke] Aucun compte smoke a purger."
  exit 0
fi

sql="DELETE FROM users WHERE email ~* '${regex}';"
docker compose --env-file "$ENV_FILE" -f docker-compose.target.yml exec -T db_target psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 -c "$sql" >/dev/null

echo "[cleanup-smoke] $count compte(s) smoke supprime(s)."
