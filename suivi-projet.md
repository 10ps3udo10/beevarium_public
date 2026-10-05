# Suivi de projet Beevarium

Document de pilotage : ou en est le projet, ce qui est en cours, ce qui reste.
Les journaux de session detailles sont dans l'historique Git du depot prive.

**Derniere mise a jour : 2026-10-05**

---

## 1. Etat en une minute

| | |
|---|---|
| Beta | `v1.36.3-journal-6-mois` sur https://beta.beevarium.fr (2026-10-05, deployee par `deploy.sh`, saine, migrations jusqu'a `20261008`, sauvegarde `beevarium-target-20261005-121512.sql`) |
| Environnement de test | `~/app-dev` sur le VPS, port interne 18001 : `v1.36.3`, gate vert le 2026-10-05 |
| Version locale | `1.36.3`, identique a la beta |
| Accueil | https://beevarium.fr et https://www.beevarium.fr (page statique `site/`, Caddy) |
| Depot public | `github.com/10ps3udo10/beevarium_public`, sans licence, un commit, a jour en `1.36.3` |
| Hebergement | VPS Debian 12, Caddy + Docker Compose ; acces dans `AGENTS.local.md` (non versionne) |
| Sauvegardes | locales 03h15 UTC (14 jours), hors site chiffrees 03h45 UTC, restaurations de controle le dimanche |
| Supervision | alertes e-mail toutes les 5 minutes vers `contact@beevarium.fr` (testees de bout en bout le 2026-10-04) |
| Testeurs | beta ouverte : inscription libre depuis l'ecran de connexion, comptes Premium pendant la beta ; premier testeur invite le 2026-10-04 |

**Prochaine etape** : accompagner les premiers testeurs (retours hebdomadaires
via `list_beta_feedback.sh`), test terrain sur telephone par le concepteur,
remise a niveau de `~/app-dev`.

---

## 2. Decisions du concepteur

| # | Date | Sujet | Decision |
|---|---|---|---|
| D1 | 2026-10-03 | Ruches a surveiller | Reine de 2 ans ou plus ; note <= 2 ; pas de ponte ou reine non vue ; couvain < 30 % en saison ; pas de visite depuis 21 j (avril-septembre) ou 60 j ; tag `orpheline`. Tag `a surveiller` pose et retire automatiquement, sans toucher un tag manuel. |
| D2 | 2026-10-03 | Saison | Annee civile ; `Saison derniere` = annee civile precedente. |
| D3 | 2026-10-03 | Demontage d'une ruche | Archivage : elements remis en stock, reine terminee, historique conserve dans les statistiques. |
| D4 | 2026-10-03 | Creation de ruche | Origine `Stock atelier` (refus si insuffisant) ou `Nouveau materiel` (libelle qui remplace `Achat` depuis 1.36.0). |
| D5 | 2026-10-03 | Publication | Depot public a historique neuf, sans licence ; le depot d'exploitation reste prive. Mise a jour par `export_public.sh` puis envoi force, apres feu vert. |
| F9 | 2026-10-03 | Transvasement | La fiche suit la colonie (identifiant conserve, nouveau possible) ; ancien contenant en stock ; provenance stock, nouveau materiel ou ruche preparee a l'Atelier ; tag `production` suggere. |
| A1 | 2026-10-04 | Recolte d'un rucher entier | Repartition a parts egales conservee ; la confirmation avertit et affiche le poids par ruche. |
| A2 | 2026-10-04 | Age de la reine | Compte depuis le jour de mise en place (`reine_date_mise_en_place`) ; sans date : jour de saisie pour l'annee en cours, 1er juillet pour une annee passee. |
| A3 | 2026-10-04 | Couvre-cadres | Un par ruche par defaut, remis en stock au demontage. |
| A4 | 2026-10-04 | Suppression d'un rucher | Les ruches vivantes ne vont qu'a un autre rucher (transhumance), jamais a l'Atelier. |
| A5 | 2026-10-04 | Ouverture beta | Editeur particulier anonyme (LCEN art. 6-III-2), contact `contact@beevarium.fr` ; testeurs Premium ; inscription libre, sans code d'invitation. |
| A6 | 2026-10-04 | Saisie en nombre | Creation rapide gratuite (premiere etape de la prise en main) ; modeles et import tableur en Premium, grises en gratuit ; pas de duplication de rucher ; numerotation automatique modifiable ; reines saisies ensuite a la main ; type de ruche dans la creation, l'import et la visite. |

---

## 3. Livraisons du 2026-10-03 au 2026-10-04

### Retours concepteur 2026-09-23 / 2026-10-02 : lots L1 a L8 (v1.34.0)

