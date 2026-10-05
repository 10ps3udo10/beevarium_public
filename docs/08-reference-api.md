# Reference API

Toutes les routes protegees attendent un jeton Bearer. Le client ne transmet jamais
de `user_id` : l'utilisateur est porte par le jeton.

La specification OpenAPI complete est generee par FastAPI et disponible sur
`/docs` de l'environnement cible.

---

## Authentification
Le backend expose maintenant une authentification simple par compte local:
- POST /auth/register
- POST /auth/login
- POST /auth/logout
- POST /auth/forgot-password
- POST /auth/reset-password
- GET /auth/me
- PATCH /users/me

Les routes metier protegees utilisent maintenant l'utilisateur porte par le token Bearer.
Le client ne doit plus envoyer `user_id` dans les payloads de creation de rucher ou de ruche.
La deconnexion invalide la session courante cote serveur; l'ancien token ne fonctionne plus apres `/auth/logout`.
Le champ `is_premium` est porte par le compte et sert a autoriser les fonctions premium comme l'IA vocale.
Le profil permet maintenant de mettre a jour le prenom depuis `/users/me`.
Le plan gratuit est limite a 2 ruchers. A partir du 3eme rucher, l'API renvoie `403` tant que le compte n'est pas premium.
Les e-mails sont normalises en minuscules a l'inscription, a la connexion et a la
demande de reinitialisation ; deux comptes ne peuvent pas differer seulement par
la casse de l'adresse.

Exemple Bash:

```bash
curl -X POST http://localhost:8000/auth/register \
	-H 'Content-Type: application/json' \
	-d '{
		"email": "toi@example.com",
		"prenom": "Paul",
		"password": "motdepasse123"
	}'
```

```bash
curl -X POST http://localhost:8000/auth/login \
	-H 'Content-Type: application/json' \
	-d '{
		"email": "toi@example.com",
		"password": "motdepasse123"
	}'
```

```bash
curl http://localhost:8000/auth/me \
	-H "Authorization: Bearer TON_TOKEN"
```

Exemple Bash pour creer un rucher authentifie:

```bash
curl -X POST http://localhost:8000/ruchers \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer TON_TOKEN" \
	-d '{
		"nom": "Rucher Maison",
		"latitude": 45.123456,
		"longitude": 3.123456,
		"type_terrain": "plaine",
		"statut_activite": "actif",
		"statut_peuplement": "peuple"
	}'
```

## Mot de passe oublie

Parcours en deux temps, sans authentification prealable.

`POST /auth/forgot-password` envoie un lien a usage unique valable 30 minutes.
La reponse est volontairement identique que le compte existe ou non, afin de ne
pas permettre de decouvrir quelles adresses sont inscrites. En environnement
`dev`, `test` ou `local` uniquement, la reponse peut inclure `debug_reset_url`
pour tester le parcours complet sans boite mail.

```bash
curl -X POST http://localhost:8000/auth/forgot-password \
	-H 'Content-Type: application/json' \
	-d '{"email": "toi@example.com"}'
```

`POST /auth/reset-password` consomme le jeton et applique le nouveau mot de passe.
Le jeton est a usage unique. La reinitialisation incremente `token_version`, ce
qui deconnecte toutes les sessions ouvertes.

```bash
curl -X POST http://localhost:8000/auth/reset-password \
	-H 'Content-Type: application/json' \
	-d '{
		"token": "JETON_RECU_PAR_EMAIL",
		"password": "nouveaumotdepasse123"
	}'
```

Reponses possibles:
- `200`: mot de passe mis a jour
- `400`: jeton inconnu, deja utilise ou expire
- `422`: mot de passe trop court ou adresse mal formee

Limite: 5 demandes par heure et par compte. Une nouvelle demande annule les liens
precedents encore valides.

## Dictionnaires de reference
Routes disponibles:
- GET /references/type-ruche
- GET /references/statut-ruche
- GET /references/action-visite
- GET /references/type-intervention
- GET /references/action-cadre
- GET /references/type-materiel
- POST /references/{reference_type}
- PUT /references/{reference_type}/{option_id}
- DELETE /references/{reference_type}/{option_id}

Exemple Bash:

```bash
curl http://localhost:8000/references/type-ruche \
	-H "Authorization: Bearer TON_TOKEN"
```

```bash
curl -X POST http://localhost:8000/references/type-ruche \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer TON_TOKEN" \
	-d '{
		"libelle": "Ruche test perso"
	}'
```

