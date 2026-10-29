#!/usr/bin/env bash
# Verifie qu'une sauvegarde hors site est reellement exploitable.
#
# Telecharge la derniere archive distante, la dechiffre, verifie l'integrite
# gzip puis la restaure dans un PostgreSQL jetable. Une sauvegarde distante
# jamais restauree ne vaut pas mieux qu'une absence de sauvegarde.
set -euo pipefail

ENV_FILE="${1:-.env.target}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

RCLONE="${RCLONE:-$HOME/bin/rclone}"

set -a
source "$ENV_FILE"
set +a

: "${BACKUP_OFFSITE_REMOTE:?BACKUP_OFFSITE_REMOTE absent de $ENV_FILE}"
: "${BACKUP_ENCRYPTION_PASSPHRASE:?BACKUP_ENCRYPTION_PASSPHRASE absent de $ENV_FILE}"

travail="$(mktemp -d)"
conteneur="beevarium_offsite_check_$$"

nettoyer() {
  rm -rf "$travail"
  docker rm -f "$conteneur" >/dev/null 2>&1 || true
}
trap nettoyer EXIT

derniere="$("$RCLONE" lsf "$BACKUP_OFFSITE_REMOTE" | sort | tail -1)"
if [[ -z "$derniere" ]]; then
  echo "[verif-hors-site] Aucune archive distante" >&2
  exit 1
fi

echo "[verif-hors-site] Archive testee: $derniere"
"$RCLONE" copyto "$BACKUP_OFFSITE_REMOTE/$derniere" "$travail/archive.enc"

openssl enc -d -aes-256-cbc -md sha512 -pbkdf2 -iter 200000 \
  -in "$travail/archive.enc" -out "$travail/archive.sql.gz" \
  -pass env:BACKUP_ENCRYPTION_PASSPHRASE

gzip -t "$travail/archive.sql.gz"

docker run -d --name "$conteneur" \
  -e POSTGRES_USER=verify -e POSTGRES_PASSWORD="$(openssl rand -hex 16)" -e POSTGRES_DB=verify \
  postgres:16-alpine >/dev/null

for _ in $(seq 1 30); do
  docker exec "$conteneur" pg_isready -U verify -d verify >/dev/null 2>&1 && break
  sleep 1
done

gunzip -c "$travail/archive.sql.gz" | docker exec -i "$conteneur" psql -U verify -d verify -q >/dev/null

comptes="$(docker exec "$conteneur" psql -U verify -d verify -tA -c "SELECT count(*) FROM users;")"
if (( comptes < 1 )); then
  echo "[verif-hors-site] Restauration invalide: aucun utilisateur" >&2
  exit 1
fi

rapport="artifacts/backups/last-offsite-check.json"
cat > "$rapport" <<JSON
{
  "status": "ok",
  "archive": "$derniere",
  "utilisateurs_restaures": $comptes,
  "verifie_le": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
}
JSON

echo "[verif-hors-site] OK: $comptes utilisateur(s) restaure(s) depuis le stockage distant"
