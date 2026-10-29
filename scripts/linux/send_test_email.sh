#!/usr/bin/env bash
# Envoie un e-mail de test en reutilisant la configuration SMTP de l API
# deployee. Valide la chaine complete sans toucher a un compte utilisateur.
set -euo pipefail

DESTINATAIRE="${1:-}"
ENV_FILE="${2:-.env.target}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ -z "$DESTINATAIRE" ]]; then
  echo "Usage: $0 <destinataire> [env-file]" >&2
  exit 1
fi

stack_name="$(grep -E '^STACK_NAME=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"
api_container="${stack_name:-beevarium}_api_target"

docker exec -e TEST_RECIPIENT="$DESTINATAIRE" "$api_container" python -c "
import os
from app.emailer import send_email, smtp_is_configured
from app.config import settings

if not smtp_is_configured():
    raise SystemExit('SMTP non configure: SMTP_HOST est vide')

print(f'Serveur: {settings.smtp_host}:{settings.smtp_port} TLS={settings.smtp_use_tls}')
print(f'Expediteur: {settings.smtp_from_email}')

ok = send_email(
    os.environ['TEST_RECIPIENT'],
    'Test Beevarium',
    'Ceci est un message de test envoye depuis Beevarium.\n\nSi vous le recevez, la configuration SMTP est fonctionnelle.',
)
raise SystemExit(0 if ok else 'Echec d envoi, voir les logs du conteneur')
"

echo "[smtp] Message remis au serveur. Verifier la boite de reception et le dossier indesirables."
