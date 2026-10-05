#!/usr/bin/env bash
# Liste les retours des testeurs enregistres dans la base cible.
# Par defaut seuls les retours non traites ; --tous affiche aussi l'historique.
# Classer un retour traite : scripts/linux/classer_beta_feedback.sh.
set -euo pipefail

ENV_FILE="${1:-.env.target}"
FILTRE="WHERE f.traite_le IS NULL"
if [[ "${2:-}" == "--tous" ]]; then
  FILTRE=""
fi

set -a
source "$ENV_FILE"
set +a

docker compose --env-file "$ENV_FILE" -f docker-compose.target.yml exec -T db_target \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -P pager=off -c "
    SELECT left(f.id::text, 8) AS id, f.created_at, f.category, u.email, f.context, f.message,
           f.traite_le, f.note_traitement
    FROM beta_feedback f
    JOIN users u ON u.id = f.user_id
    $FILTRE
    ORDER BY f.created_at DESC;
  "
