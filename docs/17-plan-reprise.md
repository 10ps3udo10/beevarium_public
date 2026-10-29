# Plan de reprise d'activite (R1)

Procedure de remise en service de Beevarium apres sinistre, objectifs RTO/RPO
et compte rendu des exercices. Complete `docs/06-exploitation.md` (sauvegardes,
deploiement, rollback) et `docs/16-analyse-risques.md` (risques R1, R5, R10).
Aucun secret ne figure ici : seuls les emplacements sont decrits.

## 1. Objectifs

| Mesure | Cible | Justification | Mesure reelle |
|---|---|---|---|
| RPO (perte de donnees maximale) | 24 h | Sauvegarde quotidienne a 03h15 UTC, copie hors site a 03h45 UTC. Les visites saisies hors ligne se resynchronisent a la reconnexion | Non mesure sur VPS ; la copie hors site date de 24 h au plus par construction |
| RTO (remise en service) | 4 h (proposition, a valider par le concepteur) | VPS neuf, Docker, restauration, release, DNS | Repetition locale : 56 s de restauration technique (voir section 6) ; exercice VPS : a faire |

Le RTO reel sur VPS sera domine par : provisionnement, construction de l'image,
propagation DNS et delivrance du certificat TLS, non mesurables en local.

## 2. Scenarios

| Scenario | Symptome | Reponse |
|---|---|---|
| A. Perte totale du VPS | SSH et `/health` injoignables, panne OVH, compromission | Procedure complete section 4 (VPS vierge) |
| B. Base corrompue ou donnees detruites | API en erreur, tables vides ou incoherentes, VPS sain | Etapes 7 a 11 de la section 4 sur le VPS existant, avec `--force` ; sauvegarde de l'etat actuel d'abord (`deploy_backup_db.sh`) |
| C. Mauvaise release | Regression apres deploiement | `deploy_rollback.sh .env.target` (`docs/06`) ; si une migration est en cause, restaurer la sauvegarde prise avant le deploiement (scenario B) |

## 3. Prerequis hors VPS (a verifier avant tout sinistre)

Ces elements ne doivent exister **que** hors du VPS ou etre reconstructibles.
Si l'un manque, la reprise est impossible ou fortement allongee.

| Element | Ou le trouver | Remarque |
|---|---|---|
| Phrase de chiffrement des sauvegardes (`BACKUP_ENCRYPTION_PASSPHRASE`) | Gestionnaire de mots de passe du concepteur | Perdue = archives hors site definitivement illisibles |
| Configuration rclone (cle d'acces du stockage objet) | Gestionnaire de mots de passe ; sinon recreable depuis la console du fournisseur (nouvelle cle d'acces au conteneur `BACKUP_OFFSITE_REMOTE`) | `~/bin/rclone config`, voir `docs/06` section 10 |
| Cle SSH d'administration | Poste du concepteur (`~/.ssh`) ; la cle publique est declaree dans la console OVH et dans la configuration Ansible | Une cle de secours hors poste est recommandee |
| Contenu de `.env.target` (JWT, SMTP, Stripe le cas echeant) | Gestionnaire de mots de passe (copie a jour a chaque changement) | `.env.target.example` donne la liste des variables. Un nouveau `JWT_SECRET_KEY` fonctionne mais deconnecte tous les utilisateurs |
| Acces console OVH, registrar DNS | Compte du concepteur (2FA) | Necessaire pour creer le VPS et changer le DNS |
| Depot Git prive | GitHub, cle de deploiement ou acces du concepteur | Contient scripts, migrations, Caddyfile de reference |

Verification trimestrielle : `rclone lsf` du conteneur depuis le poste, ouverture
du gestionnaire de mots de passe, `openssl` disponible.

## 4. Procedure pas a pas : VPS vierge Debian 12

Chronometrer chaque etape (heure de debut et de fin dans le compte rendu).