- **L1 bugs** : `Nouvelle recolte` depuis Visites ; suppression d'un rucher non vide refusee (`409`) ; colonne `Reine` a jour apres remplacement ; jauge Visites sans les ruches Atelier ; statistiques qui suivent fenetre et portee ; recherche avec autocompletion ; Visites en 390 px ; popup tags ; onglet conserve dans l'URL ; tags choisis hors ligne ; `References materiel` et reines de plus de 2 ans au tableau de bord.
- **L2 consolidation** : resume reine et table `reines` synchronises (migration `20261003`) ; idempotence offline sous verrou PostgreSQL ; controle d'appartenance centralise (`ownership.py`).
- **L3 UX** : rucher modifiable et supprimable ; popup de visite rucher puis ruche ; en-tete, logo, aide, infobulles.
- **L4 materiel** : creation depuis le stock ou en nouveau materiel ; stocker ou demonter a l'Atelier ; transvasement (journal `ruche_transvasements`) ; calcul du stock corrige ; heure de saisie conservee hors ligne (migration `20261004`).
- **L5** : ruches a surveiller automatiques (`surveillance.py`).
- **L6** : statistiques par portee, fiches rucher et ruche.
- **L7** : simulation d'une journee d'apiculteur professionnel (`simulation_apiculteur.sh`, refuse la beta).
- **L8** : menage du depot, acces prives dans `AGENTS.local.md`, README et suivi condenses, export public.

### Tour concepteur (v1.34.1)

Bouton `Modifier le rucher` rendu visible (en-tete masque par une regle CSS) ;
plusieurs tags a la fois ; nouvelle visite pre-remplie (cadres et couvain) ;
transhumance obligatoire avant suppression d'un rucher ; mouvements de cadres
qui ajustent le total de la visite, fiche ruche alignee sur la derniere visite.

### Ouverture aux testeurs (v1.35.0 a v1.35.4)

- Pages legales completes (mentions, confidentialite, conditions beta).
- Page d'accueil `beevarium.fr` (`site/`, `deploy_site.sh`).
- Alertes e-mail (`scripts/watchdog.py`, timer `beevarium-watchdog`), heures en heure de Paris.
- Client decoupe en modules ES (`static/app/js/`), `app.js` reduit a `bindEvents` et `bootstrap`.
- Inscription depuis l'ecran de connexion (aucun formulaire n'existait : le premier testeur etait bloque), sans code d'invitation.
- Badge d'en-tete calcule depuis `/health` : `Beta`, `Test` ou `Local`.

### Saisie en nombre (v1.36.0 et v1.36.1)

- **Creation rapide** (gratuite) : rucher et jusqu'a 200 ruches en une transaction ; type (Production par defaut), format, cadres, prefixe et numero de depart (suite du plus grand existant), elements ; apercu modifiable ligne par ligne ; `Ajouter plusieurs ruches` dans un rucher existant.
- **Modeles de ruche** (Premium) : type, format, cadres et elements reutilisables (migrations `20261005`, `20261006`).
- **Import CSV / Excel** (Premium) : modele telechargeable, colonnes devinees et modifiables, formats et types tolerants, apercu avec erreurs corrigeables sur place, rien n'est cree tant qu'une ligne est en erreur (dependance `openpyxl`).
- **Type de ruche modifiable pendant une visite**, hors ligne compris.
- Oeil sur les champs mot de passe.

### Retours testeurs du 2026-10-05 (v1.36.2)

Retours du concepteur en testeur (formulaire feedback). Saisie hors ligne et
mot de passe oublie valides sur telephone ; e-mail de reset arrive en
indesirables (DKIM actif chez OVH, domaine inscrit sur Google Postmaster : la
reputation se construit, rien a corriger dans le code).

