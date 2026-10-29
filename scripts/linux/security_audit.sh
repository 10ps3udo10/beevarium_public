#!/usr/bin/env bash
# Audit de securite : vulnerabilites connues des dependances Python
# (pip-audit) et de l'image API (Trivy : paquets systeme + Python).
# Echoue sur une faille HIGH/CRITICAL qui a un correctif disponible.
# Exceptions acceptees : security-ignore.txt (un identifiant par ligne).
#
# Usage : security_audit.sh [--image <image|id>] [--skip-image]
set -euo pipefail

PIP_AUDIT_VERSION="2.9.0"
TRIVY_IMAGE="aquasec/trivy:0.61.0"
IMAGE=""
SKIP_IMAGE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image)
      IMAGE="$2"
      shift 2
      ;;
    --skip-image)
      SKIP_IMAGE=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ignore_file="$repo_root/security-ignore.txt"

if ! command -v docker >/dev/null 2>&1; then
  echo "[security] docker indisponible : audit impossible." >&2
  exit 1
fi

ignore_ids=()
if [[ -f "$ignore_file" ]]; then
  while read -r id _; do
    [[ -z "$id" || "$id" == \#* ]] && continue
    ignore_ids+=("$id")
  done < "$ignore_file"
fi

echo "[security] Dependances Python (pip-audit $PIP_AUDIT_VERSION)"
pip_ignore_args=""
for id in "${ignore_ids[@]+"${ignore_ids[@]}"}"; do
  pip_ignore_args+=" --ignore-vuln $id"
done
docker run --rm -v "$repo_root/backend:/w:ro" -w /w python:3.12-slim sh -c \
  "pip install -q --disable-pip-version-check --root-user-action=ignore pip-audit==$PIP_AUDIT_VERSION \
   && pip-audit --progress-spinner off -r requirements.txt -r requirements-dev.txt$pip_ignore_args"

if [[ "$SKIP_IMAGE" -eq 1 ]]; then
  echo "[security] Image API ignoree (--skip-image)"
  exit 0
fi

if [[ -z "$IMAGE" ]]; then
  for container in beevarium_api beevarium_dev_api_target; do
    if IMAGE="$(docker inspect --format '{{.Image}}' "$container" 2>/dev/null)"; then
      echo "[security] Image du conteneur $container"
      break
    fi
    IMAGE=""
  done
fi
if [[ -z "$IMAGE" ]]; then
  echo "[security] Aucun conteneur API trouve : passer --image ou --skip-image." >&2
  exit 1
fi

echo "[security] Image API (Trivy $TRIVY_IMAGE) : $IMAGE"
docker_args=(--rm -v /var/run/docker.sock:/var/run/docker.sock -v beevarium_trivy_cache:/root/.cache/trivy)
trivy_args=(image --quiet --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1)
if [[ -f "$ignore_file" ]]; then
  docker_args+=(-v "$ignore_file:/security-ignore.txt:ro")
  trivy_args+=(--ignorefile /security-ignore.txt)
fi
docker run "${docker_args[@]}" "$TRIVY_IMAGE" "${trivy_args[@]}" "$IMAGE"

echo "[security] OK"
