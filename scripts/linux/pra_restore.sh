#!/usr/bin/env bash
# Plan de reprise (R1) : restaure une sauvegarde dans une stack cible, applique
# les migrations, demarre l'API, attend /health et affiche des comptages de
# controle ainsi que la duree de chaque etape. Voir docs/17-plan-reprise.md.
#
# Usage : pra_restore.sh <env_file> <sauvegarde.sql.gz|sauvegarde.sql.gz.enc>
#           [--force] [--tag TAG] [--expect "users|ruchers|ruches|visites"]
#
# - Un fichier .enc est dechiffre avec la meme commande openssl que
#   backup_offsite.sh / backup_offsite_verify.sh (BACKUP_ENCRYPTION_PASSPHRASE
#   lue dans l'env_file).
# - Refuse une base deja peuplee sans --force.
# - Refuse l'env_file de la beta (port 18000 ou STACK_NAME vide / "beevarium")
#   sauf CONFIRM_BETA_RESTORE=oui.
set -euo pipefail

ENV_FILE=""
BACKUP=""
FORCE=0
TAG=""
EXPECT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1; shift ;;
    --tag) TAG="$2"; shift 2 ;;
    --expect) EXPECT="$2"; shift 2 ;;
    -*) echo "[pra] Option inconnue: $1" >&2; exit 1 ;;
    *)
      if [[ -z "$ENV_FILE" ]]; then ENV_FILE="$1"
      elif [[ -z "$BACKUP" ]]; then BACKUP="$1"
      else echo "[pra] Argument en trop: $1" >&2; exit 1; fi
      shift ;;
  esac
done

if [[ -z "$ENV_FILE" || -z "$BACKUP" ]]; then
  echo "Usage: $0 <env_file> <sauvegarde.sql.gz[.enc]> [--force] [--tag TAG] [--expect \"u|r|h|v\"]" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

[[ -f "$ENV_FILE" ]] || { echo "[pra] env_file introuvable: $ENV_FILE" >&2; exit 1; }
[[ -f "$BACKUP" ]] || { echo "[pra] Sauvegarde introuvable: $BACKUP" >&2; exit 1; }

set -a
source "$ENV_FILE"
set +a

# Garde-fou beta : la beta utilise le port 18000 et le STACK_NAME par defaut.
if [[ "${TARGET_API_PORT:-}" == "18000" || -z "${STACK_NAME:-}" || "${STACK_NAME:-}" == "beevarium" ]]; then
  if [[ "${CONFIRM_BETA_RESTORE:-}" != "oui" ]]; then
    echo "[pra] REFUS: $ENV_FILE designe la beta (port 18000 ou STACK_NAME beta/vide)." >&2
    echo "[pra] Sur un VPS de remplacement uniquement: CONFIRM_BETA_RESTORE=oui $0 ..." >&2
    exit 1
  fi
  echo "[pra] ATTENTION: cible beta confirmee par CONFIRM_BETA_RESTORE=oui"
fi

dc() { docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" "$@"; }
psqlc() { dc exec -T db_target psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 "$@"; }

travail="$(mktemp -d)"
trap 'rm -rf "$travail"' EXIT

NOMS=(); DUREES=()
etape_debut() { ETAPE="$1"; T0=$SECONDS; echo "[pra] == $ETAPE"; }
etape_fin() { NOMS+=("$ETAPE"); DUREES+=($((SECONDS - T0))); }
DEBUT=$SECONDS

# 1. Preparation de l'archive
etape_debut "Preparation de l'archive"
if [[ "$BACKUP" == *.enc ]]; then
  : "${BACKUP_ENCRYPTION_PASSPHRASE:?BACKUP_ENCRYPTION_PASSPHRASE absent de $ENV_FILE}"
  openssl enc -d -aes-256-cbc -md sha512 -pbkdf2 -iter 200000 \
    -in "$BACKUP" -out "$travail/archive.sql.gz" -pass env:BACKUP_ENCRYPTION_PASSPHRASE
else
  cp "$BACKUP" "$travail/archive.sql.gz"
fi
gzip -t "$travail/archive.sql.gz"
etape_fin

# 2. Base de donnees demarree et controle de base vide
etape_debut "Demarrage de la base"
dc up -d db_target
# -h 127.0.0.1 : sur un volume vide, le serveur temporaire d'initialisation
# n'ecoute que sur le socket Unix puis s'arrete ; seul le vrai serveur repond en TCP.
for _ in $(seq 1 90); do
  dc exec -T db_target pg_isready -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1 && break
  sleep 1
done
dc exec -T db_target pg_isready -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null
existants="$(psqlc -tA -c "SELECT CASE WHEN to_regclass('public.users') IS NULL THEN 0 ELSE (SELECT count(*) FROM users) END;" | tr -d '[:space:]')"
if (( existants > 0 && FORCE == 0 )); then
  echo "[pra] REFUS: la base cible contient deja $existants utilisateur(s). Utiliser --force pour l'ecraser." >&2
  exit 1
fi
etape_fin

# 3. Restauration. Le volume vide a deja recu db/init (docker-entrypoint-initdb.d) :
# le schema public est recree vide pour que le dump s'applique sans conflit.
etape_debut "Restauration du dump"
psqlc -q -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
gunzip -c "$travail/archive.sql.gz" | psqlc -q --single-transaction >/dev/null
etape_fin

# 4. Migrations
etape_debut "Migrations"
bash scripts/linux/deploy_apply_migrations.sh "$ENV_FILE"
etape_fin

# 5. Release (build de l'image, demarrage de l'API, attente de /health)
TAG="${TAG:-$(git describe --tags --always 2>/dev/null || echo pra)}"
etape_debut "Release $TAG et /health"
bash scripts/linux/deploy_release.sh "$TAG" "$ENV_FILE"
etape_fin

# 6. Controles
etape_debut "Controles"
api_base="${TARGET_API_BASE_URL:-http://localhost:${TARGET_API_PORT}}"
echo "[pra] /health: $(curl -fsS "${api_base%/}/health")"
comptes="$(psqlc -tA -c "SELECT (SELECT count(*) FROM users) || '|' || (SELECT count(*) FROM ruchers) || '|' || (SELECT count(*) FROM ruches) || '|' || (SELECT count(*) FROM visites_ruche);" | tr -d '[:space:]')"
IFS='|' read -r c_users c_ruchers c_ruches c_visites <<< "$comptes"
echo "[pra] Comptages: users=$c_users ruchers=$c_ruchers ruches=$c_ruches visites_ruche=$c_visites"
statut=0
if [[ -n "$EXPECT" ]]; then
  if [[ "$comptes" == "${EXPECT//[[:space:]]/}" ]]; then
    echo "[pra] Comptages identiques a la source ($EXPECT)"
  else
    echo "[pra] ECART: attendu $EXPECT, obtenu $comptes" >&2
    statut=1
  fi
fi
(( c_users >= 1 )) || { echo "[pra] Restauration invalide: aucun utilisateur" >&2; statut=1; }
etape_fin

echo "[pra] ---- Durees"
for i in "${!NOMS[@]}"; do printf '[pra] %-32s %4d s\n' "${NOMS[$i]}" "${DUREES[$i]}"; done
printf '[pra] %-32s %4d s\n' "TOTAL" "$((SECONDS - DEBUT))"
exit "$statut"