- **Zoom iOS sur les champs** : texte des champs a 16 px sur ecran tactile (`pointer: coarse`), zoom manuel conserve.
- **Stock : un retrait devenait un ajout** : l'API ne renvoyait pas `format_materiel`, le client ne retrouvait pas la ligne et `Modifier` en creait une nouvelle (3 lignes `Corps Dadant` sur la beta). Format renvoye, une seule ligne par type et format (index unique, doublons fusionnes par la migration `20261007`), `POST` sur un couple existant additionne, boutons `-` / `+` et rappel « quantite totale rangee ».
- **Cadres et partitions au format du cadre** (decision concepteur) : Dadant, Langstroth, Warre sont des formats de cadre, la ruchette un corps plus etroit. Cadres et partitions `ruchette` ranges en `dadant` (migration), calcul en service Dadant incluant les ruchettes ; corps, plancher, toit, nourrisseur gardent le format ruchette.
- **Infobulle `Ruches a l'atelier`**.
- **Tableau de bord : `Occupation cadres` en %** (cadres occupes / capacite du corps : 10 Dadant ou Langstroth, 8 Warre, 6 ruchette ; hors Atelier), champ `taux_occupation_cadres` ; `cadres_moyens_par_ruche` conserve dans l'API.
- **Liste des ruches qui se decale en cochant** (iOS sans ancrage du defilement) : la ligne cochee reste sous le doigt (Ruches et Atelier).
- **Retours traites classes** : colonnes `traite_le` et `note_traitement` ; `list_beta_feedback.sh` n'affiche que les non traites (`--tous` pour l'historique), `classer_beta_feedback.sh` les classe.
- Non reproduit : erreur a la connexion puis session ouverte apres rafraichissement (un seul `GET /auth/me 403` dans les logs) ; plus revu apres plusieurs connexions, abandonne par le concepteur le 2026-10-05.
- Valide sur iPhone par le concepteur : zoom, stock `-` / `+`, cochage rapide de plusieurs ruches (1.36.3).

### Journal technique (v1.36.3)

- Decision concepteur 2026-10-05 : `api_events` conserve **6 mois** (fourchette CNIL 6 mois a 1 an ; 108 Mo en 7 semaines, inclus dans chaque sauvegarde).
- `backup_daily.sh` purge chaque nuit les lignes de plus de 6 mois (`API_EVENTS_RETENTION_MONTHS`) avant le dump ; un echec de purge n'empeche pas la sauvegarde. Premieres suppressions en fevrier 2027.
- Index `idx_api_events_created_at` (migration `20261008`) ; politique de confidentialite mise a jour (« 6 mois, puis efface automatiquement »).
- **Liste des ruches qui se decale (complement 1.36.2)** : la vraie cause etait asynchrone. Apres le clic, les tags de la ruche arrivent du serveur, reconstruisent le tableau et agrandissent le bloc Tags au-dessus. Le tableau n'est plus reconstruit si les tags n'ont pas change, et la ligne cochee reste ancree 1,2 s (interrompu des que l'utilisateur touche ou fait defiler). Test e2e renforce (mesure apres chargement), echoue sans la correction.

### Deploiement en une commande

- `scripts/linux/deploy.sh [latest|<tag>] [all|dev|beta]` sur le VPS : app-dev (pull, migrations, release, gate), puis beta apres confirmation `beta` (pull, sauvegarde, migrations, release, health watch), verification de `/health`, journal dans `~/app/artifacts/deploy-logs/`. Script bash plutot qu'Ansible : rien a installer sur le VPS, reutilise les scripts existants.

### Validations

Derniere release (1.36.2) : `check_client_assets`, smoke strict, 79 tests
d'integration, 30 parcours navigateur (instables connus relances seuls, 3/3).
App-dev puis beta deployees par le concepteur (gate app-dev vert), `/health`
`1.36.2`. Migration `20261007` sur la beta : 3 groupes fusionnes, 5 doublons
supprimes, totaux conserves ; 8 retours classes, `3b5b1864` reste ouvert.

---

## 4. Ce qui est livre

- **Socle** : API FastAPI, PostgreSQL 16, migrations versionnees, Docker Compose local et cible, sauvegardes locales et hors site chiffrees, supervision Netdata, Uptime Kuma et alertes e-mail, deploiement versionne avec rollback.
- **Comptes** : inscription libre, connexion par cookie HttpOnly, revocation de session, mot de passe oublie, e-mails SPF/DKIM/DMARC.
- **Freemium** : Free limite a 2 ruchers ; Premium pour l'IA vocale, les modeles de ruche et l'import ; testeurs beta Premium (`BETA_NEW_USERS_PREMIUM=true`).
- **Metier** : ruchers, ruches (type, format, cadres), creation rapide et import, Atelier, transhumance, demontage, transvasement, reines, visites rucher et ruche, tags avec effets metier, ruches a surveiller, cadres et age de la cire, recoltes, materiel par type et format, statistiques et fiches.
- **Terrain** : file offline IndexedDB pour les visites (tags, transvasement et type compris), idempotence et conflits explicites.
- **Client web** : HTML/CSS/JavaScript sans framework en modules ES, servi sous `/app`, desktop et mobile ; page d'accueil statique.

---

## 5. Reste a faire

### Beta en cours
- [ ] Validation sur telephone reel en conditions terrain, file offline comprise (concepteur, en cours)
- [ ] Suivi hebdomadaire des retours testeurs (`list_beta_feedback.sh`, puis `classer_beta_feedback.sh` une fois livres) et corrections en petites versions
- [ ] Classer le retour `3b5b1864` sur la beta : `classer_beta_feedback.sh .env.target "non reproduit, abandonne" 3b5b1864`
- [ ] Verifier dans l'Atelier de la beta les quantites `en service` saisies a la main pour grilles et nourrisseurs (elles s'ajoutent au calcul automatique depuis 1.34)

