#!/usr/bin/env bash
# Demarre la supervision et rappelle comment y acceder.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

docker compose -f docker-compose.monitoring.yml up -d

echo
echo "[supervision] Services demarres."
docker compose -f docker-compose.monitoring.yml ps --format "  {{.Name}}\t{{.Status}}"

cat <<'INFO'

Aucun service n'est accessible depuis Internet. Pour ouvrir les interfaces,
creer un tunnel SSH depuis votre poste :

  ssh -N -L 19999:127.0.0.1:19999 -L 3001:127.0.0.1:3001 beevarium@<IP_VPS>

Puis, dans le navigateur :
  Netdata      http://localhost:19999   metriques temps reel
  Uptime Kuma  http://localhost:3001    disponibilite et alertes
INFO
