#!/usr/bin/env bash
# Installe les timers systemd utilisateur qui planifient les sauvegardes.
# Ne necessite aucun privilege root.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
units_dir="$HOME/.config/systemd/user"

mkdir -p "$units_dir"
cp "$repo_root"/scripts/systemd/beevarium-backup*.service "$units_dir/"
cp "$repo_root"/scripts/systemd/beevarium-backup*.timer "$units_dir/"

# Sans linger, les timers ne tournent que pendant une session ouverte.
loginctl enable-linger "$USER"

systemctl --user daemon-reload

# La copie hors site n'est activee que si un stockage distant est configure.
for unite in "$units_dir"/beevarium-backup*.timer; do
  nom="$(basename "$unite")"
  if [[ "$nom" == *offsite* ]] && ! grep -q "^BACKUP_OFFSITE_REMOTE=" "$repo_root/.env.target" 2>/dev/null; then
    echo "[backup] $nom ignore: BACKUP_OFFSITE_REMOTE absent de .env.target"
    continue
  fi
  systemctl --user enable --now "$nom"
done

echo "[backup] Timers installes:"
systemctl --user list-timers 'beevarium-*' --no-pager
