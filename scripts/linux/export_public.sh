#!/usr/bin/env bash
# Prepare une copie publique du depot, sans historique Git (decision D5).
# Copie les fichiers suivis et nouveaux non ignores, retire les fichiers propres
# a l'exploitation privee, bloque si une information sensible est detectee, puis
# cree un depot local a un seul commit. N'envoie rien : la commande de push est
# affichee et reste a lancer a la main, apres relecture.
set -euo pipefail

DEST="${1:-../beevarium_public_export}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

# Fichiers lies au compte de demonstration de la beta privee.
PRIVATE_FILES=(
  "scripts/seed_showcase_test_account.py"
)

if [[ -e "$DEST" ]]; then
  echo "[export] $DEST existe deja : le supprimer ou choisir un autre dossier." >&2
  exit 1
fi
mkdir -p "$DEST"

git ls-files --cached --others --exclude-standard -z \
  | while IFS= read -r -d '' file; do
      [[ -f "$file" ]] || continue
      for private in "${PRIVATE_FILES[@]}"; do
        [[ "$file" == "$private" ]] && continue 2
      done
      mkdir -p "$DEST/$(dirname "$file")"
      cp -p "$file" "$DEST/$file"
    done

# Motifs interdits : IP du serveur, comptes reels, cles privees, secrets en clair.
patterns=(
  '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}'
  'test@beevarium\.com'
  '@icloud\.|@gmail\.|@hotmail\.|@orange\.fr'
  'BEGIN [A-Z ]*PRIVATE KEY'
  '(JWT_SECRET_KEY|POSTGRES_PASSWORD|SMTP_PASSWORD|BACKUP_ENCRYPTION_PASSPHRASE)=[^c$"<]'
)
found=0
for pattern in "${patterns[@]}"; do
  # 127.0.0.1 et 0.0.0.0 sont des adresses locales legitimes.
  if matches="$(grep -rnIE "$pattern" "$DEST" | grep -vE '127\.0\.0\.1|0\.0\.0\.0|172\.1[0-9]\.0\.' || true)"; [[ -n "$matches" ]]; then
    echo "[export] Motif sensible detecte ($pattern) :" >&2
    echo "$matches" | head -10 >&2
    found=1
  fi
done
if [[ "$found" -ne 0 ]]; then
  echo "[export] Export bloque : corriger les fichiers puis relancer." >&2
  exit 1
fi

cd "$DEST"
git init -q -b main
git add -A
git -c user.name="Beevarium" -c user.email="noreply@beevarium.fr" commit -q -m "Beevarium : etat public du projet"
echo "[export] Depot public pret dans $DEST ($(git ls-files | wc -l | tr -d ' ') fichiers, 1 commit)."
echo "[export] Relire puis, avec l'accord du concepteur :"
echo "  cd $DEST && git remote add origin git@github.com:10ps3udo10/beevarium_public.git && git push -u origin main"
