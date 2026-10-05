# Beevarium Agent Guide

Guide permanent pour les agents IA qui travaillent sur Beevarium. Ce document est specifique a ce depot. La source de verite est Git : ne jamais perdre, ecraser ou reinitialiser les changements existants.

## Produit et priorite

Beevarium est une application web de gestion de ruchers, ruches, visites, recoltes et materiel pour apiculteurs. La beta est ouverte a des testeurs depuis le 2026-10-04 (inscription libre, comptes Premium pendant la beta). La priorite est de stabiliser, corriger vite les retours des testeurs sans regression et ameliorer l'UX terrain.

Ne pas sur-ingenieriser, migrer de framework ou ajouter de grandes fonctionnalites sans demande explicite. Des donnees reelles de testeurs sont sur la beta : toute operation cible demande une sauvegarde prealable et un accord explicite.

## Documentation et etat courant

- Le code versionne, les migrations, les scripts et les tests definissent le comportement executable. Verifier ces sources avant de modifier un contrat ou une procedure.
- `README.md` est le point d'entree. `suivi-projet.md` est le handoff et le suivi de livraison : lire en priorite son en-tete, la section `Reste a faire` et les entrees les plus recentes. Les sections historiques plus bas ne decrivent pas necessairement l'etat actuel.
- Les documents `docs/01` a `docs/12` donnent le cadrage par domaine (produit, architecture, qualite, exploitation, API, beta, design et paiement). Ils peuvent contenir des procedures historiques : en cas de conflit, appliquer la regle la plus recente dans `suivi-projet.md`, puis ce guide pour les garde-fous agents, et signaler l'ecart plutot que de suivre une instruction risquee.
- Les maquettes Excalidraw ont ete abandonnees et retirees du depot (decision concepteur 2026-10-03). Les choix visuels se basent sur l'application actuelle, `docs/12-refonte-visuelle.md` (palette, regles mobile) et les retours du concepteur.
- La derniere version deployee sur la beta est `v1.36.1-type-ruche` (2026-10-04) ; `~/app-dev` est reste en `v1.35.0`. Ce n'est pas une preuve de l'etat live : avant toute operation cible, confirmer le tag Git, l'image et `/health`.

## Stack verifiee

- Python 3.12 dans `backend/Dockerfile`.
- FastAPI 0.141.1, Uvicorn 0.35.0, SQLAlchemy 2.0.43, Pydantic 2.11.7, pydantic-settings, psycopg 3.2.9, PyJWT 2.14.0, python-multipart, email-validator et openpyxl (lecture des imports `.xlsx`).
- PostgreSQL 16 dans Docker Compose.
- Client frontend HTML/CSS/JavaScript vanilla en modules ES natifs sous `backend/app/static/app/`, sans build. Aucun React, Vue, Angular ou autre framework frontend.
- Tests Python avec pytest 9.1.1 et requests 2.34.2 (`backend/requirements-dev.txt`), executes par `gate_fast.sh` dans `backend/.venv` s'il existe, sinon dans Docker.
- Tests navigateur avec Playwright Test 1.55.0, executes dans `mcr.microsoft.com/playwright:v1.55.0-noble`.
- Docker Compose local dans `docker-compose.yml`; stack cible dans `docker-compose.target.yml`.
- Ansible est present sous `ansible/` pour l'orchestration locale.

## Structure utile

