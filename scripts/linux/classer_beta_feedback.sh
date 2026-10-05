#!/usr/bin/env bash
# Classe des retours testeurs comme traites (historique conserve, rien n'est supprime).
# Usage : classer_beta_feedback.sh .env.target "note de traitement" <id8> [<id8> ...]
# Les identifiants sont les 8 premiers caracteres affiches par list_beta_feedback.sh.
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 .env.target \"note\" <id8> [<id8> ...]" >&2
  exit 2
fi

ENV_FILE="$1"
NOTE="$2"
shift 2

for id in "$@"; do
  if [[ ! "$id" =~ ^[0-9a-f]{8}$ ]]; then
    echo "Identifiant invalide: $id (8 caracteres hexadecimaux attendus)" >&2
    exit 2
  fi
done

set -a
source "$ENV_FILE"
set +a

ids_sql="$(printf "'%s'," "$@")"
ids_sql="${ids_sql%,}"

docker compose --env-file "$ENV_FILE" -f docker-compose.target.yml exec -T db_target \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -v note="$NOTE" -P pager=off <<SQL
UPDATE beta_feedback
SET traite_le = NOW(), note_traitement = :'note'
WHERE left(id::text, 8) IN (${ids_sql}) AND traite_le IS NULL
RETURNING left(id::text, 8) AS id, category, note_traitement;
SQL
