#!/usr/bin/env bash
# Verifie la syntaxe des fichiers du client web.
# Une erreur de syntaxe dans app.js ou un module de js/ rend l application entierement inutilisable
# sans qu aucun test d API ne le detecte.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

static_dir="backend/app/static/app"
failures=0

echo "[client] Verification de la syntaxe JavaScript"
if command -v node >/dev/null 2>&1; then
  runner=(node --check)
  for file in "$static_dir"/*.js "$static_dir"/js/*.js; do
    if "${runner[@]}" "$file"; then
      echo "  ok   ${file#"$static_dir"/}"
    else
      echo "  ECHEC $(basename "$file")" >&2
      failures=$((failures + 1))
    fi
  done
elif command -v docker >/dev/null 2>&1; then
  # Node 22 reconnait seul la syntaxe des modules ES (import/export).
  for file in "$static_dir"/*.js "$static_dir"/js/*.js; do
    if docker run --rm -v "$repo_root/$static_dir:/w" -w /w node:22-alpine \
      node --check "${file#"$static_dir"/}"; then
      echo "  ok   ${file#"$static_dir"/}"
    else
      echo "  ECHEC $(basename "$file")" >&2
      failures=$((failures + 1))
    fi
  done
else
  echo "[client] Ni node ni docker disponibles, verification impossible" >&2
  exit 1
fi

echo "[client] Verification des fichiers JSON"
for file in "$static_dir"/*.json; do
  [[ -e "$file" ]] || continue
  if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$file"; then
    echo "  ok   $(basename "$file")"
  else
    echo "  ECHEC $(basename "$file")" >&2
    failures=$((failures + 1))
  fi
done

if (( failures > 0 )); then
  echo "[client] $failures fichier(s) invalide(s)" >&2
  exit 1
fi

echo "[client] Tous les fichiers client sont valides"
