#!/usr/bin/env bash
# Configure le stockage hors site en saisie guidee.
#
# Les identifiants sont saisis directement sur le serveur : ils ne transitent ni
# par une conversation, ni par l'historique du shell.
set -euo pipefail

ENV_FILE="${1:-.env.target}"
NOM_REMOTE="${NOM_REMOTE:-beevarium-offsite}"
RCLONE="${RCLONE:-$HOME/bin/rclone}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ ! -x "$RCLONE" ]]; then
  echo "[hors-site] rclone introuvable: $RCLONE" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[hors-site] Fichier d environnement introuvable: $ENV_FILE" >&2
  exit 1
fi

echo "Configuration du stockage hors site"
echo "-----------------------------------"
echo "Regions OVH courantes : gra, sbg, rbx, de, uk, waw"
read -r -p "Region [gra] : " REGION
REGION="${REGION:-gra}"

DEFAUT_ENDPOINT="s3.${REGION}.io.cloud.ovh.net"
read -r -p "Endpoint S3 [${DEFAUT_ENDPOINT}] : " ENDPOINT
ENDPOINT="${ENDPOINT:-$DEFAUT_ENDPOINT}"

read -r -p "Nom du conteneur [beevarium-sauvegardes] : " CONTENEUR
CONTENEUR="${CONTENEUR:-beevarium-sauvegardes}"

read -r -p "Cle d acces S3 : " ACCESS_KEY
read -r -s -p "Cle secrete S3 : " SECRET_KEY
echo
if [[ -z "$ACCESS_KEY" || -z "$SECRET_KEY" ]]; then
  echo "[hors-site] Identifiants incomplets, abandon" >&2
  exit 1
fi

echo
echo "Phrase de chiffrement des archives."
echo "ATTENTION : sans elle, les sauvegardes distantes sont definitivement illisibles."
echo "La conserver dans un gestionnaire de mots de passe, hors du serveur."
read -r -s -p "Phrase de chiffrement : " PHRASE
echo
read -r -s -p "Confirmer la phrase : " PHRASE_CONFIRMEE
echo
if [[ "$PHRASE" != "$PHRASE_CONFIRMEE" ]]; then
  echo "[hors-site] Les deux phrases different, abandon" >&2
  exit 1
fi
if (( ${#PHRASE} < 16 )); then
  echo "[hors-site] Phrase trop courte: 16 caracteres minimum" >&2
  exit 1
fi
if [[ "$PHRASE" == *"'"* ]]; then
  echo "[hors-site] La phrase ne doit pas contenir d apostrophe" >&2
  exit 1
fi

echo
echo "[hors-site] Declaration du stockage..."
"$RCLONE" config delete "$NOM_REMOTE" >/dev/null 2>&1 || true
"$RCLONE" config create "$NOM_REMOTE" s3 \
  provider=Other \
  access_key_id="$ACCESS_KEY" \
  secret_access_key="$SECRET_KEY" \
  endpoint="$ENDPOINT" \
  region="$REGION" \
  acl=private \
  --non-interactive >/dev/null

echo "[hors-site] Verification de l acces..."
if ! "$RCLONE" lsd "${NOM_REMOTE}:" >/dev/null 2>&1; then
  echo "[hors-site] Connexion refusee. Verifier les identifiants, la region et l endpoint." >&2
  echo "[hors-site] Diagnostic detaille : $RCLONE lsd ${NOM_REMOTE}: -vv" >&2
  exit 1
fi

if ! "$RCLONE" lsd "${NOM_REMOTE}:" 2>/dev/null | grep -q " ${CONTENEUR}$"; then
  echo "[hors-site] Creation du conteneur ${CONTENEUR}..."
  "$RCLONE" mkdir "${NOM_REMOTE}:${CONTENEUR}"
fi

export PHRASE ENV_FILE NOM_REMOTE CONTENEUR
python3 - <<'PY'
import os
import pathlib

chemin = pathlib.Path(os.environ["ENV_FILE"])
valeurs = {
    "BACKUP_OFFSITE_REMOTE": f"{os.environ['NOM_REMOTE']}:{os.environ['CONTENEUR']}",
    "BACKUP_ENCRYPTION_PASSPHRASE": os.environ["PHRASE"],
}

lignes = chemin.read_text(encoding="utf-8").splitlines()
vues = set()
sortie = []


def rendre(cle: str, valeur: str) -> str:
    # Guillemets simples: docker compose prend la valeur litteralement et bash
    # ne tente aucune substitution.
    return f"{cle}='{valeur}'" if cle == "BACKUP_ENCRYPTION_PASSPHRASE" else f"{cle}={valeur}"


for ligne in lignes:
    cle = ligne.split("=", 1)[0] if "=" in ligne else None
    if cle in valeurs:
        sortie.append(rendre(cle, valeurs[cle]))
        vues.add(cle)
    else:
        sortie.append(ligne)

for cle, valeur in valeurs.items():
    if cle not in vues:
        sortie.append(rendre(cle, valeur))

chemin.write_text("\n".join(sortie) + "\n", encoding="utf-8")
print(f"[hors-site] {chemin} mis a jour")
PY

chmod 600 "$ENV_FILE"
chmod 600 "$HOME/.config/rclone/rclone.conf" 2>/dev/null || true

echo
echo "[hors-site] Configuration terminee."
echo "  Premier envoi   : bash scripts/linux/backup_offsite.sh $ENV_FILE"
echo "  Puis activation : bash scripts/linux/install_backup_timers.sh"