1. **Creer le VPS** (console OVH, Debian 12, cle SSH du concepteur). Noter l'IP.
2. **Provisionner** (utilisateur `beevarium`, Docker, UFW 22/80/443, SSH par cle
   uniquement, Caddy, timers) : lancer la configuration Ansible
   `ansible/vps.yml` (en cours d'ecriture par le chantier R14 ; verifier son
   etat avant l'exercice). Alternative manuelle courte, en root une seule fois :
   creer l'utilisateur `beevarium` (sudo), copier sa cle SSH, desactiver le mot de
   passe SSH, `apt install docker.io docker-compose-plugin git caddy rclone openssl ufw`,
   `ufw allow 22,80,443/tcp && ufw enable`, `loginctl enable-linger beevarium`.
3. **Cloner** : `git clone <depot prive> ~/app && cd ~/app && git fetch --tags`
   puis `git checkout <dernier tag deploye>` (tag indique par `suivi-projet.md`
   ou le journal `artifacts/deploy-logs/`).
4. **Restaurer `.env.target`** depuis le gestionnaire de mots de passe
   (`chmod 600`). Verifier `STACK_NAME`, `TARGET_API_PORT=18000`,
   `BACKUP_OFFSITE_REMOTE` et `BACKUP_ENCRYPTION_PASSPHRASE`.
5. **Configurer rclone** (`~/bin/rclone config`, ou copier `rclone.conf` du
   gestionnaire) ; verifier `~/bin/rclone lsf "$BACKUP_OFFSITE_REMOTE" | sort | tail -3`.
6. **Recuperer la derniere archive chiffree** :
   ```bash
   set -a; source .env.target; set +a
   mkdir -p artifacts/backups/chiffres
   derniere="$(~/bin/rclone lsf "$BACKUP_OFFSITE_REMOTE" | sort | tail -1)"
   ~/bin/rclone copyto "$BACKUP_OFFSITE_REMOTE/$derniere" "artifacts/backups/chiffres/$derniere"
   ```
   Noter l'horodatage de l'archive : RPO reel = heure du sinistre - cet horodatage.
7. **Restaurer, migrer, demarrer** en une commande (dechiffrement, base,
   migrations, release, `/health`, comptages, durees par etape) :
   ```bash
   CONFIRM_BETA_RESTORE=oui bash scripts/linux/pra_restore.sh .env.target \
     "artifacts/backups/chiffres/$derniere" --tag <tag>
   ```
   `CONFIRM_BETA_RESTORE=oui` est requis car `.env.target` de la beta designe le
   port 18000 : c'est voulu sur un VPS de remplacement, jamais sur la beta saine.
   Le script refuse une base deja peuplee sans `--force`.
8. **Caddy** : reprendre le Caddyfile de reference (configuration Ansible, sinon
   `docs/06` : `beta.beevarium.fr` vers `127.0.0.1:18000`, `beevarium.fr` et
   `www` vers `/var/www/beevarium`), puis `sudo systemctl reload caddy`.
   Page statique : `bash scripts/linux/deploy_site.sh`.
9. **DNS** : avant le sinistre, abaisser le TTL des enregistrements `A` de
   `beta`, `beevarium.fr` et `www` a 300 s si l'on veut une bascule rapide
   (sinon la valeur actuelle s'applique : la relever et la noter ici). Pendant la
   reprise : pointer les `A` (et `AAAA` si present) vers la nouvelle IP. Les
   enregistrements SPF/DKIM/DMARC referencent l'IP d'envoi : les verifier
   (section « Enregistrements DNS » de `docs/06`). Attendre la propagation et l'emission du certificat par
   Caddy (`journalctl -u caddy`).
10. **Verifications** :
    - `curl -fsS https://beta.beevarium.fr/health` : `status ok`, `database connected`, version attendue ;
    - connexion avec le compte de test de demonstration (identifiants dans `CLAUDE.local.md`, hors depot) dans l'application, ouverture d'un rucher et d'une ruche ;
    - comptages affiches par `pra_restore.sh` compares a ceux du dernier controle
      (`artifacts/backups/last-restore-check.json` de l'ancien VPS si disponible, sinon dernier compte connu dans le compte rendu precedent) ;
    - un e-mail de test (`send_test_email.sh`) et le watchdog (`install_watchdog.sh`).
11. **Rearmer l'exploitation** : `bash scripts/linux/install_backup_timers.sh`,
    premiere sauvegarde manuelle (`backup_daily.sh`), envoi hors site
    (`backup_offsite.sh`), puis `backup_offsite_verify.sh`. Prevenir les testeurs
    si des donnees ont ete perdues (processus `docs/15-incidents.md`).
12. **Consigner** les heures et ecarts dans la section 7.

Scenario B (base seule) : sauter 1 a 5 et 8 a 9 ; ajouter `--force` a l'etape 7
apres `deploy_backup_db.sh .env.target` (sauvegarde de l'etat actuel, meme
abime). L'API n'est pas arretee avant la restauration : l'arreter avant
(`docker compose -f docker-compose.target.yml --env-file .env.target stop api_target`)
pour qu'aucune ecriture n'arrive pendant le remplacement du schema.

## 5. Repetition locale et exercice reel

Repetition locale (sans VPS, sans cout) : creer une stack jetable avec un env
file hors Git (`STACK_NAME=pra_rehearsal`, ports libres, secrets aleatoires),
produire un dump `pg_dump --no-owner --no-acl | gzip`, lancer
`pra_restore.sh <env> <dump> --tag essai --expect "users|ruchers|ruches|visites"`,
puis `docker compose ... down -v` et suppression de l'image et de l'env file.

Exercice reel (a declencher par le concepteur) : voir « Reste a faire » du
compte rendu ci-dessous. A refaire chaque trimestre.

## 6. Tableau RTO/RPO mesure

| Etape | Repetition locale (mesuree) | Exercice VPS |
|---|---|---|
| Creation du VPS et provisionnement (etapes 1-2) | non applicable | a mesurer |
| Clone, `.env.target`, rclone (3-5) | non applicable | a mesurer |
| Telechargement hors site (6) | non applicable (15 Mo) | a mesurer |
| Dechiffrement + verification gzip | 1 s | a mesurer |
| Demarrage de la base (volume neuf, schema d'init) | 11 s | a mesurer |
| Restauration du dump | 9 s | a mesurer |
| Migrations (25 migrations, toutes deja enregistrees) | 13 s | a mesurer |
| Build de l'image, demarrage API, `/health` | 20 s (cache Docker chaud) | a mesurer (build a froid : pull + pip) |
| Controles | 2 s | a mesurer |
| **Total restauration technique** | **56 s** | a mesurer |
| Caddy, DNS, TLS (8-9) | non applicable | a mesurer |
| **RTO total** | non applicable | cible 4 h |
| **RPO** | non applicable | cible 24 h |

## 7. Compte rendu d'exercice

Format de `docs/15-incidents.md`.

### PRA-2026-10-28-1 : repetition locale chronometree (pas d'exercice VPS)

- Gravite : G4 (exercice, aucun utilisateur touche)
- Detection : 2026-10-28, preparation de l'etape R1
- Resolution : meme jour ; duree de la restauration technique : 56 s
- Versions : application 1.37.0 (`/health` de la stack restauree)

**Impact** : aucun. Stack jetable `pra_rehearsal` (ports 18090/18091), stack
locale et beta non touchees ; tout a ete supprime a la fin.

**Chronologie** (mesures reelles) : dump `pg_dump --no-owner --no-acl | gzip` de
la base locale en 10 s, 15,4 Mo compresse ; chiffre en AES-256 avec la
commande de `backup_offsite.sh`. Puis `pra_restore.sh` sur archive chiffree :
dechiffrement 1 s, base 11 s, restauration 9 s, migrations 13 s, release et
`/health` 20 s, controles 2 s, **total 56 s**. Comptages source et restaure
identiques : users 7212, ruchers 5192, ruches 7224, visites_ruche 4346. Controles
negatifs : env file de la beta refuse (port 18000, puis `STACK_NAME=beevarium`) ;
base peuplee refusee sans `--force` ; mauvaise phrase de chiffrement refusee.

**Limites de la mesure** : base locale (donnees de charge, pas de donnees de
testeurs) ; la base locale n'a pas de table `schema_migrations`, elle a donc ete
ajoutee au dump avec les 25 migrations pour reproduire une sauvegarde de
production (une sauvegarde en retard sur les migrations n'a pas ete rejouee) ;
cache Docker chaud ; reseau, rclone, DNS, TLS et provisionnement non mesures.

**Cause racine des ecarts trouves** :
1. Sur un volume vide, `pg_isready` repond pendant le serveur temporaire de
   `docker-entrypoint-initdb.d`, qui s'arrete ensuite : `psql` echouait avec
   « the database system is shutting down » (premiere tentative de l'exercice).
   Aurait fait echouer `deploy_apply_migrations.sh` sur un VPS vierge.
2. `deploy_apply_migrations.sh` utilisait `mapfile`, absent du bash 3.2 de macOS.
3. Le volume neuf est deja initialise par `db/init` : un dump ne s'y applique
   pas tel quel (tables existantes). Le schema `public` est donc recree vide
   avant la restauration (`pra_restore.sh`). L'ancienne commande de `docs/06`
   (`gunzip | psql`) echouerait sur une stack neuve.

**Correction** : `pg_isready -h 127.0.0.1` dans les deux scripts, boucle
portable a la place de `mapfile`, `pra_restore.sh` (nouveau).

**Actions** :

| Action | Responsable | Echeance | Statut |
|---|---|---|---|
| Valider RTO 4 h / RPO 24 h | Concepteur | Avant l'exercice VPS | A faire |
| Exercice sur VPS vierge (section 4), mesures dans la colonne « Exercice VPS » | Concepteur | A fixer | A faire |
| Verifier que `ansible/vps.yml` (R14) couvre l'etape 2 | Concepteur | Avant l'exercice | A faire |
| Copie hors ligne des prerequis (section 3), cle SSH de secours | Concepteur | A fixer | A faire |
| Abaisser/noter le TTL DNS | Concepteur | Avant l'exercice | A faire |
| Rejouer le test sur une sauvegarde reelle de la beta (retard de migrations) | Concepteur | Exercice VPS | A faire |

**Lecons** : la restauration technique est courte (moins d'une minute pour
15 Mo) ; le RTO reel dependra du provisionnement, du DNS et de la disponibilite
de la phrase de chiffrement, pas de la base.

### Exercice VPS vierge : a faire

Reprendre le modele de `docs/15-incidents.md` (heures de debut/fin par etape de
la section 4, RPO reel, ecarts, actions).
