# Suivi de projet Beevarium

Document de pilotage : ou en est le projet, ce qui est en cours, ce qui reste.
Les journaux de session detailles sont dans l'historique Git du depot prive.

**Derniere mise a jour : 2026-10-29**

---

## 1. Etat en une minute

| | |
|---|---|
| Beta | `v1.37.0-rgpd-securite` sur https://beta.beevarium.fr (2026-10-28, deployee par `deploy.sh`, saine, aucune migration, migrations jusqu'a `20261008`) |
| Environnement de test | `~/app-dev` sur le VPS, port interne 18001 : `v1.37.0`, gate vert le 2026-10-28 |
| Version locale | `1.38.0`, identique a la beta (deployee le 2026-10-29, confirmee par le concepteur) |
| Accueil | https://beevarium.fr et https://www.beevarium.fr (page statique `site/`, Caddy) |
| Depot public | `github.com/10ps3udo10/beevarium_public`, sans licence, un commit, a jour en `1.36.5` avec la CI visible (jobs sautes) le 2026-10-28 |
| Hebergement | VPS Debian 12, Caddy + Docker Compose ; acces dans `CLAUDE.local.md` (non versionne) |
| Sauvegardes | locales 03h15 UTC (14 jours), hors site chiffrees 03h45 UTC, restaurations de controle le dimanche |
| Supervision | alertes e-mail toutes les 5 minutes vers `contact@beevarium.fr` (testees de bout en bout le 2026-10-04) |
| Testeurs | beta ouverte : inscription libre depuis l'ecran de connexion, comptes Premium pendant la beta ; premier testeur invite le 2026-10-04 |

**Prochaine etape** : accompagner les premiers testeurs (retours hebdomadaires
via `list_beta_feedback.sh`), puis
feuille de route R1 a R14 (section 5).

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
| A7 | 2026-10-28 | Industrialisation | Etapes R1 a R14 ajoutees a `docs/07-roadmap.md` section 7 (PRA, CI, DevSecOps, audit, risques, ADR, SLA, incidents, MFA, RGPD, budget, logs, accessibilite, VPS en code). |
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

### Securite : audit des vulnerabilites (2026-10-21)

- CVE-2026-109618 / 109619 (PHP2Shell, RCE PHP) : **non concerne**. Aucun PHP dans le depot ni sur le VPS (`dpkg`, binaires et images Docker verifies le 2026-10-21).
- Nouveau `scripts/linux/security_audit.sh`, etape 2/6 de `gate_fast.sh` (`--skip-security` pour le diagnostic hors ligne) : `pip-audit` 2.9.0 sur `backend/requirements*.txt`, Trivy 0.61.0 sur l'image API en service (paquets Debian et Python). Echec sur une faille HIGH/CRITICAL corrigeable ; exceptions motivees dans `security-ignore.txt`.
- Premier passage : PyJWT 2.14.0 vulnerable (PYSEC-2026-4141, RecursionError sur payload imbrique ; PYSEC-2026-4183, import JWK OKP). Exposition faible (signature HS256 verifiee, pas de JWK) ; passe en **2.15.0**. Image API locale : 0 faille HIGH/CRITICAL corrigeable.

### Documentation alignee sur le code (2026-10-28)

- PBKDF2 a 600 000 iterations (et non 100 000) dans `CLAUDE.md`, `docs/03`, `docs/06` (y compris la reinitialisation manuelle).
- `docs/06` : la limite « copie hors site a mettre en place » remplacee par l'etat reel (copie chiffree depuis le 2026-08-27, miroir de 14 jours chez le meme fournisseur).
- `docs/07` : date de mise en ligne de la beta corrigee (aout 2026, date exacte inconnue ; testeurs depuis le 2026-10-04), version renvoyee vers ce suivi.
- `docs/03` : validation offline sur telephone reel marquee faite (2026-10-16).
- Politique de confidentialite : les tags favoris sont stockes avec le compte, pas sur l'appareil.
- `models.py` : contrainte `poids_miel_kg` copiee par erreur sur `ApiEvent` retiree (sans effet sur la base, le schema vient des fichiers SQL).
- Politique de confidentialite deployee avec la 1.36.5 (2026-10-28).