## Ruchers
La liste des ruchers peut maintenant etre filtree par:
- `nom`
- `statut_activite`
- `statut_peuplement`
- `type_terrain`

Archivage logique:
- `POST /ruchers/{rucher_id}/archive`
- passe le `statut_activite` a `inactif`
- le rucher reste consultable et filtrable dans l historique

Suppression : `DELETE /ruchers/{rucher_id}` renvoie `409` tant que le rucher
contient des ruches ; elles doivent d'abord etre deplacees (`POST /ruches/move`).

Exemple Bash:

```bash
curl "http://localhost:8000/ruchers?nom=Maison&statut_activite=actif" \
	-H "Authorization: Bearer TON_TOKEN"
```

## Ruches et tags

Une ruche creee dans un rucher recoit le statut systeme `Active` si aucun statut
n'est fourni. Une ruche creee dans l'Atelier reste identifiee par
`is_at_atelier=true` et n'est pas forcee en statut metier.

Tags manuels disponibles sur une ruche possedee par l'utilisateur :
- GET /ruches/{ruche_id}/tags
- POST /ruches/{ruche_id}/tags
- DELETE /ruches/{ruche_id}/tags/{tag_id}

Le client propose un catalogue de tags predefinis, avec favoris configurables
depuis `Profil > Reglages tags`. Les tags restent libres cote API pour ne pas
bloquer un usage terrain non prevu.

Effets automatiques actuellement actifs :
- `atelier` est expose comme tag derive pour une ruche dans l'Atelier ;
- `production`, `essaim recent`, `starter`, `finisseur`, `nuclei`,
	`banque a males` et `ruche piege` changent le type de ruche quand le type
	systeme correspondant existe ;
- `active`, `bourdonneuse`, `orpheline`, `quarantaine`, `suspicion maladie` et
	`colonie morte` changent le statut metier quand le statut systeme correspondant existe ;
- `nourrisseur present` et `grille a reine` cochent le materiel present ;
- `1 hausse posee` a `5 hausses posees` remplacent l'eventuel tag de quantite
	precedent, marquent la ruche comme ayant une hausse et ajoutent le mouvement
	de hausse necessaire au stock calcule. Retirer le tag ajoute le mouvement
	inverse.

Les autres tags du catalogue sont informatifs pour l'instant : ils ne modifient
pas le stock ni les donnees metier.

Les visites ne posent pas automatiquement de nouveaux tags : elles renvoient des
`tag_suggestions` a valider par l'utilisateur. Elles renvoient aussi
`tag_removal_suggestions` quand des tags ont ete retires automatiquement. Elles
retirent les tags reversibles quand un signal contraire est saisi, par exemple
`reine vue` retire `reine non vue` et `orpheline`, des reserves correctes
retirent `reserves faibles` et `a nourrir`.

Les tags evenementiels `candi pose`, `sirop donne`, `traitement varroa`,
`division prevue` et `essaim recent` expirent a la prochaine visite ou apres 30
jours, puis sont masques par l'API.

Limite volontaire : les suggestions restent simples et explicites ; les regles
avancees de priorite entre tags seront ajustees apres test terrain.

```bash
curl -X POST http://localhost:8000/ruches/ID_RUCHE/tags \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer TON_TOKEN" \
	-d '{"libelle": "a nourrir"}'
```

## Visites rucher
Routes disponibles:
- GET /visites-rucher
- GET /visites-rucher/{visite_rucher_id}
- POST /visites-rucher
- PUT /visites-rucher/{visite_rucher_id}
- DELETE /visites-rucher/{visite_rucher_id}

Exemple Bash:

```bash
curl -X POST http://localhost:8000/visites-rucher \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer TON_TOKEN" \
	-d '{
		"rucher_id": "ID_RUCHER",
		"note_meteo": "ensoleille",
		"impression_generale": "Belle activite",
		"note_globale": 4
	}'
```

## Visites ruche
Le payload de visite ruche accepte maintenant un suivi explicite des hausses via `mouvements_hausses`.
Chaque mouvement porte un `quantite_delta`:
- positif: pose de hausse
- negatif: retrait de hausse

Validation metier:
- une visite ne peut pas etre enregistree si elle ne contient ni observation, ni action, ni intervention, ni mouvement
- en cas de lien avec une visite rucher, la visite rucher doit appartenir au meme rucher que la ruche

