#!/usr/bin/env bash
# Deploiement en une commande, a lancer sur le VPS :
#   bash ~/app/scripts/linux/deploy.sh                # dernier tag : app-dev, gate, puis beta
#   bash ~/app/scripts/linux/deploy.sh v1.36.3-xxx    # tag precis
#   bash ~/app/scripts/linux/deploy.sh latest dev     # app-dev seulement
#   bash ~/app/scripts/linux/deploy.sh latest beta    # beta seulement (app-dev deja valide)
# Depuis le poste : ssh -t <utilisateur>@<vps> 'bash ~/app/scripts/linux/deploy.sh'
#
# Enchaine les scripts existants : app-dev (pull, migrations, release, gate),
# puis beta apres confirmation (pull, sauvegarde, migrations, release, health
# watch). S'arrete a la premiere erreur et n'avance jamais la beta si app-dev
# echoue. BEEVARIUM_DEPLOY_YES=1 saute la confirmation beta.
set -euo pipefail

# Tout le script est dans main : bash le lit en entier avant d'executer, le
# `git pull` du clone qui contient ce fichier ne peut donc pas le modifier en cours.
main() {
  local requested="${1:-latest}"
  local scope="${2:-all}"
  local dev_dir="${APP_DEV_DIR:-$HOME/app-dev}"
  local beta_dir="${APP_DIR:-$HOME/app}"
  local dev_url="http://127.0.0.1:18001"
  local beta_url="https://beta.beevarium.fr"

  case "$scope" in
    all|dev|beta) ;;
    *) echo "Usage: $0 [latest|<tag>] [all|dev|beta]" >&2; exit 2 ;;
  esac

  mkdir -p "$beta_dir/artifacts/deploy-logs"
  local log="$beta_dir/artifacts/deploy-logs/deploy-$(date -u '+%Y%m%d-%H%M%S').log"
  exec > >(tee -a "$log") 2>&1
  tee_pid=$!
  # A la fin, ssh ferme le terminal et tue tee : les dernieres lignes (verdict
  # compris) etaient perdues, a l'ecran comme dans le journal. On attend tee.
  trap 'exec >&- 2>&-; wait "$tee_pid" 2>/dev/null' EXIT
  echo "[deploy] Journal : $log"

  local tag
  tag="$(resolve_tag "$beta_dir" "$requested")"
  echo "[deploy] Tag : $tag (perimetre : $scope)"

  if [[ "$scope" != "beta" ]]; then
    deploy_dev "$dev_dir" "$tag" "$dev_url"
  fi
  if [[ "$scope" != "dev" ]]; then
    confirm_beta "$tag"
    deploy_beta "$beta_dir" "$tag" "$beta_url"
  fi
  echo "[deploy] Termine : $tag ($scope)"
}

resolve_tag() {
  local dir="$1" requested="$2"
  git -C "$dir" fetch --quiet --tags origin
  if [[ "$requested" == "latest" ]]; then
    # Dernier tag atteignable depuis main : jamais un tag d'une autre branche.
    git -C "$dir" describe --tags --abbrev=0 origin/main
  else
    git -C "$dir" rev-parse --quiet --verify "refs/tags/$requested" >/dev/null || {
      echo "[deploy] Tag introuvable : $requested" >&2
      exit 1
    }
    echo "$requested"
  fi
}

# Met le clone a jour : l'image est construite depuis l'arbre de travail, pas
# depuis le tag.
sync_clone() {
  local dir="$1" tag="$2"
  cd "$dir"
  if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "[deploy] $dir a des modifications locales, arret." >&2
    git status --short --untracked-files=no >&2
    exit 1
  fi
  git pull --quiet --ff-only origin main
  git fetch --quiet --tags origin
  # Image et migrations viennent de backend/ et db/ : ils doivent etre ceux du
  # tag. Des scripts ou de la documentation commites apres le tag sont admis.
  if ! git merge-base --is-ancestor "$tag" HEAD; then
    echo "[deploy] Le tag $tag n'est pas dans l'historique de main." >&2
    exit 1
  fi
  if [[ -n "$(git diff --name-only "$tag" HEAD -- backend db)" ]]; then
    echo "[deploy] backend/ ou db/ ont change depuis $tag : creer un nouveau tag avant de deployer." >&2
    git diff --stat "$tag" HEAD -- backend db >&2
    exit 1
  fi
}

expected_version() {
  sed -nE 's/^ *app_version: str = "([^"]+)".*/\1/p' backend/app/config.py | head -1
}

check_version() {
  local url="$1" expected="$2" health
  health="$(curl -fsS "$url/health")"
  echo "[deploy] /health : $health"
  if [[ "$health" != *"\"app_version\":\"$expected\""* ]]; then
    echo "[deploy] Version attendue $expected absente de /health." >&2
    return 1
  fi
}

deploy_dev() {
  local dir="$1" tag="$2" url="$3"
  echo "[deploy] === app-dev ($dir) ==="
  sync_clone "$dir" "$tag"
  bash scripts/linux/deploy_apply_migrations.sh .env.target
  bash scripts/linux/deploy_release.sh "$tag" .env.target
  bash scripts/linux/gate_fast.sh --api-base-url "$url"
  check_version "$url" "$(expected_version)"
  echo "[deploy] app-dev OK"
}

confirm_beta() {
  local tag="$1"
  if [[ "${BEEVARIUM_DEPLOY_YES:-}" == "1" ]]; then
    return
  fi
  if [[ ! -t 0 ]]; then
    echo "[deploy] Confirmation beta impossible sans terminal (ssh -t, ou BEEVARIUM_DEPLOY_YES=1)." >&2
    exit 1
  fi
  local answer
  read -r -p "[deploy] Deployer $tag sur la beta (donnees reelles) ? Taper 'beta' pour confirmer : " answer
  if [[ "$answer" != "beta" ]]; then
    echo "[deploy] Beta non deployee."
    exit 1
  fi
}

deploy_beta() {
  local dir="$1" tag="$2" url="$3"
  echo "[deploy] === beta ($dir) ==="
  sync_clone "$dir" "$tag"
  bash scripts/linux/deploy_backup_db.sh .env.target artifacts/backups
  if ! bash scripts/linux/deploy_apply_migrations.sh .env.target \
    || ! bash scripts/linux/deploy_release.sh "$tag" .env.target \
    || ! bash scripts/linux/deploy_health_watch.sh "$url" 6 artifacts/beta/health-watch.json \
    || ! check_version "$url" "$(expected_version)"; then
    echo "[deploy] ECHEC beta. Sauvegarde : $(ls -t artifacts/backups/beevarium-target-*.sql 2>/dev/null | head -1)" >&2
    echo "[deploy] Retour arriere : bash scripts/linux/deploy_rollback.sh .env.target (voir docs/06-exploitation.md)" >&2
    exit 1
  fi
  echo "[deploy] beta OK"
}

main "$@"
