#!/usr/bin/env bash
# Attribue ou retire le role administrateur (seul moyen : aucune route API ne le permet).
# Usage : set_admin.sh <email> on|off [env_file]   (env_file par defaut : .env.target)
# L'administration exige aussi la double authentification du compte (voir /admin).
set -euo pipefail

if [[ $# -lt 2 || ! "$2" =~ ^(on|off)$ ]]; then
  echo "Usage: $0 <email> on|off [env_file]" >&2
  exit 2
fi

EMAIL="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
VALEUR="false"
[[ "$2" == "on" ]] && VALEUR="true"
ENV_FILE="${3:-.env.target}"

set -a
source "$ENV_FILE"
set +a

RESULTAT="$(docker compose --env-file "$ENV_FILE" -f docker-compose.target.yml exec -T db_target \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -v email="$EMAIL" -v valeur="$VALEUR" -At <<'SQL'
UPDATE users SET is_admin = :'valeur'::boolean WHERE lower(email) = :'email' RETURNING email;
SQL
)"

if [[ -z "$RESULTAT" ]]; then
  echo "Compte introuvable: $EMAIL" >&2
  exit 1
fi
echo "Administrateur $2 : $EMAIL"
