# Qualite et tests

## Objectif
Verifier a faible cout pendant l'iteration, et de facon complete avant chaque
livraison sur la beta.

## Strategie
1. Pendant le developpement : `Gate rapide`, avec E2E critiques seulement.
2. Avant une livraison : `Gate complet`, avec toutes les integrations et tous les E2E.
3. Avant un tag : `Gate release candidate`, qui produit un rapport JSON tracable.

## Commandes

### Gate rapide
```bash
bash scripts/linux/gate_fast.sh --api-base-url http://localhost:8000
```

Ce mode execute les assets client, le smoke strict, un sous-ensemble de tests
d'integration critiques et les parcours navigateur marques `@critical`.

### Gate complet
```bash
bash scripts/linux/gate_fast.sh --full-integration --api-base-url http://localhost:8000
```

Options utiles :
- `--e2e-mode critical` : parcours navigateur critiques seulement.
- `--e2e-mode full` : tous les parcours navigateur.
- `--e2e-mode skip` : aucun parcours navigateur, a reserver au diagnostic local.

### Gate release candidate + rapport
```bash
bash scripts/linux/gate_release_candidate.sh artifacts/v1-readiness.json http://localhost:8000
```

## Artefacts
- `artifacts/smoke-result.json`: details smoke + checks freemium + revocation
- `artifacts/v1-readiness.json`: resultat gate release candidate

## Ce que couvre le gate

Le gate rapide enchaine un smoke strict, la validation de son rapport JSON, un
sous-ensemble de tests d'integration critiques et trois E2E critiques :
chargement sans erreur JavaScript, parcours rucher/ruche/visite, deconnexion.
Le mode complet execute la suite d'integration entiere et tous les E2E.

Le smoke strict verifie de bout en bout : health, inscription, connexion,
creation de rucher et de ruche, saisie de visite, synthese de periode, IA vocale
Premium, deconnexion et revocation effective du jeton. Il verifie aussi les deux
regles freemium : blocage de l'IA pour un compte Free, et refus du 3e rucher.

## Tests d'integration

```bash
pip install -r backend/requirements-dev.txt
pytest backend/tests/integration -q
```

L'URL cible se configure via la variable `BEEVARIUM_API_URL`
(defaut : `http://localhost:8000`).

Apres un rebuild, attendre la disponibilite de l'API avant de lancer les tests,
sinon les premiers echouent de facon transitoire :

```bash
bash scripts/linux/wait_for_api.sh --api-base-url http://localhost:8000
```

## Limite connue

Les endpoints ajoutes entre les versions `v1.3` et `v1.23` ont ete livres sans
tests d'isolation des comptes dedies. Ce rattrapage est un prerequis P0 avant
d'ouvrir la beta a des testeurs externes.

Le rattrapage est largement couvert et a ete renforce localement le 2026-09-06
sur les endpoints recents de tags, reines et deplacement de ruches. Avant une
ouverture externe, rejouer le gate complet sur `~/app-dev` et conserver le smoke
hors de la beta.


## Tests de parcours navigateur

Neuf parcours couvrent ce que les tests d'API ne voient pas : une erreur de
syntaxe dans `app.js` rend l'application inutilisable alors que toute l'API
reste verte.

```bash
bash scripts/linux/e2e_test.sh http://127.0.0.1:18001
```

Ils tournent dans un conteneur Playwright, ciblent l'environnement de test et
sont inclus dans le gate complet. Le script accepte les arguments Playwright,
par exemple :

```bash
bash scripts/linux/e2e_test.sh http://127.0.0.1:18001 --grep "@critical"
```

Si `pytest` n'est pas installe sur le VPS, `gate_fast.sh` bascule sur un
conteneur `python:3.11-slim` pour lancer les tests d'integration.

## Jeu de donnees realiste

```bash
python3 scripts/seed_realistic_data.py --amateurs 3 --pluriactifs 2 --pros 1
```

Trois profils : amateur (1 rucher, 2 a 4 ruches), pluriactif (2 a 3 ruchers,
6 a 12 ruches par rucher), professionnel (5 a 8 ruchers, 20 a 35 ruches par
rucher). Les visites s'etalent sur la saison en cours, les recoltes et le stock
d'atelier suivent le cheptel.

Le script **refuse d'ecrire ailleurs qu'en local** sans `--autoriser-production`.
Un jeu de donnees de test ne doit jamais atterrir sur la beta par megarde.

Mot de passe commun aux comptes generes : `motdepasse123`.

### Performance mesuree

Sur un profil professionnel genere (7 ruchers, 191 ruches, 1689 visites) :

| Endpoint | Temps |
|---|---|
| `/statistiques/cheptel` | 221 ms |
| `/statistiques/dernieres-visites` | 140 ms |
| `/statistiques/tableau-de-bord` | 112 ms |
| `/ruchers` | 18 ms |

## Tests de montee en charge

