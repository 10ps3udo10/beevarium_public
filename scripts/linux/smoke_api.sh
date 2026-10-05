#!/usr/bin/env bash
# Smoke API : inscription, connexion, ruchers, ruches, visites, revocation de
# session. Cree des donnees : jamais sur la beta.
set -euo pipefail

API_BASE_URL="http://localhost:8000"
STRICT_REVOCATION=0
OUTPUT_JSON_PATH=""
SKIP_WAIT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-base-url)
      API_BASE_URL="$2"
      shift 2
      ;;
    --strict-revocation)
      STRICT_REVOCATION=1
      shift
      ;;
    --output-json-path)
      OUTPUT_JSON_PATH="$2"
      shift 2
      ;;
    --skip-wait)
      SKIP_WAIT=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

API_BASE_URL="${API_BASE_URL%/}"

if [[ "$SKIP_WAIT" -eq 0 ]]; then
  scripts/linux/wait_for_api.sh --api-base-url "$API_BASE_URL"
fi

email="smoke$RANDOM$RANDOM@example.com"
password="motdepasse123"

json_post() {
  local path="$1"
  local body="$2"
  local token="${3:-}"
  if [[ -n "$token" ]]; then
    curl -fsS -X POST "${API_BASE_URL}${path}" -H "Authorization: Bearer $token" -H 'Content-Type: application/json' -d "$body"
  else
    curl -fsS -X POST "${API_BASE_URL}${path}" -H 'Content-Type: application/json' -d "$body"
  fi
}

json_get() {
  local path="$1"
  local token="${2:-}"
  if [[ -n "$token" ]]; then
    curl -fsS "${API_BASE_URL}${path}" -H "Authorization: Bearer $token"
  else
    curl -fsS "${API_BASE_URL}${path}"
  fi
}

health="$(json_get /health)"
register_payload="$(python3 - <<PY
import json
print(json.dumps({
  'email': '$email',
  'prenom': 'Smoke',
  'password': '$password',
  'is_premium': True
}))
PY
)"
register="$(json_post /auth/register "$register_payload")"
token="$(python3 - <<PY
import json
print(json.loads('''$register''')['access_token'])
PY
)"

me="$(json_get /auth/me "$token")"
me_email="$(python3 - <<PY
import json
print(json.loads('''$me''')['email'])
PY
)"
if [[ "$me_email" != "$email" ]]; then
  echo "auth/me mismatch" >&2
  exit 1
fi

rucher_payload='{"nom":"Rucher Smoke","latitude":46.8,"longitude":4.8,"type_terrain":"plaine","statut_activite":"actif","statut_peuplement":"peuple"}'
rucher="$(json_post /ruchers "$rucher_payload" "$token")"
rucher_id="$(python3 - <<PY
import json
print(json.loads('''$rucher''')['id'])
PY
)"

ruche_payload="$(python3 - <<PY
import json
print(json.dumps({
  'identifiant_personnalise':'SMOKE-1',
  'rucher_id':'$rucher_id',
  'is_at_atelier':False,
  'ref_type_ruche_id':None,
  'ref_statut_ruche_id':None,
  'reine_annee_marquage':2026,
  'reine_race':'Buckfast',
  'reine_provenance':'Local'
}))
PY
)"
ruche="$(json_post /ruches "$ruche_payload" "$token")"
ruche_id="$(python3 - <<PY
import json
print(json.loads('''$ruche''')['id'])
PY
)"

visite_rucher_payload="$(python3 - <<PY
import json
print(json.dumps({'rucher_id':'$rucher_id','note_meteo':'ensoleille','impression_generale':'Activite reguliere','note_globale':4}))
PY
)"
visite_rucher="$(json_post /visites-rucher "$visite_rucher_payload" "$token")"
visite_rucher_id="$(python3 - <<PY
import json
print(json.loads('''$visite_rucher''')['id'])
PY
)"