### Visite : coupure reseau apres l'enregistrement (v1.36.5, deployee le 2026-10-28)

- Cause de l'instabilite S2 de la simulation : dans `saveVisite` (`js/visites.js`), les rafraichissements qui suivent un POST reussi etaient dans le meme `try` que le POST. Si le reseau tombait pendant ces rafraichissements, la visite deja creee etait remise en file hors ligne (doublon a la synchronisation, nouvelle cle d'idempotence), et la saisie suivante deja commencee etait videe, son popup ferme.
- Correctif : les rafraichissements ont leur propre `try` ; un echec affiche `Visite enregistree. Actualisation impossible: ...` sans remise en file.
- Non-regression : `une coupure reseau apres l enregistrement ne duplique pas la visite` (`parcours.spec.js`, mobile), rouge avant le correctif, vert apres.
- Simulation : l'attente S1 sur les cadres Dadant datait d'avant 1.36.2 (cadres ruchette ranges en Dadant) et echouait a chaque passage ; corrigee (32).
- Validations : `check_client_assets.sh` OK, `parcours.spec.js` 31/31, simulation 8/8 (2 echecs sur 7 avant) ; gate complet vert en 1.36.5 (audit securite, smoke, 79 tests d'integration, 31 parcours).
- Doublons deja crees sur la beta : aucun (verifie le 2026-10-28 en lecture seule, meme ruche et meme `date_visite`).
- Part aussi avec cette version : la politique de confidentialite corrigee (tags favoris).

### MFA plus claire, administration en popup, Atelier sans lignes a 0 (v1.38.1)

- Double authentification : etapes numerotees, champ « Mot de passe de votre compte Beevarium », e-mail du compte affiche, QR code genere dans le navigateur (`qrcode-generator` 2.0.4, MIT, copie dans `js/vendor/`, integrite npm verifiee), aide « Changer de telephone ou telephone perdu ».
- `scripts/linux/reset_mfa.sh <email>` : debloque un compte sans telephone ni code de secours (confirmation `oui`, une transaction).
- Administration : popup dedie ouvert depuis le menu Profil, bouton visible seulement pour un administrateur ; section retiree de « Mes informations ».
- Retour testeur 2026-10-28 : l'Atelier masque le materiel a 0 partout (en service, range, ruches atelier) ; l'ajout passe toujours par le formulaire et reutilise la ligne existante.
- Tests e2e : materiel a 0, popup d'administration (reponses `/admin` simulees), QR code et e-mail dans le parcours MFA.
- Corrige : la suppression de compte (`DELETE /users/me`) journalisait l'evenement API au nom du compte supprime (violation de cle etrangere sur `api_events`, traceback, reponse 204 inchangee) ; l'evenement est desormais anonyme.
- Regles agents (`CLAUDE.md`) : organisation agent principal et sous-agents, sur demande du concepteur.
- Validations : gate complet vert (securite OK, 89 integrations, 36 parcours).
- Dette : « le formulaire de ruche s ouvre en edition » instable (1 echec sur un gate, 5/5 seul) : le popup de ruche ne s'ouvre pas apres la selection du rucher ; piste : attendre la fin de `selectRucher` avant le clic.

### Chantiers paralleles R1, R7, R9, R11, R13, R14 (v1.38.0)

- Six agents en parallele (worktrees), relus et fusionnes par l'orchestrateur ; gate complet vert apres fusion (89 integrations, 34 parcours), simulation verte, Bandit 0.
- R9 : MFA TOTP en stdlib (anti-rejeu atomique, 8 codes de secours hashes, limiteur 5/15 min), connexion en deux etapes (`/auth/login/mfa`), role administrateur par `set_admin.sh`, section Administration (retours beta, statistiques) reservee a un admin avec MFA. Migration `20261029` idempotente. ADR 0018 propose : secret TOTP stocke en clair en base.
- R14 : `ansible/vps.yml` (base, SSH sans mot de passe, UFW, Docker, Caddy avec en-tetes, utilisateur et timers, Lynis) ; ecrase `/etc/caddy/Caddyfile` : comparer avant. Corrige au test : `/run/sshd`, fail2ban en `backend = systemd`.
- R1 : `pra_restore.sh` et repetition locale 56 s, comptages identiques ; corrige `deploy_apply_migrations.sh` (attente PostgreSQL sur volume vide, `mapfile`).
- R7 : engagement de service propose (99 %, maintenance dimanche 05-07 h), tableau mensuel ; scan quotidien des images (Trivy, alerte e-mail sans doublon) ; `alert_mail.py` extrait de `watchdog.py` a l'identique. Le scan local signale des failles dans `postgres:16-alpine`.
- R13 : accessibilite (contrastes de `.btn`, `--danger`, `--ok` legerement assombris, `aria-current`, libelles, cibles tactiles), test perenne ; inventaire des actifs.
- R11 : budget sans montant invente, postes OVH a relever.
- Incident sans effet : un agent a execute sur le poste un script prevu pour un conteneur (dossier temporaire partage) ; seul `/tmp/inv.ini` cree puis supprime. Regle : un dossier temporaire par agent.

### Incidents et risques (R8, R5, 2026-10-28)

- `docs/15-incidents.md` : gravite G1 a G4, processus (detecter, qualifier, contenir, corriger, communiquer, rediger), modele de compte rendu, registre de 14 incidents depuis le 2026-08-27, comptes rendus a posteriori de la panne du client (G1), des doublons de stock (G2) et du fichier personnel dans l'export public (quasi-incident).
- `docs/16-analyse-risques.md` : besoins DICT par valeur metier (positions des ruchers en confidentialite critique, vol de ruches), biens supports, sources de risque, 11 scenarios cotes avant et apres mesures, politique de securite en 8 regles. Risque residuel le plus haut : forcage SSH (8), a fermer par l'action A1.
- A valider par le concepteur : objectif de remise en service de 4 h (propose), revue annuelle.

### Audit de securite (R4, v1.37.0)

- ZAP 2.16.1 sur la stack locale : baseline 0 echec, scan actif de 86 routes 0 echec (113 regles), aucune erreur 500 ; beta et VPS en lecture publique (en-tetes, TLS, CORS, ports, SSH).
- Corriges : IP client = derniere valeur de `X-Forwarded-For` (la premiere, fournie par le client, permettait de contourner la limitation de debit par IP) ; `/docs`, `/redoc`, `/openapi.json` limites a `dev`, `test`, `local` ; `--no-server-header` ; `Cross-Origin-Opener-Policy` et `Cross-Origin-Resource-Policy`.
- A faire par le concepteur sur le VPS : **SSH accepte encore le mot de passe** (A1), en-tetes Caddy du site statique (A2), Lynis (A4). Polices hebergees (A3) : Kalam et Nunito Sans (SIL OFL, Fontsource 5.3.0) servies par l'application et le site, plus aucune requete vers Google ; CSP `font-src 'self'`.
- Site `beevarium.fr` republie le 2026-10-28 (polices hebergees).
- Validations : gate complet vert (81 integrations, 32 parcours), Bandit 0.

### Decisions d'architecture (R6, 2026-10-28)

- `docs/adr/` : 16 ADR (0001 a 0016), un fichier par decision, dates reprises de `git log` (premiere trace). 14 acceptes, 2 proposes (Capacitor et IA vocale locale, paiement).
- Ecarts notes dans les ADR : copie hors site chez le meme fournisseur et sans copie hors ligne (0007, pour R1) ; limiteur en memoire non partage (0011, pour R4) ; simulation apiculteur hors gate (0010).

### RGPD : export et suppression du compte (R10, v1.37.0)

- `GET /users/me/export` : JSON de toutes les donnees du compte, 23 sections (`_EXPORT_QUERIES` dans `routers/users.py`), sans empreinte de mot de passe, jetons ni cles d'idempotence.
- `DELETE /users/me` : mot de passe exige, 5 essais par 15 minutes ; suppression SQL, cascade PostgreSQL verifiee sur toutes les cles etrangeres (`api_events` en `SET NULL`) ; cookie efface, file hors ligne videe.
- Profil > Mes donnees : `Exporter mes donnees`, `Supprimer mon compte` (mot de passe et confirmation). `.btn-danger` n'avait aucun style : tous les boutons de suppression passent en `--danger`.
- Politique de confidentialite (28 octobre) et registre `docs/13-registre-rgpd.md`.
- Tests : 2 integrations (export limite au compte, suppression avec mot de passe et sans toucher aux autres comptes), 1 parcours Playwright.

### Integration continue et clone neuf (2026-10-28)

- CI GitHub Actions (R2, R3) : voir `docs/05-qualite-et-tests.md`. Premier run vert.
- Le montage de `demo-access.json` (ignore par Git) dans `docker-compose.yml` est retire : sur un clone neuf, Docker creait un repertoire a sa place et `check_client_assets` echouait. `bootstrap_demo_data.sh` copie deja le fichier dans le conteneur ; a relancer apres un rebuild de l'API. `backend/.dockerignore` l'exclut de toute image.
- Dette P2 soldee : `le formulaire de ruche s ouvre en edition` (instable note le 2026-10-04) ne se reproduit plus (113/113 le 2026-10-28, dont 3 suites completes) ; cause probable corrigee en 1.36.3 (tableau des ruches reconstruit apres chargement des tags). Test renforce : attente des listes rechargees avant les clics.
- `export_public.sh` n'exporte plus que les fichiers suivis (un document personnel non suivi avait failli partir), ni `dependabot.yml`.

### Deploiement en une commande

- `scripts/linux/deploy.sh [latest|<tag>] [all|dev|beta]` sur le VPS : app-dev (pull, migrations, release, gate), puis beta apres confirmation `beta` (pull, sauvegarde, migrations, release, health watch), verification de `/health`, journal dans `~/app/artifacts/deploy-logs/`. Script bash plutot qu'Ansible : rien a installer sur le VPS, reutilise les scripts existants.

### Validations

Derniere release (1.36.2) : `check_client_assets`, smoke strict, 79 tests
d'integration, 30 parcours navigateur (instables connus relances seuls, 3/3).
App-dev puis beta deployees par le concepteur (gate app-dev vert), `/health`
`1.36.2`. Migration `20261007` sur la beta : 3 groupes fusionnes, 5 doublons
supprimes, totaux conserves ; 8 retours classes, `3b5b1864` reste ouvert.

Patch PyJWT 2.15.0, tag `v1.36.4-pyjwt` (2026-10-21, revalide le 2026-10-27) : gate complet vert,
`check_client_assets`, audit securite (pip-audit et Trivy, 0 faille
corrigeable), smoke strict, 79 tests d'integration, 30 parcours navigateur.
Depot deplace hors d'iCloud vers `~/dev/beevarium/beevarium` (fichiers evinces
qui bloquaient Docker en EIO) ; `git fsck` propre, index reconstruit.

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
- [x] Validation sur telephone reel en conditions terrain, file offline comprise (concepteur, validee le 2026-10-16)
- [ ] Suivi hebdomadaire des retours testeurs (`list_beta_feedback.sh`, puis `classer_beta_feedback.sh` une fois livres) et corrections en petites versions
- [x] Classer le retour `3b5b1864` sur la beta (fait ; verifie le 2026-10-16 : aucun retour non traite, aucun nouveau depuis le 2026-10-05)
- [x] Deployer `v1.37.0-rgpd-securite` : app-dev puis beta le 2026-10-28 via `deploy.sh`, site republie par `deploy_site.sh` ; `/health` en `1.37.0`, image sur les deux stacks, `/docs` en 404, polices servies en `font/woff2` sans Google, aucun 500 ni traceback
- [x] Deployer `v1.36.5-visite-reseau` : app-dev puis beta le 2026-10-28 via `deploy.sh`, `/health` en `1.36.5`, image `beevarium-api:v1.36.5-visite-reseau` sur les deux stacks, aucun 500 ni traceback
- [x] Deployer `v1.36.4-pyjwt` (PyJWT 2.15.0) : app-dev puis beta le 2026-10-27 via `deploy.sh`, `/health` en `1.36.4`, aucun 500 ni traceback
- [ ] Option : scan quotidien des images sur le VPS avec alerte e-mail : `scan_images.sh` et timer prets (2026-10-28), a installer sur le VPS
- [x] Verifier dans l'Atelier de la beta les quantites `en service` saisies a la main pour grilles et nourrisseurs : aucune (0 ligne, verifie en lecture seule le 2026-10-28), rien a corriger

