#!/usr/bin/env bash
# Copie chiffree des sauvegardes vers un stockage distant.
#
# Les sauvegardes locales protegent d'une erreur de manipulation. Elles ne
# protegent pas de la perte du serveur: ce script repond a ce risque-la.
#
# Le contenu est chiffre avant l'envoi: il comporte des adresses e-mail et des
# empreintes de mots de passe, qui n'ont rien a faire en clair chez un tiers.
set -euo pipefail

ENV_FILE="${1:-.env.target}"
SOURCE_DIR="${2:-artifacts/backups}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

RCLONE="${RCLONE:-$HOME/bin/rclone}"
CHIFFRES_DIR="$SOURCE_DIR/chiffres"

if [[ ! -x "$RCLONE" ]]; then
  echo "[hors-site] rclone introuvable: $RCLONE" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[hors-site] Fichier d environnement introuvable: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

: "${BACKUP_OFFSITE_REMOTE:?BACKUP_OFFSITE_REMOTE absent de $ENV_FILE}"
: "${BACKUP_ENCRYPTION_PASSPHRASE:?BACKUP_ENCRYPTION_PASSPHRASE absent de $ENV_FILE}"

mkdir -p "$CHIFFRES_DIR"

chiffres=0
for archive in "$SOURCE_DIR"/beevarium-*.sql.gz; do
  [[ -e "$archive" ]] || continue
  cible="$CHIFFRES_DIR/$(basename "$archive").enc"
  [[ -f "$cible" ]] && continue
  openssl enc -aes-256-cbc -md sha512 -pbkdf2 -iter 200000 -salt \
    -in "$archive" -out "$cible" -pass env:BACKUP_ENCRYPTION_PASSPHRASE
  chiffres=$((chiffres + 1))
done

# Les archives locales supprimees par la retention le sont aussi a distance:
# sync, et non copy, pour que les deux cotes restent alignes.
for orphelin in "$CHIFFRES_DIR"/*.enc; do
  [[ -e "$orphelin" ]] || continue
  origine="$SOURCE_DIR/$(basename "$orphelin" .enc)"
  [[ -f "$origine" ]] || rm -f "$orphelin"
done

echo "[hors-site] $chiffres nouvelle(s) archive(s) chiffree(s)"
"$RCLONE" sync "$CHIFFRES_DIR" "$BACKUP_OFFSITE_REMOTE" --stats-one-line

distantes="$("$RCLONE" lsf "$BACKUP_OFFSITE_REMOTE" | wc -l)"
locales="$(find "$CHIFFRES_DIR" -name '*.enc' -type f | wc -l)"

rapport="$SOURCE_DIR/last-offsite.json"
cat > "$rapport" <<JSON
{
  "status": "ok",
  "remote": "$BACKUP_OFFSITE_REMOTE",
  "archives_locales": $locales,
  "archives_distantes": $distantes,
  "chiffrees_cette_fois": $chiffres,
  "synchronise_le": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
}
JSON

if [[ "$distantes" -ne "$locales" ]]; then
  echo "[hors-site] Ecart: $locales archive(s) locale(s) contre $distantes a distance" >&2
  exit 1
fi

echo "[hors-site] OK: $distantes archive(s) chiffree(s) hors site"
