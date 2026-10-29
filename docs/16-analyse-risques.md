# Analyse de risques et politique de securite (R5)

Analyse inspiree d'EBIOS Risk Manager, simplifiee a l'echelle de Beevarium
(un editeur, un VPS, une beta a donnees reelles). Etat au 2026-10-28.
A revoir a chaque changement d'architecture (ADR), apres tout incident G1 ou G2
(`docs/15-incidents.md`) et au moins une fois par an.

## 1. Valeurs metier et besoins de securite (DICT)

Echelle : 1 faible, 2 moyen, 3 fort, 4 critique.

| Valeur metier | D | I | C | T | Justification |
|---|---|---|---|---|---|
| Historique apicole (visites, recoltes, reines, stock) | 2 | 4 | 2 | 2 | Base des decisions de l'apiculteur ; une donnee fausse ou perdue est pire qu'une indisponibilite de quelques heures |
| Emplacement des ruchers (coordonnees GPS) | 1 | 2 | 4 | 2 | Le vol de ruches est un risque reel : la position d'un rucher ne doit fuir vers personne |
| Comptes (e-mail, empreinte du mot de passe) | 2 | 3 | 3 | 3 | Donnees personnelles (RGPD) ; reutilisation d'identifiants |
| Saisie au rucher (hors ligne) | 3 | 4 | 2 | 2 | Saisie faite une seule fois sur le terrain : elle ne doit ni se perdre ni se dupliquer |
| Service en ligne (beta) | 2 | 2 | 1 | 2 | Beta gratuite sans engagement de service ; une coupure de quelques heures est tolerable |

