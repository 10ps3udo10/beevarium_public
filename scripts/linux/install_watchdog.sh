#!/usr/bin/env bash
# Installe le timer systemd utilisateur de supervision (alertes e-mail).
# Ne necessite aucun privilege root. Destinataire : ALERT_EMAIL de .env.target
# (contact@beevarium.fr par defaut).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
units_dir="$HOME/.config/systemd/user"

mkdir -p "$units_dir"
cp "$repo_root"/scripts/systemd/beevarium-watchdog.service "$units_dir/"
cp "$repo_root"/scripts/systemd/beevarium-watchdog.timer "$units_dir/"
loginctl enable-linger "$USER"
systemctl --user daemon-reload

# Premier passage a blanc : affiche les controles sans envoyer d'e-mail.
python3 "$repo_root/scripts/watchdog.py" .env.target --dry-run

systemctl --user enable --now beevarium-watchdog.timer
systemctl --user list-timers 'beevarium-watchdog*' --no-pager
