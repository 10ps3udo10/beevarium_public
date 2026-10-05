# Beevarium

Application web de gestion de ruchers pour apiculteurs amateurs et
professionnels : ruchers, ruches, reines, visites, recoltes, materiel d'atelier
et statistiques. Pensee pour le terrain : utilisable au telephone, saisie des
visites hors ligne avec synchronisation au retour du reseau.

**Beta fermee : https://beta.beevarium.fr**

- **Gratuit** : toutes les fonctionnalites, jusqu'a 2 ruchers.
- **Premium** : ruchers illimites et saisie vocale des visites (en preparation).

## Fonctionnalites

- **Cheptel** : ruchers (biotope, statut, coordonnees), ruches par format
  (Dadant, ruchette...), transhumance, Atelier pour les ruches stockees.
- **Reines** : historique, remplacement, age, alerte au-dela de 2 ans.
- **Visites** : observations, cadres et couvain, hausses, tags metier
  (`a nourrir`, `orpheline`...), saisie hors ligne, transvasement d'une colonie
  vers un nouveau contenant.
- **Materiel** : stock par type et format, ruche montee depuis le stock ou
  achetee, demontage qui remet les elements en stock.
- **Suivi** : tableau de bord, ruches a surveiller detectees automatiquement,
  statistiques par saison, par rucher et fiche detaillee par ruche.

## Architecture

| Couche | Choix |
|---|---|
| API | Python 3.12, FastAPI, SQLAlchemy, Pydantic |
| Donnees | PostgreSQL 16, migrations SQL versionnees |
| Client | HTML, CSS et JavaScript sans framework, servi par l'API sous `/app` ; file hors ligne IndexedDB |
| Exploitation | Docker Compose, Caddy, sauvegardes chiffrees hors site, supervision |
| Qualite | pytest (integration HTTP et isolation des comptes), Playwright (parcours desktop et mobile), simulation d'usage |

Details : [docs/03-architecture.md](docs/03-architecture.md).

## Demarrage local

Prerequis : Docker.

```bash
cp .env.example .env
docker compose --env-file .env up -d --build
bash scripts/linux/wait_for_api.sh --api-base-url http://localhost:8000
```

- Application : http://localhost:8000/app
- Sante : http://localhost:8000/health

Compte de demonstration avec donnees :

```bash
bash scripts/linux/bootstrap_demo_data.sh --premium --output-json-path artifacts/demo-access.json
```

Puis, sur la page de connexion, `Utiliser un acces de demonstration` et `Se connecter`. Pour un
cheptel professionnel realiste (plusieurs ruchers, ~200 ruches) :
`python3 scripts/seed_realistic_data.py --api-base-url http://localhost:8000 --amateurs 0 --pluriactifs 0 --pros 1 --sortie-json artifacts/pro.json` (identifiants dans le fichier JSON).

## Verifier

```bash
# Gate rapide : assets client, smoke API, integration, parcours critiques
bash scripts/linux/gate_fast.sh --api-base-url http://localhost:8000

# Gate complet avant livraison
bash scripts/linux/gate_fast.sh --full-integration --api-base-url http://localhost:8000

# Simulation d'une journee d'apiculteur professionnel (desktop et mobile)
bash scripts/linux/simulation_apiculteur.sh http://localhost:8000
```

Strategie de test : [docs/05-qualite-et-tests.md](docs/05-qualite-et-tests.md).

## Structure

```
backend/app/        API FastAPI (routers, modeles, schemas) et client web (static/app)
backend/tests/      tests d'integration HTTP
db/                 schema initial, references et migrations
tests/e2e/          parcours Playwright et simulation apiculteur
scripts/linux/      gates, deploiement, sauvegardes, donnees de demonstration
ansible/            orchestration locale
docs/               documentation projet
site/               page d accueil statique de beevarium.fr
```

## Documentation

| Document | Contenu |
|---|---|
| [suivi-projet.md](suivi-projet.md) | Etat du projet, plan d'action, reste a faire |
| [AGENTS.md](AGENTS.md) | Regles de travail des agents IA sur le depot |
| [docs/01-vision-produit.md](docs/01-vision-produit.md) | Cadrage produit, cibles, contraintes terrain |
| [docs/02-backlog.md](docs/02-backlog.md) | Backlog par epics |
| [docs/03-architecture.md](docs/03-architecture.md) | Stack, offline, choix techniques |
| [docs/04-ux-ui.md](docs/04-ux-ui.md) | Cahier des charges de l'interface |
| [docs/05-qualite-et-tests.md](docs/05-qualite-et-tests.md) | Gates, tests, simulation |
| [docs/06-exploitation.md](docs/06-exploitation.md) | Deploiement, sauvegardes, supervision, rollback |
| [docs/07-roadmap.md](docs/07-roadmap.md) | Trajectoire beta puis stores |
| [docs/08-reference-api.md](docs/08-reference-api.md) | Reference des endpoints |
| [docs/09-ouverture-beta-testeurs.md](docs/09-ouverture-beta-testeurs.md) | Kit testeurs et support |
| [docs/10-audit-mobile-et-test-terrain.md](docs/10-audit-mobile-et-test-terrain.md) | Protocole de test sur telephone |
| [docs/11-paiements-et-abonnements.md](docs/11-paiements-et-abonnements.md) | Paiement web et stores |
| [docs/12-refonte-visuelle.md](docs/12-refonte-visuelle.md) | Principes visuels |

## Securite

Aucun secret n'est versionne : configuration par fichiers `.env` ignores par Git
(modeles `.env.example` et `.env.target.example`). Mots de passe hashes
PBKDF2-SHA256, sessions par cookie HttpOnly revocables, isolation stricte des
donnees entre comptes, couverte par les tests d'integration.
