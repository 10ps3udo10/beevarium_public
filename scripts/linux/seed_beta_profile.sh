#!/usr/bin/env bash
# Complete le compte de demonstration avec un cheptel realiste via l'API.
# Cree des donnees : a utiliser seulement avec accord explicite.
set -euo pipefail

API_BASE_URL="https://beta.beevarium.fr"
ACCESS_FILE="backend/app/static/app/demo-access.json"
TARGET_TOTAL=25
INTERACTIVE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-base-url) API_BASE_URL="$2"; shift 2 ;;
    --access-file) ACCESS_FILE="$2"; shift 2 ;;
    --target-total) TARGET_TOTAL="$2"; shift 2 ;;
    --interactive) INTERACTIVE=1; shift ;;
    *) echo "Argument inconnu: $1" >&2; exit 1 ;;
  esac
done

API_BASE_URL="${API_BASE_URL%/}"

if [[ "$INTERACTIVE" -eq 1 ]]; then
  read -r -p "Email du profil beta: " email
  read -r -s -p "Mot de passe du profil beta: " password
  printf '\n'
elif [[ -f "$ACCESS_FILE" ]]; then
  email="$(jq -er '.email' "$ACCESS_FILE")"
  password="$(jq -er '.password' "$ACCESS_FILE")"
else
  echo "Fichier d acces demo absent: $ACCESS_FILE (utiliser --interactive)" >&2
  exit 1
fi
login_body="$(jq -cn --arg email "$email" --arg password "$password" '{email:$email,password:$password}')"
token="$(curl -fsS -H 'Content-Type: application/json' -d "$login_body" "$API_BASE_URL/auth/login" | jq -er '.access_token')"
auth_header="Authorization: Bearer $token"

post_json() {
  local path="$1"
  local body="$2"
  curl -fsS -H 'Content-Type: application/json' -H "$auth_header" -d "$body" "$API_BASE_URL$path"
}

put_json() {
  local path="$1"
  local body="$2"
  curl -fsS -X PUT -H 'Content-Type: application/json' -H "$auth_header" -d "$body" "$API_BASE_URL$path"
}

mapfile -t ruchers < <(curl -fsS -H "$auth_header" "$API_BASE_URL/ruchers" | jq -r 'sort_by(.nom) | .[].id')
if [[ "${#ruchers[@]}" -ne 3 ]]; then
  echo "Le profil doit avoir exactement 3 ruchers avant le seed" >&2
  exit 1
fi

type_rows="$(curl -fsS -H "$auth_header" "$API_BASE_URL/references/type-ruche")"
resolve_type() {
  local pattern="$1"
  local fallback="$2"
  jq -er --arg pattern "$pattern" --arg fallback "$fallback" '[.[] | select((.libelle|ascii_downcase) | test($pattern))][0].id // ([.[] | select(.id == $fallback)][0].id // .[0].id)' <<<"$type_rows"
}
fallback_type="$(jq -er '.[0].id' <<<"$type_rows")"
type_dadant10="$(resolve_type 'dadant.*10|dadant10' "$fallback_type")"
type_dadant12="$(resolve_type 'dadant.*12|dadant12' "$type_dadant10")"
type_ruchette="$(resolve_type 'ruchette|nuclei' "$type_dadant10")"

existing="$(curl -fsS -H "$auth_header" "$API_BASE_URL/ruches")"
existing_count="$(jq 'length' <<<"$existing")"
next_index=$((existing_count + 1))

while (( existing_count < TARGET_TOTAL )); do
  slot=$(( (next_index - 1) % 3 ))
  rucher_id="${ruchers[$slot]}"
  type_id="$type_dadant10"
  frames=10
  if (( next_index % 5 == 0 )); then type_id="$type_dadant12"; frames=12; fi
  if (( next_index % 7 == 0 )); then type_id="$type_ruchette"; frames=6; fi
  identifier="BETA-$(printf '%02d' "$next_index")"
  ruche="$(post_json /ruches "$(jq -cn --arg id "$identifier" --arg rucher "$rucher_id" --arg type "$type_id" '{identifiant_personnalise:$id,rucher_id:$rucher,is_at_atelier:false,ref_type_ruche_id:$type,ref_statut_ruche_id:null,reine_annee_marquage:(2022 + ($id|capture("(?<n>[0-9]+)").n|tonumber)%5),reine_race:(if ($id|endswith("5")) then "Noire" else "Buckfast" end),reine_provenance:"Elevage local"}')")"
  ruche_id="$(jq -er '.id' <<<"$ruche")"
  post_json "/ruches/$ruche_id/reines" "$(jq -cn --arg date "$(date -u -d "$((next_index % 18 + 1)) months ago" +%Y-%m-%dT%H:%M:%SZ)" '{date_mise_en_place:$date,origine:"apport_reine_fecondee",race:"Buckfast",provenance:"Elevage local"}')" >/dev/null
  for visit_index in 1 2; do
    visit_date="$(date -u -d "$((visit_index * 23 + next_index % 12)) days ago" +%Y-%m-%dT%H:%M:%SZ)"
    post_json /visites "$(jq -cn --arg ruche "$ruche_id" --argjson frames "$frames" --argjson visit_index "$visit_index" '{ruche_id:$ruche,visite_rucher_id:null,reine_vue:($frames % 2 == 0),presence_ponte:true,etat_couvain:(if $frames > 8 then "normal" else "excellent" end),nombre_cadres_couvain:(if $frames > 8 then 4 else 3 end),nombre_cadres_total:$frames,reserves_nourriture:(if $visit_index == 1 then "correct" else "abondant" end),agressivite:2,note_ruche:(3 + ($frames % 3)),source_saisie:"manuelle",statut_validation:"valide",action_ids:[],interventions:[],mouvements_cadres:[],mouvements_hausses:[]}')" >/dev/null
  done
  next_index=$((next_index + 1))
  existing_count=$((existing_count + 1))
done

echo "Seed beta termine: $existing_count ruches, donnees visites et reines ajoutees."