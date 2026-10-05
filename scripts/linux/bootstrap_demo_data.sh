#!/usr/bin/env bash
# Cree un compte de demonstration local (ruchers, ruches, Atelier, reines, visites)
# et ecrit ses identifiants dans un fichier ignore par Git. Local uniquement.
set -euo pipefail

API_BASE_URL="http://localhost:8000"
EMAIL=""
PASSWORD="motdepasse123"
PRENOM="Demo"
PREMIUM=0
OUTPUT_JSON_PATH="artifacts/demo-access.json"
CLIENT_ACCESS_FILE_PATH="backend/app/static/app/demo-access.json"
CONTAINER_NAME="beevarium_api"

usage() {
  cat <<'EOF'
Usage: scripts/linux/bootstrap_demo_data.sh [options]
  --api-base-url URL
  --email EMAIL
  --password PASSWORD
  --prenom NAME
  --premium
  --output-json-path PATH
  --client-access-file-path PATH
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-base-url) API_BASE_URL="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --prenom) PRENOM="$2"; shift 2 ;;
    --premium) PREMIUM=1; shift ;;
    --output-json-path) OUTPUT_JSON_PATH="$2"; shift 2 ;;
    --client-access-file-path) CLIENT_ACCESS_FILE_PATH="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Argument inconnu: $1" >&2; usage >&2; exit 1 ;;
  esac
done

API_BASE_URL="${API_BASE_URL%/}"
if [[ -z "$EMAIL" ]]; then
  EMAIL="demo$(date -u +%Y%m%d%H%M%S)@example.com"
fi

wait_for_api() {
  scripts/linux/wait_for_api.sh --api-base-url "$API_BASE_URL"
}

post_json() {
  local path="$1"
  local body="$2"
  local auth_header="${3:-}"
  if [[ -n "$auth_header" ]]; then
    curl -fsS --retry 2 --retry-delay 1 -H "Content-Type: application/json" -H "$auth_header" \
      -d "$body" "$API_BASE_URL$path"
  else
    curl -fsS --retry 2 --retry-delay 1 -H "Content-Type: application/json" \
      -d "$body" "$API_BASE_URL$path"
  fi
}

wait_for_api

echo "[bootstrap_demo] Initialisation du compte demo: $EMAIL"
register_body="$(jq -cn --arg email "$EMAIL" --arg prenom "$PRENOM" --arg password "$PASSWORD" --argjson premium "$PREMIUM" '{email:$email, prenom:$prenom, password:$password, is_premium:($premium == 1)}')"
if ! auth_response="$(post_json /auth/register "$register_body" 2>/dev/null)"; then
  echo "[bootstrap_demo] Compte deja existant ou non-cree, tentative login"
  login_body="$(jq -cn --arg email "$EMAIL" --arg password "$PASSWORD" '{email:$email, password:$password}')"
  auth_response="$(post_json /auth/login "$login_body")"
else
  echo "[bootstrap_demo] Compte cree"
fi

token="$(jq -er '.access_token' <<<"$auth_response")"
auth_header="Authorization: Bearer $token"

rucher_ids=()
for rucher_data in \
  '{"nom":"Rucher Demo Nord","latitude":45.76,"longitude":4.84,"type_terrain":"plaine","statut_activite":"actif","statut_peuplement":"peuple"}' \
  '{"nom":"Rucher Demo Sud","latitude":45.70,"longitude":4.85,"type_terrain":"colline","statut_activite":"actif","statut_peuplement":"peuple"}' \
  '{"nom":"Rucher Demo Ouest","latitude":45.74,"longitude":4.80,"type_terrain":"foret","statut_activite":"actif","statut_peuplement":"peuple"}'; do
  rucher="$(post_json /ruchers "$rucher_data" "$auth_header")"
  rucher_ids+=("$(jq -er '.id' <<<"$rucher")")
done
rucher_id="${rucher_ids[0]}"