Tags hors ligne : `POST /visites` accepte `tags_ajoutes` (liste de libelles,
20 au plus, 50 caracteres chacun). Ils sont poses dans la meme transaction que
la visite, donc rejoues sans doublon avec la meme `Idempotency-Key`. Un tag deja
present ou refuse par les regles de tags est ignore sans bloquer la visite.

Routes complementaires:
- `PATCH /visites/{visite_id}` (edition partielle)
- `GET /visites/synthese/periode`

Parametres synthese periode:
- `start_date` (YYYY-MM-DD)
- `end_date` (YYYY-MM-DD)
- `rucher_id` (optionnel)
- `ruche_id` (optionnel)

La synthese renvoie des agregats terrain sur la periode: total visites ruche/rucher, repartition manuelle vs ia_vocale, brouillons IA, moyennes de notes et taux reine vue.

Gardes-fous de validation:
- `GET /visites`: `source_saisie` doit etre `manuelle` ou `ia_vocale`
- `GET /visites`: `statut_validation` doit etre `brouillon` ou `valide`
- `GET /visites/synthese/periode`: `start_date` doit etre <= `end_date`
- `PATCH /visites/{visite_id}`: payload vide refuse

### Historique pagine

`GET /visites/historique` retourne l'historique leger du compte, avec le nom du
rucher et l'identifiant de ruche. Il accepte `rucher_id`, `ruche_id`, `search`,
`source_saisie`, `statut_validation`, `start_date`, `end_date` et `limit`
(`1` a `200`, `100` par defaut). La reponse contient `total` et les visites de
la page, triees de la plus recente a la plus ancienne.

## IA vocale Premium
Une route mockable permet de simuler l analyse d une transcription terrain et, si besoin, de sauvegarder un brouillon de visite.

Route disponible:
- `POST /ia-vocale/transcrire-audio`
- `POST /ia-vocale/analyser-visite`
- `GET /ia-vocale/brouillons`

Comportement:
- `transcrire-audio` accepte un fichier audio (multipart) et renvoie une transcription mockable
- prend une `transcription` et une `ruche_id`
- extrait une structure de visite simple
- renvoie `statut_validation` a `brouillon` si la transcription est incomplete ou ambigue
- enregistre un brouillon si `save_as_draft=true`

Exemple Bash (upload transcription):

```bash
curl -X POST http://localhost:8000/ia-vocale/transcrire-audio \
	-H "Authorization: Bearer TON_TOKEN" \
	-F "audio_file=@visite.wav"
```

Exemple Bash:

```bash
curl -X POST http://localhost:8000/ia-vocale/analyser-visite \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer TON_TOKEN" \
	-d '{
		"ruche_id": "ID_RUCHE",
		"transcription": "reine vue, ponte presente, couvain 4 cadres, reserves correct, agressivite 2, note 4, 2 hausses",
		"save_as_draft": true
	}'
```

Revue des brouillons IA:
- `GET /ia-vocale/brouillons?ruche_id=...`

## Cadres
Les cadres ont maintenant une synthese d age par ruche a partir des mouvements saisis pendant les visites.

Routes disponibles:
- `GET /cadres/stats/par-ruche`
- `GET /cadres/alertes/renouvellement`

Les retours incluent:
- la repartition par age de cire
- l age moyen et maximum
- un indicateur d alerte si des cadres ont plus de 3 ans

Exemple Bash:

```bash
curl http://localhost:8000/cadres/stats/par-ruche \
	-H "Authorization: Bearer TON_TOKEN"
```

Exemple Bash:

```bash
curl -X POST http://localhost:8000/visites \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer TON_TOKEN" \
	-d '{
		"ruche_id": "ID_RUCHE",
		"visite_rucher_id": null,
		"reine_vue": true,
		"presence_ponte": true,
		"etat_couvain": "normal",
		"nombre_cadres_couvain": 4,
		"reserves_nourriture": "correct",
		"agressivite": 2,
		"note_ruche": 4,
		"nombre_cadres_total": 10,
		"source_saisie": "manuelle",
		"statut_validation": "valide",
		"action_ids": [],
		"interventions": [],
		"mouvements_cadres": [],
		"mouvements_hausses": [
			{
				"quantite_delta": 2,
				"note": "Pose de 2 hausses"
			}
		]
	}'
```

## Indicateurs du tableau de bord