- `backend/app/main.py` : creation FastAPI, middleware, gestion d'erreurs, montage `/app`, `/` et `/health`.
- `backend/app/config.py` : configuration Pydantic Settings et controles de securite runtime.
- `backend/app/security.py` : hash PBKDF2-SHA256, JWT, verification Bearer et revocation par `token_version`.
- `backend/app/models.py` : modeles SQLAlchemy principaux (`User`, `Rucher`, `Ruche`, `RucheTag`, `VisiteRuche`, `Reine`, materiel, mouvements, recoltes, evenements API).
- `backend/app/schemas.py` : contrats Pydantic API.
- `backend/app/routers/` : routes FastAPI : auth, users, ruchers, ruches, creation rapide (creation en nombre, modeles, import), reines, visites, visites-rucher, recoltes, materiel-atelier, cadres, statistiques, references, IA vocale, feedback et events.
- Services partages de `backend/app/` : `ownership.py` (appartenance), `materiel_flux.py` (stock), `surveillance.py` (ruches a surveiller), `creation_rapide.py` (creation en nombre, lecture et verification des imports).
- `backend/app/static/app/app.js` : point d'entree du client (liaison des evenements, demarrage) ; la logique vit dans les modules ES de `backend/app/static/app/js/` (voir `docs/03-architecture.md`). Une erreur de syntaxe ou un element DOM manquant peut arreter le bootstrap complet.
- `backend/app/static/app/index.html` : shell, onglets, formulaires, dialogues et controles de l'application.
- `backend/app/static/app/styles.css` : style et responsive desktop/mobile.
- `backend/app/static/app/feedback.html` : formulaire de feedback authentifie avec connexion inline si aucune session locale n'existe.
- `db/init/001_schema.sql` et `002_seed_refs.sql` : schema initial et references systeme pour une base vide.
- `db/migrations/` : migrations incrementales appliquees alphabetiquement par `deploy_apply_migrations.sh`; le nom suit `AAAAMMJJ_description_courte.sql`.
- `backend/tests/integration/test_api_integration.py` : suite d'integration HTTP et tests d'ownership ; `test_creation_rapide.py` : creation rapide, modeles, import et Premium.
- `tests/e2e/parcours.spec.js` : parcours Playwright critiques et non critiques ; `tests/e2e/simulation-apiculteur.spec.js` : journee d'un apiculteur professionnel (`simulation_apiculteur.sh`, jamais sur la beta).
- `site/` : page d'accueil statique de `beevarium.fr`, publiee par `scripts/linux/deploy_site.sh`.
- `scripts/watchdog.py` et `scripts/systemd/beevarium-watchdog.*` : alertes e-mail de supervision.
- `scripts/linux/export_public.sh` : copie sans historique pour le depot public.
- `tests/charge/parcours.js` et `scripts/linux/load_test.sh` : charge/performance, uniquement sur environnement local autorise.
- `suivi-projet.md` : handoff et etat de livraison a maintenir.
- `docs/05-qualite-et-tests.md` : gates et strategie de test.
- `docs/06-exploitation.md` : lancement, backup, deploiement, supervision et rollback.
- `docs/08-reference-api.md` : contrat API documente.
- `docs/07-roadmap.md` et `docs/02-backlog.md` : priorites produit.

## API et donnees

Les routes sont montees dans `main.py` avec les prefixes suivants :

- `/auth`, `/users`
- `/atelier`
- `/ruchers`, `/ruchers/creation-rapide`, `/ruches`, `/ruches/{id}/reines`, `/ruches/{id}/tags`
- `/modeles-ruche`, `/import/ruches` (Premium)
- `/visites`, `/visites-rucher`, `/recoltes`
- `/materiel-atelier`, `/cadres`, `/statistiques`, `/references`
- `/ia-vocale`, `/feedback`, `/events`

Toutes les routes metier authentifiees utilisent l'utilisateur du JWT. Toute lecture, creation, modification, suppression ou filtre par identifiant doit verifier l'ownership. Les erreurs d'acces a une ressource d'un autre compte sont generalement rendues en `404` pour ne pas exposer son existence; les regles explicites d'acces utilisateur peuvent rendre `403`.

Le perimetre offline couvre les visites manuelles de ruche : file IndexedDB, `Idempotency-Key` lie a l'utilisateur et conflits explicites par version. Les tags choisis, un transvasement et un changement de type de ruche voyagent dans le payload de la visite et sont appliques dans la meme transaction. Ne pas etendre ce mecanisme aux ruchers, ruches, reines ou audio sans conserver l'idempotence, l'ordre de synchronisation, l'absence d'ecrasement silencieux et les tests de conflit.

