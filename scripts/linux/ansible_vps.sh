#!/usr/bin/env bash
# Lance le playbook ansible/vps.yml depuis un conteneur (aucune installation
# locale d'Ansible). Usage :
#   bash scripts/linux/ansible_vps.sh [--check] [--tags a,b] [--inventory FICHIER]
# L'inventaire reel (hors Git) est ansible/inventory/vps.ini par defaut.
# Hors --check, la variable CONFIRM_VPS=oui est obligatoire.
# Garder une session SSH ouverte pendant l'execution (voir docs/06-exploitation.md).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
inventory="$repo_root/ansible/inventory/vps.ini"
check=0
extra=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) check=1; extra+=(--check --diff); shift ;;
    --tags) extra+=(--tags "${2:?--tags demande une valeur}"); shift 2 ;;
    --inventory) inventory="${2:?--inventory demande un fichier}"; shift 2 ;;
    *) echo "[ansible-vps] Option inconnue: $1" >&2; exit 2 ;;
  esac
done

if [[ "$check" -eq 0 && "${CONFIRM_VPS:-}" != "oui" ]]; then
  echo "[ansible-vps] Refus: hors --check, definir CONFIRM_VPS=oui." >&2
  exit 1
fi
if [[ ! -f "$inventory" ]]; then
  echo "[ansible-vps] Inventaire introuvable: $inventory (copier ansible/inventory/vps.example.ini)." >&2
  exit 1
fi

ssh_dir="${SSH_DIR:-$HOME/.ssh}"
inv_dir="$(cd "$(dirname "$inventory")" && pwd)"
inv_name="$(basename "$inventory")"

docker run --rm -t \
  -v "$repo_root/ansible:/work/ansible" \
  -v "$inv_dir:/work/inventory:ro" \
  -v "$ssh_dir:/root/.ssh:ro" \
  -w /work/ansible \
  -e ANSIBLE_HOST_KEY_CHECKING=True \
  python:3.12-slim bash -c '
    set -euo pipefail
    apt-get update -qq && apt-get install -y -qq --no-install-recommends openssh-client >/dev/null
    pip install -q "ansible-core==2.17.*"
    ansible-galaxy collection install -q -r requirements.yml
    ansible-playbook -i "/work/inventory/$0" vps.yml "$@"
  ' "$inv_name" ${extra[@]+"${extra[@]}"}