`GET /statistiques/cheptel` (filtres optionnels `rucher_id`, `ruche_id`) :

- `ruches_suivies` : ruches en rucher, hors Atelier ;
- `ruches_visitees_annee` : ruches en rucher visitees depuis le 1er janvier ;
- `ruches_sans_visite_recente` : ruches en rucher sans visite depuis 30 jours ;
- `reines_plus_2_ans` : reines actives de 2 ans ou plus.

`GET /statistiques/tableau-de-bord` accepte `start_date` et `end_date`
(YYYY-MM-DD) en plus de `year`, `rucher_id` et `ruche_id`. Visites, recoltes et
miel suivent cette fenetre ; a defaut, l'annee civile (`year` ou annee en cours).
La reponse renvoie la fenetre appliquee (`start_date`, `end_date`). Une date de
debut posterieure a la date de fin renvoie `422`.

## Fiches Statistiques

- `GET /statistiques/fiche-ruche?ruche_id=...&start_date=...&end_date=...` :
  ruche, reine active et historique, materiel porte, visites de la fenetre,
  mouvements de cadres, recoltes, transvasements et motifs de surveillance.
- `GET /statistiques/fiche-rucher?rucher_id=...&start_date=...&end_date=...` :
  effectifs par format et type, reines, visites, note et couvain moyens, miel
  de chaque ruche (y compris 0 kg) et ruches a surveiller.

Sans dates, la fenetre est la saison en cours (annee civile).

## Creation rapide, modeles et import

- `POST /ruchers/creation-rapide` (tous comptes) : `{rucher: {nom, type_terrain...}}` ou
  `{rucher_id}`, et `ruches` (1 a 200) `{identifiant_personnalise, ref_type_ruche_id?, format_ruche?,
  nombre_cadres?, has_corps, has_toit, has_plancher, has_grille_a_reine,
  has_nourrisseur, has_hausse, has_partition}`. Tout ou rien : `409` si un
  identifiant est deja pris ou en double, `403` au-dela de 2 ruchers en
  gratuit. Nouveau materiel (stock inchange), sans reine. Cadres par defaut
  selon le format.
- `GET/POST /modeles-ruche`, `DELETE /modeles-ruche/{id}` (Premium, `403`
  sinon) : format, cadres et elements reutilisables ; nom unique par compte.
- `POST /import/ruches/analyse` (Premium) `{nom_fichier, contenu_base64,
  correspondance?}` : CSV (`;`, `,` ou tabulation, UTF-8 ou Windows-1252) ou
  `.xlsx` ; devine les colonnes `rucher`, `identifiant`, `type_ruche`, `format`,
  `nombre_cadres`, verifie chaque ligne (formats tolerants : `D10`, `dadant 10`,
  fautes proches) et renvoie `lignes` avec `erreurs`, sans rien creer.
- `POST /import/ruches/verifier` `{lignes}` : reverifie des lignes corrigees.
- `POST /import/ruches` `{lignes}` : cree ruchers manquants et ruches si aucune
  ligne n'est en erreur (`422` sinon, rien n'est cree). 1 000 lignes au plus.