### Apres les premiers retours
- [ ] Contrat d'ingestion capteurs
- [ ] V2 : plan de rucher sur quadrillage

### Stores (V2)
- [ ] Encapsulation Capacitor, tests internes Google Play et TestFlight
- [ ] Achats in-app, connexion Apple et Google, documents RGPD

### Paiement web
- [x] Architecture Stripe, PayPal, Apple Pay, Google Pay documentee
- [ ] Statut juridique, prix et conditions, comptes fournisseurs en mode test

### IA vocale
- [x] Acces Premium, extraction structuree, brouillons et revue
- [ ] Transcription reelle : Whisper `base` local dans l'application Capacitor, sans envoi d'audio au serveur
- [ ] Ecran de gestion du modele, mesures sur telephones, lexique apicole

---

## 6. Dette technique et points d'attention

| Sujet | Risque | Priorite |
|---|---|---|
| Simulation, etape S2 : `#btn-visit-transvasement` parfois invisible apres l'ajout de tags hors ligne (popup de visite pas encore rouverte) ; passe a la relance | test instable, possible course reelle cote client | P1 |
| Test `le formulaire de ruche s ouvre en edition` instable en suite complete | faux rouge | P2 |
| `~/app-dev` en retard sur la beta | validation de la prochaine release faussee | P1 |
| Fins de ligne CRLF | diffs bruyants | P2 |

---

## 7. Regles de livraison

- Aucun secret committe : mots de passe, cles, `.env*`, tokens, acces VPS.
- Un tag Git par deploiement, aligne sur le tag de l'image Docker.
- Backup de la base avant toute migration sur la beta.
- Le VPS ne recoit que du code venant de `main`.
- Gate complet avant chaque deploiement ; jamais de smoke sur la beta.
- Circuit : local, tour concepteur, `~/app-dev`, beta apres accord explicite. Les deploiements beta sont lances par le concepteur sur le VPS (l'agent prepare les commandes et verifie ensuite en lecture seule).
- Depot public : `export_public.sh` puis envoi force, uniquement apres feu vert.

---

## 8. Historique des versions

| Periode | Versions | Apports |
|---|---|---|
| 2026-08 | v1.1 a v1.23 | Premier candidat beta, onglets, Atelier, stock, visites, statistiques, recoltes (deployees sans tags Git, reconstituees depuis les images) |
| 2026-08 | v1.24 a v1.25 | Renommage Beevarium, mot de passe oublie, sauvegardes, environnement de test, e-mails conformes |
| 2026-08 | v1.26 a v1.31 | Corrections metier, selecteurs rucher/ruche, formats de materiel, tests navigateur, donnees realistes, tests de charge |
| 2026-08/09 | v1.32 | Canal de retours, kit beta, Premium automatique en beta, prise en main guidee |
| 2026-09 | v1.33.0 a v1.33.4 | Refonte visuelle (shell, navigation, tableau de bord, Ruchers, Visites, Atelier) |
| 2026-09 | v1.33.5 a v1.33.8 | UX, tags de ruche et regles avancees, durcissement auth et isolation |
| 2026-09 | v1.33.9 a v1.33.11 | Feedback, corrections Atelier et visites, durcissement securite |
| 2026-10 | v1.34.0 | Lots L1 a L8 ; depot public publie |
| 2026-10 | v1.34.1 | Retours du tour concepteur : rucher modifiable, tags multiples, visite pre-remplie, transhumance avant suppression, mouvements de cadres |
| 2026-10 | v1.35.0 | Pages legales, accueil `beevarium.fr`, alertes e-mail, modules ES |
| 2026-10 | v1.35.1 | Contact `contact@beevarium.fr` |
| 2026-10 | v1.35.2 a v1.35.4 | Inscription depuis l'ecran de connexion (sans code d'invitation), badge `Beta` |
| 2026-10 | v1.36.0 | Creation rapide, modeles et import de ruches, `Nouveau materiel`, oeil sur les mots de passe |
| 2026-10 | v1.36.1 | Type de ruche en creation rapide, modeles, import et visite |
| 2026-10 | v1.36.2 | Retours testeurs : stock sans doublon, cadres au format du cadre, occupation des cadres, zoom iOS, retours classes |
| 2026-10 | v1.36.3 | Purge du journal technique `api_events` a 6 mois ; liste des ruches stable apres chargement des tags |