Les nouvelles donnees de schema doivent avoir une migration dans `db/migrations/` et une prise en compte dans `db/init/001_schema.sql` si une nouvelle base doit fonctionner directement. Ne jamais modifier une base cible a la main pour contourner une migration.

Les tags ont des effets metier sensibles : familles de type/statut, `colonie morte`, tags evenementiels, tags de hausses et mouvements de materiel. Toute modification de ces regles doit verifier les visites, la reine active, les mouvements, le stock et les tests d'ownership.

La quantite de materiel en service est calculee lorsque le type est auto-compte; elle ne doit pas etre ecrasee par un formulaire. Les formats de materiel restent distincts. Les annees de cire et mouvements de cadres alimentent l'age moyen des cadres.

## Authentification et secrets

- Inscription, login, logout, reset de mot de passe et `/auth/me` sont sous `/auth`.
- Les mots de passe sont hashes en `pbkdf2_sha256$iterations$salt$hash`, avec 100 000 iterations dans `security.py`.
- Les JWT utilisent HS256 par defaut et contiennent l'identifiant utilisateur, l'expiration et `ver` correspondant a `token_version`.
- Logout et reset de mot de passe incrementent `token_version`, invalidant les sessions existantes.
- Les emails sont normalises en minuscules a l'inscription, au login et au reset.
- `debug_reset_url` est exclusivement dev/test/local; ne jamais l'exposer en staging/production.
- Ne jamais afficher, committer ou journaliser mot de passe, JWT, token reset, cle privee, `JWT_SECRET_KEY`, `.env` ou `.env.target`.
- Les fichiers `.env`, `.env.target`, `backend/.env`, `artifacts/`, `node_modules/`, `test-results/` et les identifiants demo locaux sont ignores par Git. Ne pas forcer leur ajout.

## Regles de travail

1. Lire le code concerne, ses usages, les schemas/modeles et les tests avant une modification importante.
2. Formuler une hypothese locale et un controle qui peut la falsifier.
3. Modifier tout le perimetre impacte par le changement, ni plus ni moins : route, schema, modele, migration, frontend, tests et documentation concernes. Prendre du recul sur chaque modification et verifier sa coherence avec le projet dans sa globalite (logique metier, autres onglets, donnees existantes, offline, stock).
4. Preserver les endpoints, contrats et comportements existants sauf exigence explicite.
5. Pour un bug reproductible, ajouter ou renforcer un test de non-regression.
6. Apres une edition substantielle, executer d'abord la validation la plus ciblee, puis le gate pertinent.
7. Pour le frontend, toujours lancer `check_client_assets.sh`; completer avec Playwright si le parcours ou l'UX est touche.
8. Ne jamais supprimer ou affaiblir un test uniquement pour obtenir une suite verte.
9. Ne pas lancer de smoke sur la beta : les smokes creent des donnees et la configuration beta privee peut rendre les assertions freemium invalides.
10. Avant une migration ou un deploiement beta, demander confirmation si l'operation est destructive ou difficilement reversible.
11. Ne jamais utiliser `git reset --hard`, `git checkout --` ou une restauration destructive pour effacer des changements existants.
12. Ne pas committer automatiquement sauf demande explicite ou procedure de release explicitement engagee.
13. Si une incoherence, un manque ou une contradiction est detecte dans les consignes, le code, la documentation ou les tests, le signaler au concepteur et proposer une correction concrete. Ne modifier la consigne ou le comportement concerne qu'apres validation explicite du concepteur.


## Autonomie, efficacité et maîtrise des coûts des agents

### Objectif

Travailler efficacement sur Beevarium en réduisant les tokens inutiles, les relances et les validations redondantes, sans réduire la qualité du code, la couverture des tests pertinents ni la sécurité.

L'agent doit être autonome sur les décisions techniques locales et réversibles. Il doit demander une validation humaine uniquement lorsqu'une décision dépasse le périmètre autorisé, présente un risque significatif ou nécessite un arbitrage produit.

