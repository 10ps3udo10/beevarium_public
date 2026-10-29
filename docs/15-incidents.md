# Gestion des incidents (R8)

Processus, modele de compte rendu et registre des incidents de Beevarium.
Un incident est tout evenement qui degrade le service, met en jeu des donnees
ou aurait pu le faire (quasi-incident). Les comptes rendus sont sans recherche
de coupable : on cherche la cause racine et la defense qui a manque.

## Processus

1. **Detecter** : alerte e-mail du watchdog (`contact@beevarium.fr`), retour
   testeur (`list_beta_feedback.sh`), CI rouge, constat en developpement.
2. **Qualifier** la gravite :

   | Niveau | Definition | Delai de prise en charge |
   |---|---|---|
   | G1 critique | Beta indisponible, perte ou fuite de donnees | Immediat |
   | G2 majeur | Fonction principale cassee (connexion, visite, synchronisation), donnees incorrectes | Dans la journee |
   | G3 mineur | Gene sans perte de donnees, contournement possible | Prochaine release |
   | G4 quasi-incident | Defaut detecte avant tout effet sur les utilisateurs | Prochaine release |

3. **Contenir** : retour arriere (`deploy_rollback.sh` vers l'image
   precedente) si une release est en cause ; sauvegarde
   (`deploy_backup_db.sh`) avant toute action sur les donnees ; aucune
   correction manuelle en base sans accord du concepteur.
4. **Corriger** la cause racine, avec un test de non-regression qui echoue
   sans la correction ; livraison par le circuit normal (gate, app-dev, beta).
5. **Communiquer** aux testeurs concernes si des donnees ou l'usage ont ete
   touches (e-mail depuis `contact@beevarium.fr`). Fuite de donnees
   personnelles : notification a la CNIL sous 72 heures (RGPD, article 33).
6. **Rediger** le compte rendu (G1 et G2 obligatoirement, G3 et G4 dans le
   registre) au plus tard une semaine apres, et suivre ses actions jusqu'a
   cloture.

## Modele de compte rendu

```markdown
### INC-AAAA-MM-JJ-n : titre court

- Gravite : G1 | G2 | G3 | G4
- Detection : date heure, par qui ou quoi
- Resolution : date heure ; duree d'impact
- Versions : version en cause, version corrigee

**Impact** : utilisateurs, fonctions, donnees touches (chiffres).

**Chronologie** : faits horodates, de l'introduction du defaut a la cloture.

**Cause racine** : le mecanisme technique, puis pourquoi les defenses
existantes (tests, gate, revue) ne l'ont pas arrete.

**Correction** : ce qui a ete change (commits), test de non-regression.

**Actions** : | Action | Responsable | Echeance | Statut |

**Lecons** : ce qui a bien marche, ce qu'on garde.
```

## Registre

| Id | Date | Gravite | Incident | Cause racine | Correction | Source |
|---|---|---|---|---|---|---|
| INC-2026-08-27-1 | 2026-08-27 | G1 | Client web inutilisable, API verte (depuis la 1.23) | Bloc duplique et parenthese orpheline dans `app.js` | Syntaxe, controle des assets dans le gate, cache `no-cache` | Compte rendu ci-dessous |
| INC-2026-08-27-2 | 2026-08-27 | G4 | Script de deploiement termine sans message | `STACK_NAME` absent | Valeur par defaut | `718e2fd` |
| INC-2026-08-27-3 | 2026-08-27 | G2 | Sauvegardes non restaurables sous un autre role PostgreSQL | Dump avec proprietaires et ACL | `pg_dump --no-owner --no-acl`, restauration de controle hebdomadaire | `d3901b2` |
| INC-2026-08-27-4 | 2026-08-27 | G3 | Mot de passe SMTP corrompu au chargement | Caracteres speciaux non proteges dans le fichier d'environnement | Valeur entre guillemets | `95afc0d` |
| INC-2026-08-27-5 | 2026-08-27 | G3 | E-mails classes en indesirables | En-tetes RFC 5322 manquants, DKIM inactif | En-tetes, partie HTML, SPF, DKIM, DMARC | `abf0b7c`, `6ec6ff0` |
| INC-2026-08-27-6 | 2026-08-27 | G4 | Une base neuve differait d'une base migree | `001_schema.sql` en retard sur les migrations | Schema initial aligne | `b8e0f6c` |
| INC-2026-08-27-7 | 2026-08-27 | G4 | Erreurs a 60 utilisateurs simultanes (test de charge) | Pool SQLAlchemy par defaut | Pool dimensionne (ADR 0002) | `e14bcf4` |
| INC-2026-10-05-1 | 2026-10-05 | G2 | Stock : retirer creait une ligne en double (3 sur la beta) | L'API ne renvoyait pas `format_materiel` | Format renvoye, index unique, migration de fusion | Compte rendu ci-dessous |
| INC-2026-10-05-2 | 2026-10-05 | G3 | Liste des ruches qui se decale sur iPhone | Reconstruction asynchrone du tableau apres chargement des tags | Tableau stable, test e2e | `dc46e54` |
| INC-2026-10-21-1 | 2026-10-21 | G3 | Dependance vulnerable PyJWT 2.14.0 | PYSEC-2026-4141 et 4183 | PyJWT 2.15.0, audit automatique dans le gate | `2467d6a` |
| INC-2026-10-28-1 | 2026-10-28 | G4 | Une coupure reseau apres l'enregistrement d'une visite la remettait en file (doublon) et vidait la saisie suivante | Rafraichissements dans le meme `try` que le POST | `try` separe, test e2e ; aucun doublon trouve sur la beta | `fb67b61` (1.36.5) |
| INC-2026-10-28-2 | 2026-10-28 | G4 | Simulation apiculteur cassee depuis la 1.36.2 | Regle des cadres modifiee sans mettre a jour la simulation, hors gate | Attente corrigee ; CI ajoutee | `fb67b61`, `bf72bf8` |
| INC-2026-10-28-3 | 2026-10-28 | G4 | Document personnel inclus dans l'export du depot public | `export_public.sh` copiait les fichiers non suivis | Blocage avant envoi, export limite aux fichiers suivis | Compte rendu ci-dessous |
| INC-2026-10-28-4 | 2026-10-28 | G4 | Limitation de debit par IP contournable | Premiere valeur de `X-Forwarded-For` retenue | Derniere valeur (audit R4, S1) | `3cf6e73` |