`POST /visites` accepte `ref_type_ruche_id` : le type de la ruche est mis a jour
avec la visite (hors ligne compris, meme cle d'idempotence).

## Nombre de cadres de la ruche

`POST /visites`, `PUT` et `PATCH /visites/{id}` : quand la visite est la plus
recente de la ruche, son `nombre_cadres_total` devient le `nombre_cadres` de la
ruche. Une visite plus ancienne ne change pas la fiche.

## Reine de la fiche ruche

- `POST /ruches` et `PUT /ruches/{id}` acceptent `reine_date_mise_en_place`
  (date, jour J) ; l'age de la reine se compte depuis ce jour et
  `reine_annee_marquage` suit sa date. Sans date : reine de l'annee en cours
  datee du jour de saisie, annee passee datee du 1er juillet.
- `GET /ruches` et `GET /ruches/{id}` renvoient `reine_date_mise_en_place` de
  la reine active (`null` sans reine active).

## Cycle de vie du materiel

- `POST /ruches` accepte `origine_materiel` (`achat` par defaut, ou `stock`) et
  `elements_stock` (`plancher`, `corps`, `couvre_cadre`, `toit`, `partition`,
  `grille`, `nourrisseur`, `cadres`). `stock` retire ces elements du stock range
  au format de la ruche ; `409` si une quantite manque.
- `POST /ruches/demontage` `{ruche_ids, elements_stock?}` : elements remis en
  stock, reine active terminee, ruche archivee (`archived_at`,
  `motif_archive=demontee`). Les ruches archivees sortent de `GET /ruches` et du
  stock ; leur historique reste dans les statistiques ; `POST /visites` sur elles
  renvoie `409`.
- `POST /ruches/{id}/transvasements` et champ `transvasement` de `POST /visites` :
  `format_apres`, `provenance` (`stock`, `achat`, `ruche_atelier` +
  `ruche_atelier_id`), `elements`, `cadres_transferes`, `cadres_ajoutes`,
  `annee_cire`, `nouvel_identifiant`. Dans une visite, un transvasement
  impossible n'empeche pas l'enregistrement : il est signale dans
  `avertissements`. `GET /ruches/{id}/transvasements` liste l'historique.
- `POST /visites` accepte `date_visite` (heure de saisie hors ligne).
- `GET /materiel-atelier/stats/stock-synthetique-par-type` ajoute
  `quantite_ruches_atelier_calculee` (materiel des ruches rangees montees),
  inclus dans `quantite_stock_totale`.

## Ruches a surveiller

Le tag `a surveiller` peut etre `derive` (source `derive`) : calcule a la lecture
selon les criteres de `backend/app/surveillance.py`, il n'est pas stocke et
n'apparait pas si le tag a ete pose a la main.

## Graphique du tableau de bord

`GET /statistiques/visites-par-mois` retourne le nombre de visites ruche par
mois de l'annee civile en cours. La reponse contient toujours les douze mois de
janvier a decembre ; un mois sans visite retourne `count: 0`.

```json
{
	"season_start_year": 2026,
	"months": [
		{ "month": "2026-01", "count": 12 },
		{ "month": "2026-02", "count": 8 }
	]
}
```

## Recoltes
Routes disponibles:
- GET /recoltes
- GET /recoltes/stats/par-ruche
- GET /recoltes/stats/par-rucher
- GET /recoltes/stats/par-annee
- GET /recoltes/stats/periode-glissante
- GET /recoltes/stats/par-saison
- GET /recoltes/{recolte_id}
- POST /recoltes
- PUT /recoltes/{recolte_id}
- DELETE /recoltes/{recolte_id}

Parametres disponibles:
- `GET /recoltes`: `ruche_id`, `year`, `start_date`, `end_date`
- `GET /recoltes/stats/par-ruche`: `year`, `start_date`, `end_date`
- `GET /recoltes/stats/par-rucher`: `year`, `start_date`, `end_date`
- `GET /recoltes/stats/periode-glissante`: `days`
- `GET /recoltes/stats/par-saison`: `season_start_month`

Semantique saison apicole pour `GET /recoltes/stats/par-saison`:
- Par defaut, `season_start_month=3` (visite de printemps).
- La saison de production est rattachee a l annee de demarrage: `Saison 2026`.
- Les visites d hiver (nourrissement, varroa, etc.) restent possibles dans le metier, mais les stats recoltes sont groupees sur la saison de production.

Exemple Bash:

```bash
curl -X POST http://localhost:8000/recoltes \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer TON_TOKEN" \
	-d '{
		"ruche_id": "ID_RUCHE",
		"visite_ruche_id": "ID_VISITE_RUCHE",
		"poids_miel_kg": 18.5
	}'
```

Exemple Bash pour les statistiques:

```bash
curl http://localhost:8000/recoltes/stats/par-ruche \
	-H "Authorization: Bearer TON_TOKEN"
```

```bash
curl http://localhost:8000/recoltes/stats/par-rucher \
	-H "Authorization: Bearer TON_TOKEN"
```

```bash
curl "http://localhost:8000/recoltes/stats/par-ruche?year=2026" \
	-H "Authorization: Bearer TON_TOKEN"
```

```bash
curl "http://localhost:8000/recoltes/stats/periode-glissante?days=90" \
	-H "Authorization: Bearer TON_TOKEN"
```

```bash
curl "http://localhost:8000/recoltes/stats/par-saison?season_start_month=3" \
	-H "Authorization: Bearer TON_TOKEN"
```

## Materiel atelier
Routes disponibles:
- GET /materiel-atelier
- GET /materiel-atelier/stats/stock-synthetique-par-type
- GET /materiel-atelier/{materiel_id}
- POST /materiel-atelier
- PUT /materiel-atelier/{materiel_id}
- DELETE /materiel-atelier/{materiel_id}

Champs retour utiles:
- `quantite_en_service`: valeur manuelle stockee
- `quantite_en_service_manuelle`: alias explicite de la valeur manuelle
- `quantite_en_service_calculee`: calcul automatique partiel
- `quantite_en_service_totale`: manuel + calcule
- `format_materiel`: format de la ligne (renvoye depuis 1.36.2)

Une seule ligne par type et format (index `uq_materiel_atelier_type_format`) :
- `POST` sur un couple type + format existant ajoute `quantite_atelier` a la ligne existante
- `PUT` vers un couple deja porte par une autre ligne : `409`
- `Cadre` et `Partition` suivent le format du cadre : `ruchette` est range en `dadant`
  (une ruchette Dadant porte des cadres Dadant) ; leurs quantites calculees en `dadant`
  incluent les ruchettes

Calcul automatique actuel:
- `Corps`, `Plancher`, `Couvre-cadre`, `Toit`: derives du nombre de ruches declarees hors atelier
- `Hausse`: derive du journal `mouvements_hausses` cumule sur les visites de ruche

Endpoint de stock synthetique par type:
- `GET /materiel-atelier/stats/stock-synthetique-par-type`
- Agrege par type de materiel (systeme + types personnalises du compte)
- Retourne, pour chaque type: atelier total, service manuel total, service calcule, service total et stock total

Exemple Bash:

```bash
curl -X POST http://localhost:8000/materiel-atelier \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer TON_TOKEN" \
	-d '{
		"ref_type_materiel_id": "ID_TYPE_MATERIEL",
		"modele": "Dadant 10",
		"quantite_atelier": 12,
		"quantite_en_service": 4
	}'
```

```bash
curl http://localhost:8000/materiel-atelier/stats/stock-synthetique-par-type \
	-H "Authorization: Bearer TON_TOKEN"
```

## Preparation V2 Apple/Google
La table users porte deja les champs suivants pour preparer l ouverture aux providers externes:
- auth_provider: local, apple, google
- provider_subject: identifiant externe du provider

La V2 pourra donc ajouter un flux OAuth Apple/Google sans casser le modele utilisateur courant.

## Tests d integration API
Une base de tests pytest est disponible dans `backend/tests/integration/test_api_integration.py`.

Couverture initiale:
- Authentification: register, login, me
- Securite ownership: isolation entre utilisateurs sur les ruchers
- Metier: stats recoltes et endpoint stock materiel synthetique par type

Pre-requis:
- API et DB lancees localement (ex: `docker compose --env-file .env up -d --build`)
- Python avec dependances de dev installees

Installation dependances de test:

```bash
pip install -r backend/requirements-dev.txt
```

Execution:

```bash
pytest backend/tests/integration -q
```

Configuration URL API (optionnel):
- Variable `BEEVARIUM_API_URL` (defaut: `http://localhost:8000`)

## Contrat d erreur API
Les erreurs HTTP suivent maintenant un format unifie:

```json
{
	"error": {
		"code": "http_404",
		"message": "Rucher introuvable"
	}
}
```

Cas de validation:

```json
{
	"error": {
		"code": "validation_error",
		"message": "Validation error",
		"details": [
			{
				"loc": ["body", "email"],
				"msg": "value is not a valid email address",
				"type": "value_error.email"
			}
		]
	}
}
```

Les exemples de payload sont visibles dans l OpenAPI generee par FastAPI pour les routes auth, ruchers, ruches, visites, recoltes et materiel atelier.

## Observabilite minimale
L API journalise maintenant chaque requete avec:
- un `request_id` recu via `X-Request-ID` ou genere automatiquement
- la methode, le chemin, le statut et la duree
- l identifiant utilisateur courant quand la requete est authentifiee

Le endpoint health renvoie aussi des metadonnees utiles:
- `status`
- `database`
- `app_version`
- `environment`

## Journal API persistant
Les requetes HTTP sont aussi enregistrees en base dans `api_events`.

Route disponible:
- `GET /events/api` pour lire les derniers evenements du compte courant

Champs stockes:
- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`
- `error_code`
- `error_message`
- `created_at`

Exemple:

```bash
curl http://localhost:8000/events/api?limit=10 \
	-H "Authorization: Bearer TON_TOKEN"
```