### 1. Prise en charge d'une tâche

Pour chaque demande :

1. Identifier le résultat attendu, les contraintes et les critères de réussite.
2. Lire `suivi-projet.md` aux endroits pertinents, puis examiner le code, les tests et la documentation directement concernés.
3. Vérifier l'état Git et préserver les changements préexistants.
4. Définir un plan court, adapté à la taille et au risque de la tâche.
5. Exécuter la tâche de bout en bout dans le périmètre autorisé, sans demander de validation intermédiaire pour chaque étape.

Pour une tâche simple et bien définie, ne pas produire de long plan préalable : agir directement et expliquer brièvement le résultat.

Si une information manque mais peut être déterminée à partir du dépôt, la rechercher plutôt que poser une question au concepteur.

Si plusieurs solutions techniques sont raisonnables et qu'elles respectent les contrats et les objectifs existants, choisir la solution la plus simple, maintenable et cohérente avec la stack actuelle. Expliquer ce choix dans le compte rendu.

Demander une clarification uniquement si l'ambiguïté change sensiblement le comportement produit, la sécurité, les données, le coût récurrent ou le périmètre de la demande.

### 2. Périmètre et discipline de modification

* Modifier l'ensemble des fichiers impactés par le changement pour résoudre le problème durablement, sans brider artificiellement le périmètre ni l'étendre à des sujets sans lien.
* Avant de conclure, prendre du recul : la modification est-elle cohérente avec les autres onglets, les règles métier, les données existantes et les décisions déjà prises dans `suivi-projet.md` ?
* Ne pas relire systématiquement tout le dépôt : partir des fichiers concernés et suivre leurs dépendances lorsque nécessaire.
* Ne pas effectuer de refactoring opportuniste, migration de framework, ajout de dépendance ou nouvelle fonctionnalité sans nécessité démontrée.
* Ne pas dupliquer une logique existante si elle peut être réutilisée proprement.
* Ne pas modifier des fichiers sans lien avec la tâche.
* Ne pas écraser, reformater massivement ou supprimer des changements préexistants.
* Si un problème adjacent est découvert, le corriger dans la même tâche uniquement s'il est directement lié, de faible risque et dans le périmètre. Sinon, le signaler séparément.

### 3. Corrections groupées et prévention des relances

Pour un bug ou un parcours défectueux :

1. Reproduire ou caractériser le problème avec les moyens disponibles.
2. Identifier la cause racine, pas seulement masquer le symptôme.
3. Examiner les effets sur les composants, routes, données et parcours voisins.
4. Regrouper les corrections cohérentes dans une même intervention.
5. Ajouter ou renforcer les tests de non-régression.
6. Exécuter les validations pertinentes et relire le diff avant de conclure.

Ne pas rendre la main après chaque modification intermédiaire si la suite du travail est claire et autorisée.

Si un test échoue, analyser l'échec et effectuer les corrections nécessaires dans le périmètre autorisé. Ne pas s'arrêter au premier échec sans investigation.

Ne pas multiplier les tentatives identiques sans nouvelle hypothèse. Après plusieurs échecs, résumer ce qui a été appris, les hypothèses restantes et le blocage précis.

### 4. Stratégie de tests proportionnée au risque

Choisir les tests selon les couches touchées et le risque de régression.

* Documentation ou texte sans effet fonctionnel : contrôle du diff, sans lancer une suite lourde.
* JavaScript, HTML ou CSS : `check_client_assets.sh`; Playwright ciblé si le parcours, les interactions ou le rendu sont affectés.
* Route, logique métier ou modèle : tests pytest ciblés, puis tests d'intégration pertinents.
* Authentification, ownership, migrations, offline, stock ou règles métier sensibles : ajouter les vérifications spécifiques nécessaires et élargir les tests en conséquence.
* Changement transversal ou candidat à une livraison : exécuter les gates complets pertinents.

Ne pas lancer systématiquement tous les tests après chaque petite modification. Ne pas omettre un test important uniquement pour économiser du temps ou des tokens.

