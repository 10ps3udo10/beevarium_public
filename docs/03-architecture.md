# Architecture technique

## 1. Stack

| Couche | Choix | Pourquoi |
|---|---|---|
| API | FastAPI + SQLAlchemy + Pydantic | Typage fort, OpenAPI generee, rapide a iterer |
| Base | PostgreSQL 16 | Relationnel, contraintes metier, extensions disponibles |
| Client | HTML/CSS/JS servi par l'API sous `/app` | Zero CORS, zero build, un seul artefact a deployer |
| Offline | IndexedDB | Objets structures et payloads volumineux |
| Execution | Docker Compose | Environnement identique en local et sur le VPS |
| Proxy | Caddy | Certificats Let's Encrypt automatiques |
| Mobile (a venir) | Capacitor | Encapsule le client web sans reimplementation |

Le client web est servi par l'API elle-meme. C'est ce qui permet de n'avoir qu'un
seul conteneur a deployer et d'eviter toute configuration CORS entre le front et
l'API.

## 2. Structure du depot

```
backend/app/          API FastAPI
  routers/            un module par domaine metier
  models.py           mapping SQLAlchemy
  schemas.py          contrats Pydantic
  security.py         hachage PBKDF2, JWT, revocation par token_version
  static/app/         client web
db/init/              schema initial et seeds de references
db/migrations/        migrations incrementales horodatees
scripts/linux/        outillage de verification et de deploiement
ansible/              orchestration locale
docs/                 documentation projet
```

## 3. Authentification

- Hachage PBKDF2-SHA256, 100 000 iterations, sel par utilisateur
- JWT signe en HS256, portant `sub`, `exp`, `type` et `ver`
- La revocation passe par `token_version` : incrementer le compteur en base
  invalide immediatement tous les jetons deja emis pour cet utilisateur
- `auth_provider` et `provider_subject` sont deja presents en base pour accueillir
  Apple et Google sans casser le modele

## 4. Contrat d'erreur

Toutes les erreurs suivent la meme enveloppe :

```json
{ "error": { "code": "http_404", "message": "Rucher introuvable" } }
```

Les erreurs de validation ajoutent un tableau `details` reprenant les champs en
faute.

## 5. Modele freemium

La limite est appliquee cote serveur, jamais cote client :

- Compte Free : maximum 2 ruchers, la creation du 3e retourne `403`
- Fonctions IA vocale : reservees aux comptes `is_premium`, sinon `403`

---

# Offline et synchronisation

## Objectif
Permettre la saisie d une visite terrain sans reseau, puis sa synchronisation fiable au retour de la connexion, sans perte ni ecrasement silencieux.

## Perimetre du premier increment
Le premier increment offline couvre uniquement les visites manuelles de ruche. Les creations de rucher, de ruche, les remplacements de reine et les operations complexes restent en ligne jusqu a validation du mecanisme.

## Decisions

### Stockage local
- Utiliser IndexedDB dans le client web, pas localStorage, pour conserver des objets structures et des payloads volumineux.
- Une base locale contient une file `sync_operations` et un cache de lecture minimal.
- Les donnees sensibles restent limitees au navigateur de l utilisateur et sont supprimees a la deconnexion explicite.

### Format d une operation
Chaque operation de la file contient:
- `operation_id`: UUID genere cote client et idempotent.
- `entity_type`: `visite_ruche`.
- `entity_id`: UUID client genere avant envoi.
- `operation`: `create` ou `update`.
- `payload`: corps JSON complet de l operation.
- `created_at`: horodatage UTC.
- `attempts`: nombre de tentatives.
- `status`: `pending`, `syncing`, `synced`, `conflict`, `failed`.
- `last_error`: dernier message non sensible.

### Idempotence serveur
- Ajouter un header `Idempotency-Key: operation_id` sur les creations offline.
- Le serveur doit enregistrer les cles deja traitees par utilisateur.
- Une repetition de la meme operation retourne le resultat precedent au lieu de creer une seconde visite.
- La cle est liee a l utilisateur authentifie, jamais globale.

### Reprise reseau
- Le client detecte `online`/`offline`, mais considere l API comme seule source de verite.
- A la reconnexion, les operations sont envoyees dans l ordre de creation.
- Une seule operation est synchronisee a la fois pour le premier increment.
- Backoff progressif: 1 s, 3 s, 10 s, puis attente d une action utilisateur.
- Les erreurs 401 stoppent la file et demandent une reconnexion.
- Les erreurs 409 deviennent des conflits explicites.

### Conflits
Un conflit ne doit jamais etre ecrase silencieusement.

Pour une visite:
- comparer `updated_at` serveur et `client_base_version` quand le serveur supportera la version;
- conserver le payload local dans la file;
- afficher les valeurs locales et serveur;
- proposer `garder ma saisie`, `garder serveur` ou `fusionner`;
- journaliser la decision.

Le premier increment peut commencer par une regle stricte: toute modification d une visite deja modifiee serveur devient `conflict`, sans fusion automatique.

## Contrat API a ajouter

### Creation idempotente
`POST /visites` accepte:
- header `Idempotency-Key` obligatoire pour les operations offline;
- reponse identique lors d une repetition de la meme cle.

### Synchronisation
Le client reutilise les endpoints metier existants. Un endpoint de diagnostic peut etre ajoute plus tard:
- `GET /sync/status` pour retourner les compteurs serveur et la version de protocole.