Objectifs de reprise (a mesurer par l'exercice R1) : perte de donnees maximale
24 h (sauvegarde quotidienne) ; remise en service : cible proposee de 4 h sur un nouveau VPS, a valider par le concepteur.

## 2. Biens supports

| Bien support | Contenu | Reference |
|---|---|---|
| VPS OVH Debian 12 | API, PostgreSQL, Caddy, beta et app-dev | ADR 0004 |
| Base PostgreSQL de la beta | Toutes les valeurs metier | ADR 0002 |
| Sauvegardes locales et hors site | Copie complete chiffree hors site | ADR 0007 |
| Telephone ou navigateur de l'apiculteur | Session (cookie), file hors ligne IndexedDB | ADR 0005, 0006 |
| Poste du concepteur | Cle SSH, depot prive, `.env.target`, cle de chiffrement des sauvegardes | `CLAUDE.local.md` (non versionne) |
| Depots GitHub et CI | Code ; aucune donnee d'utilisateur | ADR 0010, 0013 |
| Messagerie OVH | Alertes, reinitialisation de mot de passe | ADR 0008 |
| Dependances (PyPI, images Docker) | Code tiers execute en production | `security_audit.sh` |

## 3. Sources de risque

| Source | Objectif | Pertinence |
|---|---|---|
| Robots et attaquants opportunistes | Prise de controle du serveur, rebond, rancon | Forte (exposition Internet permanente) |
| Voleur de ruches | Localiser des ruchers | Moyenne (cible precise, donnee tres utile pour lui) |
| Utilisateur malveillant de la beta | Lire ou modifier les donnees d'un autre compte | Moyenne (inscription libre) |
| Erreur d'exploitation (concepteur ou agent IA) | Involontaire : mauvaise cible, migration destructive | Forte (personne seule, deux stacks sur le meme VPS) |
| Defaillance du fournisseur | Panne, incendie de centre de donnees | Faible a moyenne |
| Chaine d'approvisionnement logicielle | Code malveillant ou vulnerable dans une dependance | Moyenne |

## 4. Scenarios de risque

Gravite G et vraisemblance V de 1 a 4 ; risque = G x V avant et apres mesures.

| # | Scenario | G | V | Mesures en place | Residuel | Actions |
|---|---|---|---|---|---|---|
| R1 | Prise de controle du VPS par forcage SSH | 4 | 2 | Cle SSH, pas de compte root utilise, pare-feu 22/80/443, OpenSSH a jour | 4x2 = 8 | **SSH sans mot de passe** (audit A1), Lynis (A4), configuration versionnee (R14) |
| R2 | Acces aux donnees d'un autre compte (IDOR) | 3 | 2 | Controle d'appartenance sur chaque route, reponse 404, tests d'ownership, scan ZAP actif | 3x1 = 3 | Garder un test d'ownership pour chaque nouvelle route |
| R3 | Fuite des positions de ruchers | 4 | 1 | Coordonnees facultatives, appartenance, HTTPS, aucune donnee en CI, export public sans donnees | 4x1 = 4 | Ne jamais exposer de coordonnees dans un partage ou une statistique publique |
| R4 | Vol de comptes par forcage ou fuite d'identifiants | 3 | 2 | PBKDF2 600 000, limitation de debit (IP corrigee, audit S1), revocation par `token_version`, cookie `HttpOnly` | 3x1 = 3 | MFA (R9) |
| R5 | Perte de donnees (panne, erreur, rancongiciel) | 4 | 2 | Sauvegarde quotidienne verifiee, copie chiffree hors site, restauration hebdomadaire, sauvegarde avant migration | 4x1 = 4 | Exercice de reprise chronometre (R1) ; copie hors ligne ou chez un second fournisseur (ADR 0007) |
| R6 | Donnees corrompues par une release (doublons, regles fausses) | 3 | 3 | Gate complet, CI, tests de non-regression, app-dev avant beta, migrations revues | 3x2 = 6 | Simulation apiculteur avant chaque release importante (ADR 0010) |
| R7 | Erreur d'exploitation sur la beta (mauvaise stack, commande destructive) | 4 | 2 | `deploy.sh` avec confirmation `beta`, ports distincts, regles agents (`CLAUDE.md`), pas de smoke sur la beta, classifieur de commandes | 4x1 = 4 | Configuration du VPS en code (R14) |
| R8 | Saisie terrain perdue ou dupliquee | 3 | 2 | File IndexedDB, idempotence, conflits explicites, correctif 1.36.5 | 3x1 = 3 | Tests de conflit a etendre avec toute evolution hors ligne |
| R9 | Dependance vulnerable exploitee | 3 | 2 | pip-audit et Trivy dans le gate et la CI, Dependabot hebdomadaire | 3x1 = 3 | Traiter les PR Dependabot chaque semaine |
| R10 | Indisponibilite prolongee du fournisseur | 2 | 1 | Sauvegardes hors site, stack reproductible par Docker Compose | 2x1 = 2 | R1 mesure le temps de reprise reel |
| R11 | Fuite de secrets (depot, journal, export public) | 4 | 2 | `.env*` ignores, gitleaks sur l'historique en CI, export public filtre et relu, liens de reinitialisation jamais journalises hors developpement | 4x1 = 4 | Relire chaque export public avant envoi |

Risques prioritaires : R1 (seul risque residuel a 8) puis R6. Les autres sont
a 4 ou moins apres mesures.

## 5. Politique de securite

1. **Acces** : VPS par cle SSH uniquement, jamais en root ; un seul
   administrateur ; secrets uniquement dans `.env.target` sur le VPS et
   `CLAUDE.local.md` sur le poste, jamais dans Git ni dans un journal.
2. **Donnees** : hebergees en France (OVH) ; minimisation (GPS facultatif) ;
   export et suppression du compte en libre-service ; journal technique 6 mois
   (`docs/13-registre-rgpd.md`).
3. **Developpement** : chaque route verifie l'appartenance ; chaque bug corrige
   recoit un test de non-regression ; aucun test supprime pour obtenir une
   suite verte ; decision technique structurante consignee en ADR.
4. **Livraison** : gate complet et CI verts ; app-dev avant la beta ;
   sauvegarde avant toute migration beta ; deploiement beta lance par le
   concepteur ; jamais de smoke ni de scan actif sur la beta.
5. **Dependances** : audit automatique a chaque gate ; faille HIGH ou CRITICAL
   corrigeable bloquante ; exception motivee dans `security-ignore.txt`.
6. **Sauvegardes** : quotidiennes, chiffrees hors site, restauration de
   controle hebdomadaire.
7. **Incidents** : processus et comptes rendus dans `docs/15-incidents.md` ;
   fuite de donnees personnelles notifiee a la CNIL sous 72 heures.
8. **Revue** : cette analyse et l'audit (`docs/14-audit-securite.md`) sont
   revus au moins une fois par an et apres tout incident G1 ou G2.
