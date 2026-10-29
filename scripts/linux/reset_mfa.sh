#!/usr/bin/env bash
# Reinitialise la double authentification d'un compte verrouille (telephone perdu et aucun code
# de secours ; l'identite du titulaire doit avoir ete verifiee au prealable par l'operateur).
# Effet : l'utilisateur se connecte avec son seul mot de passe et doit reactiver la double
# authentification ; un administrateur perd l'acces a /admin tant qu'elle n'est pas reactivee.
# Usage : reset_mfa.sh <email> [env_file]   (env_file par defaut : .env.target)
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <email> [env_file]" >&2
  exit 2
fi

EMAIL="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
ENV_FILE="${2:-.env.target}"

echo "Reinitialisation de la double authentification pour : $EMAIL"
read -r -p "Tapez 'oui' pour confirmer : " REPONSE
if [[ "$REPONSE" != "oui" ]]; then
  echo "Abandon." >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

RESULTAT="$(docker compose --env-file "$ENV_FILE" -f docker-compose.target.yml exec -T db_target \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -v email="$EMAIL" -qAt <<'SQL'
BEGIN;
DELETE FROM mfa_recovery_codes WHERE user_id = (SELECT id FROM users WHERE lower(email) = :'email');
UPDATE users SET mfa_secret = NULL, mfa_enabled_at = NULL, mfa_last_step = NULL WHERE lower(email) = :'email' RETURNING email;
COMMIT;
SQL
)"

if [[ -z "$RESULTAT" ]]; then
  echo "Compte introuvable: $EMAIL" >&2
  exit 1
fi
echo "Double authentification reinitialisee : $EMAIL"
