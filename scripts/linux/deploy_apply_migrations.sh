#!/usr/bin/env bash
# Applique dans l'ordre les migrations de db/migrations non encore enregistrees
# dans schema_migrations (cree le schema initial sur une base vide).
set -euo pipefail

ENV_FILE="${1:-.env.target}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" up -d db_target

for _ in $(seq 1 30); do
  if docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" exec -T db_target sh -lc "pg_isready -U '$POSTGRES_USER' -d '$POSTGRES_DB'" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

users_exists="$(docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" exec -T db_target sh -lc "psql -U '$POSTGRES_USER' -d '$POSTGRES_DB' -tA -c \"SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='users' LIMIT 1;\"")"
if [[ "${users_exists//[[:space:]]/}" != "1" ]]; then
  echo "[deploy] Initialize base schema from db/init"
  while IFS= read -r -d '' sql_file; do
    echo "[init] $(basename "$sql_file")"
    docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" exec -T db_target sh -lc "psql -U '$POSTGRES_USER' -d '$POSTGRES_DB' -v ON_ERROR_STOP=1" < "$sql_file"
  done < <(find db/init -maxdepth 1 -type f -name '*.sql' -print0 | sort -z)
fi

docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" exec -T db_target sh -lc "psql -U '$POSTGRES_USER' -d '$POSTGRES_DB' -v ON_ERROR_STOP=1" <<'SQL'
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
SQL

if [[ -d db/migrations ]]; then
  mapfile -t migrations < <(find db/migrations -maxdepth 1 -type f -name '*.sql' -print | sort)
  for migration in "${migrations[@]}"; do
    version="$(basename "$migration" .sql)"
    already="$(docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" exec -T db_target sh -lc "psql -U '$POSTGRES_USER' -d '$POSTGRES_DB' -tA -c \"SELECT 1 FROM schema_migrations WHERE version='${version}' LIMIT 1;\"")"
    if [[ "${already//[[:space:]]/}" == "1" ]]; then
      echo "[skip] $(basename "$migration")"
      continue
    fi

    echo "[apply] $(basename "$migration")"
    docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" exec -T db_target sh -lc "psql -U '$POSTGRES_USER' -d '$POSTGRES_DB' -v ON_ERROR_STOP=1" < "$migration"
    docker compose -f docker-compose.target.yml --env-file "$ENV_FILE" exec -T db_target sh -lc "psql -U '$POSTGRES_USER' -d '$POSTGRES_DB' -v ON_ERROR_STOP=1 -c \"INSERT INTO schema_migrations(version) VALUES ('${version}');\""
  done
fi

echo "[deploy] Target migrations done"