Si une validation est longue, coûteuse ou indisponible, commencer par les contrôles ciblés les plus informatifs, puis expliquer clairement ce qui reste à valider.

Respecter strictement les interdictions de smoke sur la beta et les règles de déploiement déjà définies dans ce guide.

### 5. Économie de ressources et usage du contexte

Chaque action consomme des tokens, du temps machine et de l'énergie. Viser le résultat juste avec le moins de ressources, sans jamais sacrifier la qualité.

* Planifier avant d'agir : regrouper les tâches qui touchent les mêmes fichiers, réutiliser les analyses, scripts, fixtures et résultats déjà produits plutôt que les refaire.
* Choisir la vérification la moins coûteuse qui prouve réellement le comportement : lecture de code, `grep`, test pytest ou appel API avant Playwright. Réserver Playwright aux parcours, interactions et rendus qui ne peuvent pas être vérifiés autrement ; limiter captures et lectures de DOM aux écrans utiles.
* Côté application, limiter le nombre et la complexité des requêtes (pas de N+1, agrégations SQL plutôt que boucles client, pas de rechargements inutiles) : c'est aussi une économie de ressources pour le serveur et le téléphone de l'apiculteur.
* Prendre du recul régulièrement, surtout avant un choix technique ou métier structurant : existe-t-il déjà une solution dans le dépôt ? La solution choisie restera-t-elle cohérente avec la suite du projet ?
* Surveiller la fenêtre de contexte sur les grosses tâches : découper en étapes qui laissent un état propre et documenté, sans s'interdire une tâche large si elle est cohérente.

* Utiliser en priorité les informations déjà présentes dans la conversation et les résultats des commandes déjà exécutées.
* Ne pas redemander une information déjà fournie ou vérifiable dans le dépôt.
* Éviter les commandes redondantes et les lectures répétées de fichiers inchangés.
* Préférer des recherches ciblées, des diffs et des tests précis aux sorties volumineuses sans valeur ajoutée.
* Regrouper les inspections et validations indépendantes lorsqu'elles peuvent être exécutées efficacement ensemble.
* Ne pas installer un outil, une dépendance ou un service externe si les outils existants suffisent.
* Ne pas ajouter de dépendance payante ou de coût récurrent sans demande explicite.
* Ne pas sacrifier la qualité, la sécurité ou la maintenabilité pour réduire artificiellement le nombre de tokens.

### 6. Autonomie et limites d'autorisation

L'agent peut, sans validation intermédiaire :

* lire et analyser le dépôt;
* modifier le code et les tests dans le périmètre demandé;
* exécuter les tests locaux et les outils de validation autorisés;
* corriger les erreurs découvertes directement liées à la tâche;
* effectuer des changements locaux réversibles;
* proposer des améliorations documentaires cohérentes avec le comportement réel.

L'agent doit demander une confirmation explicite avant :

* toute opération destructive ou difficilement réversible;
* toute migration ou modification de données sur un environnement cible;
* tout déploiement beta ou changement de configuration de production;
* toute dépense, souscription ou activation d'un service payant;
* toute modification substantielle du périmètre produit ou des contrats publics;
* toute action nécessitant un secret, un accès ou une autorisation non disponible.

Les règles de sécurité, de protection des données, de Git, de migration et de déploiement déjà présentes dans ce guide restent prioritaires et ne peuvent pas être contournées au nom de l'autonomie.

### 7. Compte rendu final concis

À la fin de la tâche, fournir un compte rendu directement exploitable :

* **Résultat :** ce qui a été corrigé ou réalisé.
* **Fichiers :** principaux fichiers modifiés.
* **Vérifications :** commandes ou tests exécutés et résultats réels.
* **Limites :** tests non exécutés, incertitudes ou problèmes restants.
* **Déploiement :** préciser explicitement si rien n'a été déployé ou si une validation humaine est requise.
* **Suite proposée :** prochaines étapes de travail et priorités recommandées.

