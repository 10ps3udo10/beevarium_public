#!/usr/bin/env bash
# Publie la page d'accueil statique (dossier site/) servie par Caddy sur
# beevarium.fr. Le dossier cible doit appartenir a l'utilisateur courant
# (preparation unique, voir docs/06-exploitation.md).
set -euo pipefail

TARGET="${1:-/var/www/beevarium}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ ! -w "$TARGET" ]]; then
  echo "[site] $TARGET absent ou non inscriptible : faire la preparation unique." >&2
  exit 1
fi

cp -R "$repo_root"/site/. "$TARGET"/
echo "[site] Page d'accueil publiee dans $TARGET"
