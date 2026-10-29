# Inventaire des actifs (R13, premiere moitie)

Etat au 2026-10-28. Registre des actifs numeriques de Beevarium. **Ne contient aucun
identifiant, secret, adresse IP ni adresse e-mail personnelle** : seules les natures de secrets
et leurs emplacements sont listees. L'audit d'accessibilite (seconde moitie de R13) est traite
separement.

Conventions :

- **Criticite** : renvoi aux besoins D/I/C/T (1 a 4) de `docs/16-analyse-risques.md` §1. Faible = 1-2, Moyenne = 3, Forte = 4 sur au moins une dimension, ou support d'une valeur forte.
- **Responsable** : le concepteur (seul administrateur), sauf mention.
- **Verifie le** : date de la derniere verification **dans le depot** (code, scripts, documentation). Sans autre mention, l'etat reel du VPS et des comptes externes n'a **pas** ete reverifie (pas d'acces SSH ni de console fournisseur) ; ces points sont listes au §10.

## 1. Materiel et hebergement

| Actif | Description | Criticite | Responsable | Verifie le | Source |
|---|---|---|---|---|---|
| VPS OVH | Debian 12 ; API, PostgreSQL 16, Caddy, beta et app-dev ; offre et taille non documentees | Forte (toutes les valeurs metier) | Concepteur | 2026-10-28 (doc) | ADR 0004, `docs/06`, `docs/16` §2 |
| Poste du concepteur | Developpement, cle SSH, depot prive, copie locale de `.env.target`, cle de chiffrement des sauvegardes | Forte (C, I) | Concepteur | 2026-10-28 (doc) | `docs/16` §2, `CLAUDE.local.md` (non versionne) |
| Appareils des apiculteurs | Navigateur ou telephone : cookie de session, file IndexedDB | Moyenne (D3, I4 pour la saisie hors ligne) | Utilisateur | 2026-10-28 (doc) | ADR 0005, 0006 |

## 2. Services externes et comptes

Aucun identifiant ici. « MFA » et « recuperation » sont a renseigner par le concepteur ; en
l'absence de preuve dans le depot, la valeur est **a verifier**.

| Service | Usage | Proprietaire | MFA | Mode de recuperation documente | Criticite | Verifie le | Source |
|---|---|---|---|---|---|---|---|
| OVH (compte client) | Facturation, console VPS, stockage objet, messagerie | Concepteur | a verifier | non documente | Forte (acces au VPS et aux sauvegardes) | non verifie | ADR 0004, 0007 |
| Registrar du domaine `beevarium.fr` | Zone DNS, renouvellement | Concepteur (registrar a identifier ; OVH probable) | a verifier | non documente | Forte (D, T : perte du domaine = perte du service et des e-mails) | non verifie | `docs/06` §Site |
| GitHub, depot prive | Code, CI, issues, secrets Actions (aucun connu) | Concepteur | a verifier | non documente | Moyenne (code ; aucune donnee d'utilisateur) | 2026-10-28 | ADR 0010, `docs/05` |
| GitHub, depot public | Copie du code sans historique (`export_public.sh`) | Concepteur | a verifier (meme compte) | non documente | Faible | 2026-10-28 | ADR 0013 |
| Messagerie OVH (`contact@beevarium.fr`, SMTP) | Alertes de supervision, reinitialisation de mot de passe, contact | Concepteur | a verifier | non documente | Moyenne (T3 : comptes ; reinitialisation depend du SMTP) | non verifie | ADR 0008, `configure_smtp.sh` |
| Stockage objet OVH (S3, via rclone) | Sauvegardes chiffrees hors site (14 jours) | Concepteur (meme compte OVH) | a verifier | non documente | Forte (derniere copie des donnees) | non verifie | ADR 0007, `configure_offsite.sh` |
| Let's Encrypt (via Caddy) | Certificats TLS, renouvellement automatique | sans compte (ACME anonyme) | sans objet | sans objet | Moyenne (D) | non verifie | ADR 0004 |
| Stripe, Apple Developer, Google Play | **Futurs** (non ouverts) | Concepteur | a prevoir | a prevoir | A definir | n/a | ADR 0014, 0015, `docs/11` |

## 3. Logiciels et versions

### 3.1 Production (VPS et image API)

| Composant | Version | Source | Criticite | Verifie le |
|---|---|---|---|---|
| Systeme | Debian 12 (version du noyau et correctifs : a verifier) | ADR 0004 | Forte | 2026-10-28 (doc) |
| Docker et Docker Compose | version installee sur le VPS : a verifier | `docs/06` §2 | Forte | non verifie |
| Caddy | version du paquet installe sur le VPS : a verifier (hors compose) | `docs/06` §1, §Site | Forte (seul composant expose) | non verifie |
| PostgreSQL | 16 (`postgres:16-alpine`) | `docker-compose*.yml` | Forte (I4) | 2026-10-28 |
| Python (image API) | 3.12 (`python:3.12-slim`, non epingle par empreinte) | `backend/Dockerfile` | Forte | 2026-10-28 |
| Application | `v1.37.0` deployee le 2026-10-28 (tag a confirmer par `/health`) | `suivi-projet.md` | Forte | 2026-10-28 (doc) |

### 3.2 Dependances Python (`backend/requirements.txt`)

| Paquet | Version |
|---|---|
| fastapi | 0.141.1 |
| uvicorn[standard] | 0.35.0 |
| sqlalchemy | 2.0.43 |
| psycopg[binary] | 3.2.9 |
| pydantic | 2.11.7 |
| pydantic-settings | 2.10.1 |
| email-validator | 2.3.0 |
| PyJWT | 2.15.0 |
| python-multipart | 0.0.32 |
| openpyxl | 3.1.5 |

Criticite : Forte pour l'ensemble (code execute en production, risque R9 de `docs/16`). Suivi : `pip-audit` et Trivy dans le gate, Dependabot hebdomadaire. Verifie le 2026-10-28.

### 3.3 Outils de test, de securite et de CI (hors production)

| Outil | Version | Source | Criticite |
|---|---|---|---|
| pytest / requests (`requirements-dev.txt`) | 9.1.1 / 2.34.2 | `backend/requirements-dev.txt` | Faible |
| Playwright Test et image | 1.55.0 (`mcr.microsoft.com/playwright:v1.55.0-noble`) | `e2e_test.sh` | Faible |
| Trivy | `aquasec/trivy:0.61.0` | `security_audit.sh` | Moyenne |
| pip-audit | 2.9.0 | `security_audit.sh` | Moyenne |
| Bandit | 1.8.6 | `.github/workflows/ci.yml` | Faible |
| gitleaks | `zricethezav/gitleaks:v8.24.3` | `.github/workflows/ci.yml` | Moyenne |
| OWASP ZAP | 2.16.1 (utilise ponctuellement, `docs/14`) | `docs/14-audit-securite.md` | Faible |
| GitHub Actions | `actions/checkout@v4`, `setup-python@v5`, `upload-artifact@v4`, runner `ubuntu-24.04`, Python 3.12 | `ci.yml` | Moyenne |
| rclone (sauvegarde hors site) | version installee dans `~/bin` du VPS : a verifier | `configure_offsite.sh` | Forte |
| Polices Kalam et Nunito Sans | Fontsource 5.3.0 (SIL OFL), auto-hebergees | `docs/14` A3 | Faible |

### 3.4 Images de supervision (`docker-compose.monitoring.yml`, non exposees)

| Image | Etiquette | Remarque |
|---|---|---|
| `tecnativa/docker-socket-proxy` | 0.1.2 | Epinglee |
| `netdata/netdata` | `stable` | Etiquette mobile, non epinglee |
| `louislam/uptime-kuma` | `1` | Etiquette majeure mobile, non epinglee |

Ces trois images n'epinglent pas de version complete ni d'empreinte pour deux d'entre elles :
a signaler (§10). Etat reel de leur lancement sur le VPS : a verifier.

## 4. Donnees

Le detail des traitements, durees et finalites est dans `docs/13-registre-rgpd.md` ; les besoins
D/I/C/T dans `docs/16` §1. Categories de tables (schema `db/init/001_schema.sql` et migrations) :

| Categorie | Tables | Criticite (D/I/C/T) | Renvoi |
|---|---|---|---|
| Comptes et authentification | `users`, `password_reset_tokens` | 2/3/3/3 | `docs/13` Compte, Reinitialisation |
| Donnees apicoles | `ruchers` (GPS facultatif), `visites_rucher`, `ruches`, `ruche_tags`, `reines`, `visites_ruche`, `actions_visite`, recoltes, materiel, cadres | 2/4/2/2 (GPS : 1/2/4/2) | `docs/13` Donnees apicoles |
| Saisie hors ligne | `idempotency_keys` | 3/4/2/2 | `docs/13` Saisie hors ligne |
| Retours beta | `beta_feedback` | faible | `docs/13` Retours beta |
| Journal technique | `api_events` (6 mois) | faible | `docs/13` Journal technique |
| Sauvegardes | Dumps locaux (14 jours) et copie chiffree hors site (14 jours) | 2/3/3 (copie complete) | ADR 0007, `docs/13` Sauvegardes |
| Futures donnees de paiement | `billing_customers`, `subscriptions`, `payment_events` (non creees) | a evaluer a l'ouverture | `docs/11` |

Emplacement : volume Docker `beevarium_target_data` (beta) et volume propre a la stack app-dev,
sur le VPS ; copie chiffree dans le stockage objet OVH.

## 5. Secrets (natures et emplacements, jamais les valeurs)

| Nature | Emplacement | Usage | Criticite | Remarques |
|---|---|---|---|---|
| Secret JWT (`JWT_SECRET_KEY`), mots de passe de base, parametres SMTP, `STACK_NAME`, image | `.env.target` du VPS (beta et app-dev, deux fichiers) | Fonctionnement de l'API | Forte | Ignore par Git ; refus de demarrer si la valeur par defaut subsiste (`docs/06`) |
| Copie de `.env.target` | Poste du concepteur (a verifier) | Reprise sur un nouveau VPS | Forte | A confirmer : existe-t-elle, ou est-elle conservee ? |
| Cle ou phrase de chiffrement des sauvegardes (AES-256-CBC, PBKDF2) | Poste du concepteur et VPS (fichier lu par `backup_offsite.sh`, emplacement a verifier) | Dechiffrer la copie hors site | Forte (perdue, la copie est inutilisable) | Une copie hors VPS est indispensable (§10) |
| Cle d'acces S3 (stockage objet), configuration rclone | `~/.config/rclone` du VPS | Envoi des sauvegardes | Forte | Creee par `configure_offsite.sh` |
| Cle SSH d'administration | Poste du concepteur (cle privee) ; cle publique sur le VPS | Acces au VPS | Forte | Mot de passe SSH encore accepte (audit A1, `docs/14`) |
| Cle SSH dediee au depot public | Poste du concepteur (`~/.ssh`) | Publication du depot public | Moyenne | Cle de deploiement GitHub ; limitee a ce depot (a verifier) |
| Cle SSH ou jeton d'acces au depot prive | Poste du concepteur et VPS (clone `~/app`) | Fetch et deploiement | Moyenne | Lecture seule recommandee sur le VPS (a verifier) |
| Secrets GitHub Actions | Parametres du depot prive | CI | Faible | Aucun requis par `ci.yml` (secret JWT genere a chaque run) |
| Identifiant du compte de demonstration | Hors depot (`CLAUDE.local.md`, `demo-access.json` ignore) | Presentation, tests | Faible | Compte fictif |
| Futurs : cles API Stripe, secret de webhook, cles des stores | `.env.target` | Paiement | Forte | A ajouter a cet inventaire a l'ouverture (ADR 0015) |

## 6. Noms de domaine et certificats

| Nom | Role | Service | Certificat | Verifie le |
|---|---|---|---|---|
| `beevarium.fr`, `www.beevarium.fr` | Page d'accueil statique (`site/`, `/var/www/beevarium`) | Caddy | Let's Encrypt, renouvellement automatique par Caddy | 2026-10-28 (doc) |
| `beta.beevarium.fr` | Application beta | Caddy vers l'API locale (port interne) | Let's Encrypt, idem | 2026-10-28 (doc) |
| Adresse `contact@beevarium.fr` | Contact public, expediteur des alertes | Messagerie OVH | sans objet | 2026-10-28 (doc) |

Echeance du domaine, enregistrements DNS (MX, SPF, DKIM, DMARC) et date d'expiration des
certificats : **a verifier** (§10).

## 7. Environnements

| Environnement | Ou | Port / URL | Stack | Donnees |
|---|---|---|---|---|
| Local | Poste du concepteur | `http://localhost:8000` | `docker-compose.yml` (conteneurs `beevarium_api`, `beevarium_db`) | Fictives |
| Test (app-dev) | VPS, clone `~/app-dev` | interne `18001` | `docker-compose.target.yml`, `STACK_NAME=beevarium_dev` | Fictives (smokes) |
| Beta | VPS, clone `~/app` | `https://beta.beevarium.fr` ; API interne `18000`, base interne `15432` | `docker-compose.target.yml` (conteneurs `beevarium_api_target`, `beevarium_db_target`) + Caddy | **Reelles** (testeurs) |
| CI | Runners GitHub | stack jetable | `docker-compose.yml` | Fictives |

Seuls SSH, 80 et 443 sont ouverts sur le VPS (`docs/06` §1).

## 8. Procedure de mise a jour

| Declencheur | Action | Qui |
|---|---|---|
| Chaque release (avant le tag) | Comparer `requirements*.txt`, `Dockerfile`, `docker-compose*.yml`, `security_audit.sh`, `ci.yml` aux §3 ; mettre a jour les versions et la ligne « Application » | Agent qui prepare la release, relecture du concepteur |
| Chaque nouveau service, compte ou fournisseur | Ajouter la ligne aux §2, §5 et `docs/19-budget.md` ; si donnees personnelles, `docs/13` ; si decision d'architecture, un ADR | Concepteur (ou agent sur demande) |
| Chaque nouvelle table ou categorie de donnees | Mettre a jour le §4 et `docs/13` | Agent |
| Chaque nouveau secret | Ajouter sa **nature** et son emplacement au §5 (jamais la valeur) | Concepteur |
| Changement de VPS, de domaine ou de fournisseur | Revoir tout le document | Concepteur |
| Chaque trimestre et apres tout incident G1 ou G2 | Relecture complete, mise a jour des dates « Verifie le », traitement du §10 | Concepteur |

Regle de date : « Verifie le » n'est mis a jour que si la verification a vraiment eu lieu, avec
sa source ; un changement lu dans le depot ne vaut pas verification de l'etat live.

## 9. Ecarts constates dans le depot

- Netdata (`stable`) et Uptime Kuma (`1`) utilisent des etiquettes mobiles, a l'inverse des autres images epinglees : un `pull` peut changer la version sans decision explicite.
- L'image `python:3.12-slim` est suivie par Dependabot mais non epinglee par empreinte.
- Aucune version de Caddy, Docker, rclone ni du noyau n'est documentee dans le depot.

## 10. Points a verifier par le concepteur

1. **MFA** active sur : compte OVH (VPS, stockage objet, messagerie), registrar, GitHub (prive et public). Noter la date.
2. **Recuperation de compte** : codes de secours GitHub et OVH conserves hors ligne ; adresse de recuperation distincte du domaine `beevarium.fr` (sinon dependance circulaire).
3. **Renouvellement du domaine** : registrar, date d'echeance, renouvellement automatique, moyen de paiement valide ; enregistrements DNS (MX, SPF, DKIM, DMARC).
4. **Cle de chiffrement des sauvegardes** : une copie existe hors du VPS et du poste (support hors ligne ou gestionnaire de mots de passe) ; sans elle, la copie hors site est inutilisable.
5. **Copie de `.env.target`** hors VPS, pour la reprise sur un nouveau VPS (cible de 4 h, `docs/16`).
6. **SSH par mot de passe** desactive (audit A1) ; Lynis (A4).
7. **Versions du VPS** : Debian (point release), Docker, Caddy, rclone, noyau ; `unattended-upgrades` actif ?
8. **Cle SSH du depot public** : cle de deploiement limitee a ce depot ; acces du VPS au depot prive en lecture seule.
9. **Netdata et Uptime Kuma** : lances ou non sur le VPS ; epingler les versions (§9).
10. **Offre du VPS et du stockage objet** (voir `docs/19-budget.md`) ; region du stockage objet (donnees dans l'Union europeenne).
11. **Dates « Verifie le »** : les mentions « non verifie » attendent un controle direct sur le VPS ou les consoles.