Ne pas affirmer qu'un test, un déploiement ou une vérification a réussi s'il n'a pas réellement été exécuté.

Si la tâche est bloquée, fournir le diagnostic, les tentatives effectuées et la décision précise attendue du concepteur.



## Commandes locales

Depuis la racine du depot :

```bash
cp .env.example .env
docker compose --env-file .env up -d --build
bash scripts/linux/wait_for_api.sh --api-base-url http://localhost:8000
```

Le nom de commande habituel est `docker compose` en minuscules; l'exemple ci-dessus reste conceptuel si le shell est sensible a la casse.

Validation rapide :

```bash
bash scripts/linux/gate_fast.sh --api-base-url http://localhost:8000
```

Validation complete :

```bash
bash scripts/linux/gate_fast.sh --full-integration --api-base-url http://localhost:8000
```

Avant un tag de livraison, produire aussi le rapport de readiness :

```bash
bash scripts/linux/gate_release_candidate.sh artifacts/v1-readiness.json http://localhost:8000
```

Validation assets seuls :

```bash
bash scripts/linux/check_client_assets.sh
```

Tests integration directs :

```bash
BEEVARIUM_API_URL=http://localhost:8000 python -m pytest backend/tests/integration -q
```

Si pytest n'est pas disponible localement, `gate_fast.sh` peut utiliser Docker avec `python:3.11-slim`. Le conteneur `beevarium_api` local n'embarque pas pytest et ne monte pas le code Python; apres une modification backend, reconstruire l'API avec `docker compose up -d --build api`.

## Playwright

Le script officiel est :

```bash
bash scripts/linux/e2e_test.sh http://localhost:8000 --grep "@critical"
```

Le script nettoie les artefacts Playwright temporaires et execute Playwright dans Docker. La configuration est sequentielle (`workers: 1`) car les parcours partagent la base et le serveur. Les tests utilisent des comptes uniques mais creent des donnees; ils doivent cibler local ou `app-dev`, jamais la beta.

Pour un parcours UI, verifier les erreurs `pageerror`, les erreurs console, les messages apres sauvegarde, l'etat des popups, la navigation entre onglets et le rendu mobile. Tester au moins une largeur desktop et une largeur mobile lorsque le CSS ou le formulaire est touche.

## Environnements et deploiement

- Local : `http://localhost:8000`, conteneurs `beevarium_api` et `beevarium_db`.
- VPS beta : SSH `<utilisateur>@<vps>` (voir `AGENTS.local.md`, non versionne), jamais root, clone `~/app`, port interne 18000, conteneurs `beevarium_api_target` et `beevarium_db_target`.
- VPS test : clone `~/app-dev`, port 18001, stack `STACK_NAME=beevarium_dev`, conteneurs `beevarium_dev_api_target` et `beevarium_dev_db_target`.
- La beta publique est `https://beta.beevarium.fr`; Caddy est le seul composant expose publiquement.
- `https://beevarium.fr` et `www` servent la page d'accueil statique (`/var/www/beevarium`), hors de l'API.
- Les deploiements beta sont lances par le concepteur sur le VPS : l'agent prepare les commandes, puis verifie en lecture seule (`/health`, image, logs, `schema_migrations`). Ne pas en deduire l'etat live sans le verifier.

Commande unique (recommandee), lancee sur le VPS par le concepteur :

```bash
bash ~/app/scripts/linux/deploy.sh                 # dernier tag de main : app-dev + gate, puis beta
bash ~/app/scripts/linux/deploy.sh <tag> dev       # app-dev seulement ; <tag> ou latest
bash ~/app/scripts/linux/deploy.sh latest beta     # beta seulement
```

Depuis le poste : `ssh -t <utilisateur>@<vps> 'bash ~/app/scripts/linux/deploy.sh'` (`-t` pour la confirmation).
Le script enchaine les etapes ci-dessous, s'arrete a la premiere erreur, ne touche pas la beta si app-dev
echoue, demande de taper `beta` avant la beta, refuse un clone modifie ou un `backend/`/`db/` different
du tag, verifie la version dans `/health` et journalise dans `~/app/artifacts/deploy-logs/`.
Il ne sert pas au retour arriere (`deploy_rollback.sh`).