- [x] 1.38.1 : MFA plus claire (mot de passe du compte, etapes, e-mail du compte, QR code, changement de telephone, `reset_mfa.sh`) ; administration dans un popup dedie
- [x] Retour testeur 2026-10-28 (fait en 1.38.1) : Atelier, masquer les lignes de materiel a 0 (en service, range, total)

### Industrialisation, securite et continuite (`docs/07-roadmap.md` section 7)
- [ ] R1 Exercice de PRA chronometre sur VPS vierge, RTO/RPO, compte rendu (P1) : runbook `docs/17`, `pra_restore.sh`, repetition locale 56 s (2026-10-28) ; reste l'exercice sur VPS vierge (cout, decision concepteur)
- [x] R2 Integration continue GitHub Actions (P1) : `ci.yml` vert le 2026-10-28 (gate complet sur stack jetable, image construite a chaque run) ; jobs sautes sur le depot public, pas de run pour la documentation seule
- [x] R3 Securite dans le pipeline (P1) : vert le 2026-10-28 (pip-audit et Trivy via le gate, gitleaks sur l'historique avec 6 faux positifs ignores, Bandit `-ll`, Dependabot hebdomadaire)
- [ ] R4 Audit de securite et plan d'actions correctives (P1) : audit fait le 2026-10-28 (`docs/14-audit-securite.md`), S1 a S4 corriges ; reste A1 (SSH sans mot de passe, concepteur), A2 (en-tetes Caddy), A4 (Lynis), A5, A6
- [x] R5 Analyse de risques EBIOS RM simplifiee ou DICT, politique de securite (P1) : `docs/16-analyse-risques.md` (2026-10-28) ; risque prioritaire R1 (SSH par mot de passe)
- [x] R6 Journal des decisions d'architecture (ADR) (P1) : `docs/adr/`, 16 decisions reconstituees avec leur date Git le 2026-10-28, puis au fil de l'eau
- [x] R7 Engagement de service et tableau mensuel Uptime Kuma (P2) : `docs/18`, `scripts/uptime_report.py` (chiffres a valider)
- [x] R8 Modele de compte rendu post-incident (P2) : `docs/15-incidents.md` (2026-10-28), 14 incidents au registre, 3 comptes rendus a posteriori
- [x] R9 Role administrateur et MFA TOTP (P2) : migration `20261029`, ADR 0018, v1.38.0
- [x] R10 Registre RGPD, suppression et export du compte (P2) : fait le 2026-10-28 (`docs/13-registre-rgpd.md`, Profil > Mes donnees), non deploye
- [x] R11 Suivi budgetaire (P2) : `docs/19` (montants OVH a relever sur facture)
- [ ] R12 Centralisation des logs et alertes securite (P3)
- [x] R13 Inventaire des actifs et audit d'accessibilite (P3) : `docs/20`, `docs/21` (axe : 52 violations a 0 reelle)
- [ ] R14 Configuration du VPS en code avec Ansible (P2) : `ansible/vps.yml` pret et teste en conteneur (ADR 0017) ; reste l'application sur le VPS par le concepteur (A1, A2, A4)

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
| 2026-10 | v1.36.4 | PyJWT 2.15.0 ; audit de securite (pip-audit, Trivy) dans le gate |
| 2026-10 | v1.36.5 | Visite : une coupure reseau apres l'enregistrement ne duplique plus la visite ni ne vide la saisie suivante ; simulation a jour |
| 2026-10 | v1.37.0 | RGPD : export et suppression du compte ; audit de securite (IP client, documentation API masquee, en-tetes) ; polices hebergees ; boutons de suppression ; CI, ADR, incidents, risques |
| 2026-10 | v1.38.0 | Role administrateur et double authentification TOTP ; accessibilite (contrastes, libelles, cibles) ; scan quotidien des images ; Ansible, plan de reprise, engagement de service, budget, inventaire |