visite_payload="$(python3 - <<PY
import json
print(json.dumps({
  'ruche_id':'$ruche_id',
  'visite_rucher_id':'$visite_rucher_id',
  'reine_vue':True,
  'presence_ponte':True,
  'etat_couvain':'normal',
  'nombre_cadres_couvain':4,
  'reserves_nourriture':'correct',
  'agressivite':2,
  'note_ruche':4,
  'nombre_cadres_total':10,
  'source_saisie':'manuelle',
  'statut_validation':'valide',
  'action_ids':[],
  'interventions':[],
  'mouvements_cadres':[],
  'mouvements_hausses':[]
}))
PY
)"
json_post /visites "$visite_payload" "$token" >/dev/null

today="$(date +%F)"
json_get "/visites/synthese/periode?start_date=${today}&end_date=${today}&rucher_id=${rucher_id}" "$token" >/dev/null

ia_payload="$(python3 - <<PY
import json
print(json.dumps({
  'ruche_id':'$ruche_id',
  'transcription':'reine vue, ponte presente, etat couvain normal',
  'audio_reference':'audio/smoke.wav',
  'save_as_draft':True
}))
PY
)"
json_post /ia-vocale/analyser-visite "$ia_payload" "$token" >/dev/null

free_email="smokefree$RANDOM$RANDOM@example.com"
free_register="$(python3 - <<PY
import json
print(json.dumps({'email':'$free_email','prenom':'SmokeFree','password':'$password','is_premium':False}))
PY
)"
free_resp="$(json_post /auth/register "$free_register")"
free_token="$(python3 - <<PY
import json
print(json.loads('''$free_resp''')['access_token'])
PY
)"

for i in 1 2; do
  if [[ "$i" == "1" ]]; then
    payload='{"nom":"Rucher Free 1","latitude":46.0,"longitude":4.0,"type_terrain":"plaine","statut_activite":"actif","statut_peuplement":"peuple"}'
  else
    payload='{"nom":"Rucher Free 2","latitude":47.0,"longitude":5.0,"type_terrain":"plaine","statut_activite":"actif","statut_peuplement":"peuple"}'
  fi
  json_post /ruchers "$payload" "$free_token" >/dev/null
done

third_payload='{"nom":"Rucher Free 3","latitude":48.0,"longitude":6.0,"type_terrain":"plaine","statut_activite":"actif","statut_peuplement":"peuple"}'
third_status="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${API_BASE_URL}/ruchers" -H "Authorization: Bearer $free_token" -H 'Content-Type: application/json' -d "$third_payload")"
[[ "$third_status" == "403" ]] || { echo "Expected 403 on free 3rd rucher" >&2; exit 1; }

logout_status="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${API_BASE_URL}/auth/logout" -H "Authorization: Bearer $token")"
[[ "$logout_status" == "200" ]] || { echo "Logout failed" >&2; exit 1; }

if [[ "$STRICT_REVOCATION" -eq 1 ]]; then
  rev_status="$(curl -s -o /dev/null -w '%{http_code}' "${API_BASE_URL}/auth/me" -H "Authorization: Bearer $token")"
  [[ "$rev_status" == "401" ]] || { echo "Expected 401 after logout" >&2; exit 1; }
fi

result_json="$(python3 - <<PY
import json
from datetime import datetime, timezone
print(json.dumps({
  'status':'ok',
  'api_base_url':'$API_BASE_URL',
  'strict_revocation': bool($STRICT_REVOCATION),
  'generated_at': datetime.now(timezone.utc).isoformat()
}, indent=2))
PY
)"

if [[ -n "$OUTPUT_JSON_PATH" ]]; then
  mkdir -p "$(dirname "$OUTPUT_JSON_PATH")"
  printf '%s\n' "$result_json" > "$OUTPUT_JSON_PATH"
  echo "[smoke] JSON written to $OUTPUT_JSON_PATH"
fi

echo "[smoke] Smoke API completed successfully."
printf '%s\n' "$result_json"