Procedure app-dev detaillee :

```bash
ssh <utilisateur>@<vps>
cd ~/app-dev
git pull --ff-only origin main
git fetch --tags origin
bash scripts/linux/deploy_apply_migrations.sh .env.target
bash scripts/linux/deploy_release.sh <tag> .env.target
bash scripts/linux/gate_fast.sh --api-base-url http://127.0.0.1:18001
```

Procedure beta, uniquement apres validation app-dev, tag Git et accord explicite :

```bash
ssh <utilisateur>@<vps>
cd ~/app
git pull --ff-only origin main
git fetch --tags origin
bash scripts/linux/deploy_backup_db.sh .env.target artifacts/backups
bash scripts/linux/deploy_apply_migrations.sh .env.target
bash scripts/linux/deploy_release.sh <tag> .env.target
bash scripts/linux/deploy_health_watch.sh https://beta.beevarium.fr 6 artifacts/beta/health-watch.json
```

Ne pas lancer `smoke_api.sh` ou `gate_fast.sh` contre la beta. Pour un rollback, utiliser `bash scripts/linux/deploy_rollback.sh .env.target` apres avoir identifie l'image precedente et la sauvegarde correspondante.

## Definition of Done

Une tache est finie lorsque :

- le comportement demande est implemente;
- les couches impactees (route, schema, modele, migration, frontend) sont coherentes;
- les tests pertinents sont ajoutes ou mis a jour;
- `check_client_assets.sh`, pytest et/ou Playwright sont passes selon le risque;
- les erreurs console et API du parcours sont verifiees lorsque pertinent;
- aucun test n'a ete supprime pour masquer un probleme;
- aucun secret, artefact ou fichier hors perimetre n'a ete ajoute;
- le diff est relu et les changements sont documentes dans `suivi-projet.md` si la tache modifie l'etat du projet.

## Pieges connus

- Une erreur de syntaxe dans `backend/app/static/app/app.js` ou un module de `js/` peut rendre toute l'application inutilisable alors que l'API reste verte.
- Le cache frontend est configure en `no-cache`, mais un rebuild/rechargement reste necessaire apres une modification backend ou HTML/CSS.
- Le client est vanilla : supprimer un id HTML sans retirer son `getElementById` ou son `addEventListener` peut interrompre `bindEvents` et casser silencieusement les controles suivants.
- Les scripts Bash utilisent `set -euo pipefail`; les recherches optionnelles doivent gerer l'absence de resultat.
- Les migrations sont alphabetiques et enregistrees dans `schema_migrations`; ne jamais renommer une migration deja appliquee.
- Les bases beta et app-dev partagent le VPS mais pas leurs volumes, conteneurs ni ports. Ne jamais confondre `18001` et `18000`.
- Les donnees de demonstration et les comptes de test sont utiles pour Playwright mais ne doivent jamais etre utilises pour justifier une modification destructive de la beta.
- La beta donne Premium a chaque nouveau compte (`BETA_NEW_USERS_PREMIUM=true`, decision du concepteur) : tester le parcours gratuit avec un compte cree `is_premium: false` en local, pas sur la beta.
- Un champ renomme dans `index.html` doit l'etre aussi dans `js/dom.js` : sinon `getElementById` renvoie `null` et `bindEvents` s'arrete.
- Le root `/` redirige vers `/app/`; `/health` expose `status`, `database`, `app_version` et `environment`.

## Communication finale

Le proprietaire veut une reponse concise et concrete : changements, fichiers principaux, validations executees, resultat, limites restantes et statut de deploiement. Signaler explicitement les tests impossibles, les changements non deployes et toute action necessitant une confirmation humaine.

Terminer en proposant au concepteur les etapes de travail suivantes et les priorites a traiter, en s'appuyant sur la section `Reste a faire` et le plan d'action de `suivi-projet.md`.