## Comptes rendus

### INC-2026-08-27-1 : client web inutilisable, API verte

- Gravite : G1
- Detection : 2026-08-27, par le concepteur en ouvrant l'application
- Resolution : 2026-08-27 ; defaut present depuis la 1.23, beta sans testeurs externes a cette date
- Versions : 1.23 a 1.25.1 ; corrige en `v1.25.2-client-syntax`

**Impact** : plus aucun ecran utilisable (connexion comprise) ; aucune donnee
perdue, l'API et la base fonctionnaient.

**Chronologie** : un bloc duplique laisse une parenthese orpheline dans
`app.js` (1.23) ; le smoke API et les tests d'integration restent verts a
chaque livraison ; le 2026-08-27, l'ecran de connexion ne reagit plus ;
correction et durcissement le jour meme.

**Cause racine** : une erreur de syntaxe JavaScript arrete tout le module, donc
le demarrage du client. Les defenses ne testaient que l'API : aucun controle
de syntaxe du client, aucun parcours navigateur.

**Correction** : syntaxe reparee ; `check_client_assets.sh` (syntaxe de chaque
module, JSON) dans le gate ; evenements de connexion lies avant le reste du
demarrage ; `Cache-Control: no-cache` sur le client (`3f54bb4`, `82caa0b`,
`dc878b1`) ; parcours Playwright ajoutes au gate (`e614a46`).

**Actions** : toutes closes (controle des assets, parcours navigateur, CI depuis
le 2026-10-28).

**Lecons** : une API verte ne prouve pas que l'application marche ; tout
changement du client passe par `check_client_assets.sh` et Playwright.

### INC-2026-10-05-1 : doublons de lignes de stock

- Gravite : G2
- Detection : 2026-10-05, retour du premier testeur
- Resolution : 2026-10-05 (1.36.2)
- Versions : depuis l'ajout des formats de materiel ; corrige en 1.36.2

**Impact** : 3 groupes de lignes de stock en double sur la beta ; totaux
affiches faux pour le testeur concerne ; aucune perte.

**Chronologie** : l'Atelier affiche une ligne par type et format ; retirer du
materiel renvoyait une ligne sans `format_materiel`, que le client recreait ;
signale par le testeur ; correction, index unique et migration de fusion le
jour meme ; sauvegarde avant migration.

**Cause racine** : contrat API incomplet (champ absent de la reponse) et
absence de contrainte d'unicite en base ; les tests verifiaient la quantite,
pas le nombre de lignes.

**Correction** : format renvoye par l'API, index unique, migration
`20261007` qui fusionne les doublons en conservant les totaux, test
d'integration (`650c04c`).

**Actions** : toutes closes.

**Lecons** : une regle d'unicite metier doit aussi etre une contrainte en base ;
les migrations de donnees sur la beta passent par sauvegarde, fusion verifiee
et comptage avant/apres.

### INC-2026-10-28-3 : document personnel dans l'export public

- Gravite : G4 (quasi-incident, rien n'a ete publie)
- Detection : 2026-10-28, controle de l'export avant envoi
- Resolution : 2026-10-28

**Impact** : aucun ; le fichier a ete retire de l'export avant l'envoi force
vers le depot public.

**Chronologie** : un dossier personnel non suivi par Git est present dans le
depot de travail ; `export_public.sh` le copie avec les fichiers du depot ; la
relecture de l'export avant envoi le repere ; le fichier est retire, puis le
script corrige.

**Cause racine** : `git ls-files --others` copiait aussi les fichiers non
suivis ; le controle de motifs sensibles du script ne cherche que des secrets,
pas des documents personnels.

**Correction** : export limite aux fichiers suivis (`32717ac`).

**Actions** : relire la liste des fichiers de l'export avant chaque envoi
(continu).

**Lecons** : la relecture humaine avant une action publique et irreversible a
arrete le defaut ; elle reste obligatoire.