ruche_ids=()
for rucher_index in 0 1 2; do
  for hive_index in 1 2; do
    ruche="$(post_json /ruches "$(jq -cn --arg rucher_id "${rucher_ids[$rucher_index]}" --arg identifiant "DEMO-$hive_index" '{identifiant_personnalise:$identifiant,rucher_id:$rucher_id,is_at_atelier:false,ref_type_ruche_id:null,ref_statut_ruche_id:null,reine_annee_marquage:2026,reine_race:(if $identifiant == "DEMO-1" then "Buckfast" else "Noire" end),reine_provenance:"Local"}')" "$auth_header")"
    ruche_id="$(jq -er '.id' <<<"$ruche")"
    ruche_ids+=("$ruche_id")
    post_json /ruches/"$ruche_id"/reines "$(jq -cn --arg date "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg origine "apport_reine_fecondee" '{date_mise_en_place:$date,origine:$origine,race:"Buckfast",provenance:"Elevage local"}')" "$auth_header" >/dev/null
    visite_rucher="$(post_json /visites-rucher "$(jq -cn --arg rucher_id "${rucher_ids[$rucher_index]}" '{rucher_id:$rucher_id,note_meteo:"ensoleille",impression_generale:"Observation demo",note_globale:4}')" "$auth_header")"
    visite_rucher_id="$(jq -er '.id' <<<"$visite_rucher")"
    post_json /visites "$(jq -cn --arg ruche_id "$ruche_id" --arg visite_rucher_id "$visite_rucher_id" '{ruche_id:$ruche_id,visite_rucher_id:$visite_rucher_id,reine_vue:true,presence_ponte:true,etat_couvain:"normal",nombre_cadres_couvain:(if $ruche_id then 4 else 4 end),reserves_nourriture:"correct",agressivite:2,note_ruche:4,nombre_cadres_total:10,source_saisie:"manuelle",statut_validation:"valide",action_ids:[],interventions:[],mouvements_cadres:[],mouvements_hausses:[]}')" "$auth_header" >/dev/null
  done
done

atelier_ruche_ids=()
for atelier_index in 1 2; do
  atelier_ruche="$(post_json /ruches "$(jq -cn --arg identifiant "ATELIER-$atelier_index" '{identifiant_personnalise:$identifiant,rucher_id:null,is_at_atelier:true,ref_type_ruche_id:null,ref_statut_ruche_id:null,reine_annee_marquage:2025,reine_race:"Buckfast",reine_provenance:"Reserve atelier"}')" "$auth_header")"
  atelier_ruche_ids+=("$(jq -er '.id' <<<"$atelier_ruche")")
done

report="$(jq -cn --arg status ok --arg api_base_url "$API_BASE_URL" --arg email "$EMAIL" --arg password "$PASSWORD" --arg token "$token" --argjson premium "$PREMIUM" --arg rucher_id "$rucher_id" --argjson rucher_ids "$(printf '%s\n' "${rucher_ids[@]}" | jq -R . | jq -s .)" --argjson ruche_ids "$(printf '%s\n' "${ruche_ids[@]}" | jq -R . | jq -s .)" --argjson atelier_ruche_ids "$(printf '%s\n' "${atelier_ruche_ids[@]}" | jq -R . | jq -s .)" '{status:$status,api_base_url:$api_base_url,email:$email,password:$password,token:$token,premium:($premium == 1),rucher_id:$rucher_id,rucher_ids:$rucher_ids,ruche_ids:$ruche_ids,atelier_ruche_ids:$atelier_ruche_ids,generated_at:(now|todateiso8601)}')"
mkdir -p "$(dirname "$OUTPUT_JSON_PATH")" "$(dirname "$CLIENT_ACCESS_FILE_PATH")"
printf '%s\n' "$report" > "$OUTPUT_JSON_PATH"
printf '%s\n' "$report" > "$CLIENT_ACCESS_FILE_PATH"

if ! docker cp "$CLIENT_ACCESS_FILE_PATH" "$CONTAINER_NAME:/app/app/static/app/demo-access.json" >/dev/null 2>&1; then
  echo "[bootstrap_demo] Copie conteneur ignoree: le fichier est probablement monte par Docker"
fi
echo "[bootstrap_demo] Fichier client publie: $CLIENT_ACCESS_FILE_PATH"
echo "[bootstrap_demo] Fichier client copie dans le conteneur: $CONTAINER_NAME:/app/app/static/app/demo-access.json"
echo "[bootstrap_demo] Donnees demo creees. Rapport: $OUTPUT_JSON_PATH"
printf '%s\n' "$report"