```bash
python3 scripts/seed_realistic_data.py --amateurs 4 --pluriactifs 3 --pros 1 \
  --sortie-json artifacts/charge/comptes.json
PALIER_MAX=60 bash scripts/linux/load_test.sh
```

Le scenario reproduit un usage reel : connexion, tableau de bord, consultation
des ruchers, selection d'un rucher, et une saisie de visite une fois sur quatre.
Les paliers montent progressivement puis redescendent.

Deux garde-fous : le script **et** le scenario k6 refusent de viser autre chose
que `127.0.0.1` sans `AUTORISER_PRODUCTION=1`. La beta et l'environnement de
test partagent le meme VPS.

Le tir s'interrompt automatiquement si le taux d'erreur depasse 2 % ou si le
p95 depasse 2 secondes.

### Resultats mesures

Jeu de donnees : 8 comptes, 244 ruches, 2 020 visites.

| Charge | Erreurs | p95 | Verdict |
|---|---|---|---|
| 20 utilisateurs | 0 % | 162 ms | confortable |
| 60 utilisateurs, pool par defaut | 1,45 % | 419 ms, pics a 60 s | saturation |
| 60 utilisateurs, pool dimensionne | 0 % | 450 ms | tenu |

### Ce que le test a revele

Le pool de connexions SQLAlchemy restait a sa valeur par defaut, soit 15
connexions, alors que PostgreSQL en accepte 100. Au-dela d'une vingtaine
d'utilisateurs simultanes, les requetes attendaient une connexion libre jusqu'au
delai d'expiration du client.

Le pool est desormais dimensionne via la configuration (`db_pool_size`,
`db_max_overflow`, `db_pool_timeout`). Le `pool_timeout` court fait echouer vite
plutot que laisser une requete pendre une minute.

## Simulation apiculteur professionnel (plan du 2026-10-03)

Objectif : faire jouer a un agent le role d'un apiculteur professionnel exigeant
(environ 8 ruchers, 200 ruches, transhumance, production de miel et d'essaims),
qui utilise l'application dans tous les sens et verifie l'effet de chaque action
sur la logique metier, les donnees et l'esthetique. A lancer apres les lots de
corrections de `suivi-projet.md`, pas avant : sinon la simulation ne fera que
redecouvrir des bugs deja connus.

### Principes d'economie

- Une seule spec dediee `tests/e2e/simulation-apiculteur.spec.js`, marquee
  `@simulation`, exclue de `gate_fast.sh` ; lancee a la demande en local ou sur
  `app-dev`, jamais sur la beta.
- L'UI est pilotee par Playwright uniquement pour ce qui est visible par
  l'apiculteur. Les effets metier (stock, reine active, tags, statistiques) sont
  verifies par appels API depuis le test (`request`), pas en lisant le DOM.
- Captures d'ecran limitees aux ecrans cles, une fois par largeur : 390 px
  (mobile) et 1440 px (desktop). Revue visuelle faite une seule fois sur ces
  captures.
- Les regles de calcul deja couvertes par pytest ne sont pas re-testees par
  navigateur.

### Scenarios

| # | Scenario | Verifications metier (API) | Verifications UI |
|---|---|---|---|
| S1 | Creation de 2 ruchers, ruches depuis le stock et ruches achetees | stock atelier decremente ou non selon le choix, en service recalcule par format | popups, messages, retour a la liste |
| S2 | Tournee de visites mobile, dont 2 visites hors ligne | visites synchronisees sans doublon, date de saisie conservee, tags et mouvements de cadres/hausses appliques | rendu 390 px sans debordement, file offline visible |
| S3 | Recolte par ruche puis par rucher entier | repartition confirmee, totaux par ruche/rucher/saison | bouton Nouvelle recolte depuis Visites et Ruchers |
| S4 | Remplacement de reine | ancienne reine terminee, nouvelle active, colonne Reine a jour | tableau Ruchers rafraichi |
| S5 | Transhumance, puis retour atelier (stocker / demonter) | rucher cible, materiel en service et stock coherents, historique conserve | popups de choix et de confirmation |
| S6 | Modification puis suppression d'un rucher | ruches conservees a la modification, suppression refusee tant qu'il reste des ruches | popup de deplacement puis confirmation |
| S7 | Statistiques saison en cours, saison derniere, ruche, rucher | chaque metrique suit la fenetre et la portee choisies | blocs contextuels, recherche avec autocompletion |
| S8 | Ruches a surveiller | tag automatique pose et retire selon les criteres valides | infobulle explicative |
| S9 | Navigation | actualisation conservant l'onglet et reinitialisant les filtres, clic logo vers tableau de bord, aide | aucun `pageerror` ni erreur console |

### Livrable

Un rapport `artifacts/simulation/rapport.md` (ignore par Git) : regard metier de
l'apiculteur, anomalies classees B/G/C, captures cles. Le resume et les
anomalies retenues sont reportes dans `suivi-projet.md`.