### Version de protocole
Le client envoie `X-Sync-Protocol: 1` afin de permettre une evolution ulterieure sans ambiguite.

## Etats UX
Toujours afficher un etat visible pres du formulaire:
- `En ligne`;
- `Hors ligne - saisie locale`;
- `A synchroniser (N)`;
- `Synchronisation en cours`;
- `Conflit a resoudre`;
- `Echec - nouvelle tentative`.

Une visite locale doit rester consultable dans la liste avec un badge `A synchroniser`, meme sans reseau.

## Etat d implementation
- [FAIT] IndexedDB et file locale des visites manuelles cote client.
- [FAIT] Etats UX en ligne/hors ligne et compteur des operations en attente.
- [FAIT] Synchronisation sequentielle au retour reseau avec `Idempotency-Key`.
- [FAIT] Table serveur des cles d idempotence par utilisateur.
- [FAIT] Detection serveur des conflits par version et tests dedies.
- [FAIT] Resolution UX explicite des conflits: garder local, garder serveur ou fusion manuelle.
- [A FAIRE] Validation sur navigateur mobile reel avant d etendre aux ruchers, ruches et reines.

## Criteres de sortie
- Une visite saisie hors reseau est visible localement.
- Le retour reseau la synchronise une seule fois.
- Une repetition de requete ne cree pas de doublon.
- Une erreur 401 bloque la file sans perte.
- Un conflit est visible et resolvable explicitement.
- Les tests de reprise et idempotence sont automatises.

## Hors perimetre initial
- Synchronisation automatique des capteurs.
- Fusion intelligente de champs.
- Edition offline des dictionnaires.
- Synchronisation de fichiers audio.
- Modification offline des structures ruchers/ruches.

## Evaluation : remplacer JavaScript par Rust (2026-10-03)

**Question du concepteur** : Rust peut-il remplacer JavaScript « en mieux », y
compris pour la future version mobile ?

**Constat** :

- Le JavaScript de Beevarium est uniquement le client navigateur
  (`backend/app/static/app/app.js` et ses modules `js/`, sans build). Le
  backend est en Python ; les scripts d'exploitation sont en Bash.
- Un navigateur n'execute pas Rust directement. Rust y tourne compile en
  WebAssembly (frameworks Leptos, Yew, Dioxus), et chaque acces au DOM passe par
  une couche de liaison JavaScript.
- Le client de Beevarium manipule surtout des formulaires, des popups, des
  tableaux et des appels API. Son temps d'execution est domine par le reseau et
  la base de donnees, pas par le calcul : Rust n'apporterait pas de gain
  perceptible.

**Couts d'un portage** :

- Reecriture complete du client et de la file offline IndexedDB, avec un risque
  de regression eleve sur des parcours valides par le concepteur.
- Ajout d'une chaine de compilation (cargo, wasm-pack, bundler) la ou le projet
  n'a aujourd'hui aucun build frontend ; paquet initial plus lourd a charger sur
  mobile en zone peu couverte.
- Tests Playwright a reprendre, competences Rust necessaires pour maintenir.

**Mobile** : la trajectoire retenue est Capacitor, qui embarque le client web
existant. Rust ne simplifie ni Capacitor, ni les achats in-app, ni les plugins
natifs. La transcription Whisper locale passera par un plugin natif existant
(whisper.cpp), sans besoin d'ecrire du Rust.

**Decision recommandee** : ne pas porter le client en Rust. Les vrais gains
viennent de la qualite du JavaScript existant : decouper `app.js` en modules ES
natifs (sans build), supprimer les doublons et le code mort, et ajouter un
controle de types leger (JSDoc + `// @ts-check`) si besoin. Rust pourra etre
reconsidere pour un composant isole et gourmand en calcul (par exemple un
traitement audio), jamais pour l'interface.

## Client web : modules ES

Depuis `1.35.0`, le client est decoupe en modules ES natifs, sans build ni
bundler. `index.html` charge `app.js` (`type="module"`), qui ne contient que
la liaison des evenements (`bindEvents`) et le demarrage (`bootstrap`). Le
reste vit dans `backend/app/static/app/js/` :

| Module | Role |
|---|---|
| `dom.js`, `state.js` | references DOM, etat partage et constantes (catalogue de tags...) |
| `utils.js`, `api.js` | utilitaires d'affichage, appels API avec reprise |
| `offline.js` | file IndexedDB, synchronisation unique, conflits |
| `navigation.js`, `auth.js` | onglets dans l'URL, menu, session, profil |
| `ruchers.js`, `ruches.js`, `scope.js` | ruchers, ruches, selection, transhumance, portee rucher/ruche |
| `visites.js`, `tags.js`, `transvasement.js` | saisie et edition de visite, tags, transvasement |
| `recoltes.js`, `reines.js`, `atelier.js` | recoltes, reines, stock et ruches de l'Atelier |
| `dashboard.js`, `statistiques.js` | tableau de bord, statistiques et fiches |
| `ia.js` | brouillons de saisie vocale |

Regles : chaque module exporte ses fonctions et importe explicitement ce qu'il
utilise ; l'etat mutable passe par l'objet `state` (une liaison importee ne se
reassigne pas). Les dependances circulaires sont permises entre fonctions,
pas pour des valeurs calculees au chargement. `check_client_assets.sh`
verifie la syntaxe de chaque module.

