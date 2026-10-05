#!/usr/bin/env bash
# Configure les parametres SMTP dans un fichier .env, en saisie interactive.
# Le mot de passe est saisi en masque et n apparait ni a l ecran, ni dans
# l historique du shell.
set -euo pipefail

ENV_FILE="${1:-.env.target}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[smtp] Fichier introuvable: $ENV_FILE" >&2
  exit 1
fi

read -r -p "Serveur SMTP [ssl0.ovh.net] : " SMTP_HOST_IN
read -r -p "Port [587] : " SMTP_PORT_IN
read -r -p "Adresse d envoi (= identifiant SMTP) [no-reply@beevarium.fr] : " SMTP_FROM_IN
read -r -s -p "Mot de passe de la boite : " SMTP_PASSWORD_IN
echo

if [[ -z "$SMTP_PASSWORD_IN" ]]; then
  echo "[smtp] Mot de passe vide, abandon" >&2
  exit 1
fi

# Le fichier est a la fois lu par docker compose et source par des scripts bash.
# Une apostrophe empecherait de quoter la valeur de facon sure pour les deux.
if [[ "$SMTP_PASSWORD_IN" == *"'"* ]]; then
  echo "[smtp] Le mot de passe contient une apostrophe, non supporte." >&2
  echo "[smtp] Changez-le dans l espace client puis relancez ce script." >&2
  exit 1
fi

export SMTP_HOST_IN="${SMTP_HOST_IN:-ssl0.ovh.net}"
export SMTP_PORT_IN="${SMTP_PORT_IN:-587}"
export SMTP_FROM_IN="${SMTP_FROM_IN:-no-reply@beevarium.fr}"
export SMTP_PASSWORD_IN
export ENV_FILE

python3 - <<'PY'
import os
import pathlib

env_path = pathlib.Path(os.environ["ENV_FILE"])
values = {
    "SMTP_HOST": os.environ["SMTP_HOST_IN"],
    "SMTP_PORT": os.environ["SMTP_PORT_IN"],
    "SMTP_USERNAME": os.environ["SMTP_FROM_IN"],
    "SMTP_PASSWORD": os.environ["SMTP_PASSWORD_IN"],
    "SMTP_USE_TLS": "true",
    "SMTP_FROM_EMAIL": os.environ["SMTP_FROM_IN"],
    "SMTP_FROM_NAME": "Beevarium",
}

lines = env_path.read_text(encoding="utf-8").splitlines()
seen = set()
out = []


def render(key: str, value: str) -> str:
    # Guillemets simples: docker compose prend la valeur litteralement et bash
    # ne tente aucune substitution. Indispensable des que le mot de passe
    # contient $, backtick, parentheses ou espaces.
    return f"{key}='{value}'" if key == "SMTP_PASSWORD" else f"{key}={value}"


for line in lines:
    key = line.split("=", 1)[0] if "=" in line else None
    if key in values:
        out.append(render(key, values[key]))
        seen.add(key)
    else:
        out.append(line)

for key, value in values.items():
    if key not in seen:
        out.append(render(key, value))

env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"[smtp] {env_path} mis a jour")
PY

chmod 600 "$ENV_FILE"
echo "[smtp] Relancer le deploiement pour appliquer: bash scripts/linux/deploy_release.sh <tag> $ENV_FILE"
