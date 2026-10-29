#!/usr/bin/env bash
# Scan quotidien des images des conteneurs en cours (Trivy) avec alerte e-mail.
# Memes image Trivy, severites et options que security_audit.sh : HIGH/CRITICAL
# avec correctif disponible, exceptions dans security-ignore.txt.
#
# Sortie silencieuse si rien n'est a signaler. Un e-mail part a l'apparition ou
# au changement des failles, puis tous les 7 jours tant qu'elles durent, et une
# fois au retour a la normale. Etat : artifacts/image-scan-state.
#
# Usage : scan_images.sh [env-file] [--dry-run]
#   --dry-run : affiche le message au lieu de l'envoyer, sans toucher l'etat.
set -euo pipefail

TRIVY_IMAGE="aquasec/trivy:0.61.0"
REMINDER_SECONDS=$((7 * 24 * 3600))
ENV_FILE=".env.target"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -*)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
    *)
      ENV_FILE="$1"
      shift
      ;;
  esac
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ignore_file="$repo_root/security-ignore.txt"
state_file="$repo_root/artifacts/image-scan-state"
[[ "$ENV_FILE" == /* ]] || ENV_FILE="$repo_root/$ENV_FILE"

if ! command -v docker >/dev/null 2>&1; then
  echo "[scan-images] docker indisponible." >&2
  exit 1
fi

docker_args=(--rm -v /var/run/docker.sock:/var/run/docker.sock -v beevarium_trivy_cache:/root/.cache/trivy)
# Code 10 = failles trouvees ; 1 reste reserve aux erreurs de Trivy.
trivy_args=(image --quiet --scanners vuln --severity "HIGH,CRITICAL" --ignore-unfixed --exit-code 10)
# Une ligne par faille (lisible en e-mail, stable pour le calcul de l'etat).
template='{{ range . }}{{ range .Vulnerabilities }}{{ .VulnerabilityID }} {{ .Severity }} {{ .PkgName }} {{ .InstalledVersion }} -> {{ .FixedVersion }}{{ "\n" }}{{ end }}{{ end }}'
trivy_args+=(--format template --template "$template")
if [[ -f "$ignore_file" ]]; then
  docker_args+=(-v "$ignore_file:/security-ignore.txt:ro")
  trivy_args+=(--ignorefile /security-ignore.txt)
fi

report=""
images="$(docker ps --format '{{.Image}}' | sort -u)"
while IFS= read -r image; do
  [[ -z "$image" ]] && continue
  status=0
  output="$(docker run "${docker_args[@]}" "$TRIVY_IMAGE" "${trivy_args[@]}" "$image" 2>&1)" || status=$?
  case "$status" in
    0) ;;
    10) report+="== $image : failles corrigeables ==
$output

" ;;
    *) report+="== $image : scan en echec (code $status) ==
$output

" ;;
  esac
done <<< "$images"

now="$(date +%s)"
previous_hash=""
notified_at=0
if [[ -f "$state_file" ]]; then
  read -r previous_hash notified_at < "$state_file" || true
fi
hash=""
subject=""
body=""
if [[ -n "$report" ]]; then
  hash="$(printf '%s' "$report" | python3 -c 'import hashlib,sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())')"
  if [[ "$hash" != "$previous_hash" || $((now - notified_at)) -ge $REMINDER_SECONDS ]]; then
    subject="[Beevarium] Failles dans les images Docker"
    body="Le scan quotidien (Trivy, HIGH/CRITICAL avec correctif) signale :

$report
Corriger en mettant a jour l'image concernee, ou accepter dans security-ignore.txt avec raison et date de reexamen."
  fi
elif [[ -n "$previous_hash" ]]; then
  subject="[Beevarium] Images Docker : retour a la normale"
  body="Le scan quotidien ne signale plus de faille corrigeable."
fi

if [[ -z "$subject" ]]; then
  [[ "$DRY_RUN" -eq 0 ]] || echo "[scan-images] rien a signaler"
  exit 0
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf '%s' "$body" | python3 "$repo_root/scripts/alert_mail.py" "$ENV_FILE" "$subject" --dry-run
  exit 0
fi

printf '%s' "$body" | python3 "$repo_root/scripts/alert_mail.py" "$ENV_FILE" "$subject"
mkdir -p "$(dirname "$state_file")"
if [[ -n "$hash" ]]; then
  printf '%s %s\n' "$hash" "$now" > "$state_file"
else
  : > "$state_file"
fi
echo "[scan-images] e-mail envoye : $subject"
