# Suivi budgetaire (R11)

Etat au 2026-10-28. Document de suivi des couts de Beevarium (un editeur, un VPS,
une beta gratuite). Les propositions marquees **[A VALIDER]** attendent la decision
du concepteur.

## 1. Regle de releve des prix

Aucun montant n'est invente. Chaque ligne porte l'un des statuts suivants :

- **donnee fournie** : montant indique par le concepteur ou la roadmap, non reverifie ;
- **a confirmer sur facture** : montant inconnu du depot, a relever sur la facture ou la page de tarifs ;
- **gratuit (plan)** : offre sans frais, a reverifier si le plan change.

Ce document a ete redige sans acces aux pages publiques de tarifs : aucun prix public n'a ete
« releve le AAAA-MM-JJ ». Le premier releve (facture ou page tarifaire, avec date) remplace les
mentions « a confirmer ».

## 2. Postes de cout

HT/TTC : TVA francaise a 20 % pour les services OVH facturables en France. Pour un service
etranger (Apple, Google, Stripe), la TVA depend du statut du titulaire : **a confirmer**.

### 2.1 Recurrents (en service)

| # | Poste | Fournisseur / offre | Mensuel HT | Annuel HT | TTC | Source | Statut |
|---|---|---|---|---|---|---|---|
| C1 | VPS (API, PostgreSQL, Caddy, beta + app-dev) | OVH, VPS Debian 12 (gamme et taille non documentees dans le depot ; ADR 0004) | a confirmer | a confirmer | a confirmer | Facture OVH | a confirmer sur facture |
| C2 | Stockage objet hors site (sauvegardes chiffrees, 14 jours, S3 OVH via rclone ; ADR 0007) | OVH Object Storage (endpoint `s3.<region>.io.cloud.ovh.net`, `configure_offsite.sh`) | a confirmer | a confirmer | a confirmer | Facture OVH (volume stocke et trafic sortant) | a confirmer sur facture |
| C3 | Nom de domaine `beevarium.fr` (+ `beta.`, `www.`) | Registrar a identifier (OVH probable, non documente) | sans objet | a confirmer | a confirmer | Facture du registrar | a confirmer sur facture |
| C4 | Messagerie : `contact@beevarium.fr`, envoi SMTP des alertes et reinitialisations (`configure_smtp.sh`) | OVH (offre e-mail ou MX Plan, a identifier) | a confirmer | a confirmer | a confirmer | Facture OVH ; parfois inclus avec le domaine ou le VPS | a confirmer sur facture |
| C5 | GitHub : depot prive, CI, depot public | GitHub Free | 0 | 0 | 0 | Plan gratuit, 2000 min/mois de CI sur depot prive (`docs/05`) | gratuit (plan) |
| C6 | Certificats TLS | Let's Encrypt via Caddy | 0 | 0 | 0 | Service gratuit | gratuit (plan) |
| C7 | Supervision (alertes e-mail `watchdog.py`, Netdata et Uptime Kuma non exposes) | Logiciels libres auto-heberges, sur le VPS (C1) | 0 | 0 | 0 | ADR 0008 | gratuit (plan) |
| C8 | Outils d'assistance IA au developpement | Abonnement(s) du concepteur, hors depot | a confirmer | a confirmer | a confirmer | Facture du concepteur | a confirmer sur facture **[A VALIDER : a inclure ou non au budget du produit]** |

### 2.2 Futurs ou eventuels

| # | Poste | Fournisseur / offre | Montant | Source | Statut |
|---|---|---|---|---|---|
| F1 | Compte developpeur Apple (distribution iOS, ADR 0014) | Apple Developer Program | 99 USD/an | donnee du concepteur | donnee fournie, a confirmer (page Apple, TVA, conversion EUR) |
| F2 | Compte developpeur Google Play (Android) | Google Play Console | 25 USD, une fois | donnee du concepteur | donnee fournie, a confirmer |
| F3 | Paiement Premium web (ADR 0015, `docs/11`) | Stripe Billing + Checkout | pas d'abonnement ; commission par transaction (pourcentage + montant fixe) | page tarifs Stripe | a confirmer (taux selon la carte ; Billing peut ajouter un pourcentage) |
| F4 | Commission des achats integres Apple et Google | Stores | pourcentage du prix, selon programme (petit editeur ou standard) | conditions des stores | a confirmer |
| F5 | Second fournisseur de sauvegarde (copie hors ligne ou autre fournisseur, risque R5 de `docs/16`, ADR 0007) | A choisir | a confirmer | devis | a confirmer **[A VALIDER : besoin et fournisseur]** |
| F6 | Statut juridique, comptabilite, assurance | A definir (`docs/11`) | a confirmer | devis | a confirmer |
| F7 | Montee en gamme du VPS si la charge l'exige | OVH | a confirmer | grille OVH | a declencher par les seuils du §4 |

## 3. Tableau de synthese

| Rubrique | Mensuel HT | Annuel HT | Part a confirmer |
|---|---|---|---|
| Recurrents connus (C5, C6, C7) | 0 EUR | 0 EUR | 0 % (gratuits) |
| Recurrents a confirmer (C1, C2, C3, C4, C8) | a confirmer | a confirmer | 100 % |
| Futurs fournis (F1 + F2, 1re annee) | sans objet | 99 + 25 = 124 USD | montant fourni ; conversion et TVA a confirmer |
| Futurs a confirmer (F3 a F7) | variable ou a confirmer | variable ou a confirmer | 100 % |
| **Total en service aujourd'hui** | **a relever : C1 + C2 + C4 (+ C8)** | **12 x mensuel + C3** | **quasi totalite** |

Formule a appliquer des que les factures sont relevees :
`total annuel HT = 12 x (C1 + C2 + C4 [+ C8]) + C3 annuel`.
Le seul montant certain aujourd'hui est **0 EUR** (postes gratuits) ; le cout reel est
entierement dans C1 a C4, a renseigner au premier releve (§5).

### Consommation de la CI GitHub (estimation, C5)

Base : 93 commits depuis le 2026-09-01 (environ 8 semaines), dont une partie en documentation
seule (CI sautee). Hypotheses a verifier dans *Settings > Billing > Usage* :

| Element | Hypothese |
|---|---|
| Job « Gate complet » (`gate_fast.sh --full-integration`) | 5 a 8 min (`docs/05`) |
| Jobs gitleaks et Bandit | 1 a 2 min chacun |
| Run complet | environ 8 a 12 min |
| Runs par mois | environ 50 (35 pushes touchant le code + 15 PR Dependabot) |
| **Total estime** | **environ 400 a 600 min/mois, soit 20 a 30 % de 2000 min** |

Marge confortable. Les runs annules par un push suivant (`cancel-in-progress`) et les changements
de documentation (`paths-ignore`) reduisent encore la consommation. Le depot public n'execute pas les jobs.

## 4. Seuils d'alerte **[A VALIDER]**

| Seuil | Action |
|---|---|
| CI superieure a 1500 min/mois (75 %) | Regrouper les pushes, limiter les PR Dependabot, ou plan payant |
| Cout mensuel reel de C1 + C2 + C4 depassant 125 % du dernier releve | Chercher la cause (volume de sauvegardes, trafic sortant, option activee) |
| Stockage hors site depassant 2 fois (taille d'un dump x 14) | Verifier la purge a 14 jours (`backup_offsite.sh`) |
| Disque ou memoire du VPS au-dela de 80 % (Netdata) | Etudier F7 avant la saturation |
| Cout infrastructure par utilisateur actif superieur a 20 % du prix Premium mensuel TTC | Revoir le prix ou l'offre (§6) |
| Echeance du domaine a moins de 60 jours | Verifier le renouvellement automatique et le moyen de paiement |
| Echeance du compte developpeur Apple a moins de 60 jours (apres ouverture) | Renouveler |

Les pourcentages sont des propositions de depart, sans analyse chiffree : a ajuster apres
trois mois de releves.

## 5. Procedure de suivi **[A VALIDER]**

1. **Chaque mois** (premiere semaine, 15 min), le concepteur releve les factures OVH (VPS,
   stockage objet, domaine, messagerie), l'usage CI GitHub et, une fois actifs, Stripe et les stores.
2. Il ajoute une ligne au fichier de suivi (modele ci-dessous), tenu **hors du depot public**
   (donnees financieres) : un tableur, ou `artifacts/budget/releves.md` (ignore par Git).
3. Il compare aux seuils du §4 et note toute derive.
4. Les montants releves remplacent les « a confirmer » du §2 (montant et date du releve ; numero de
   facture dans le fichier de suivi, jamais dans le depot).
5. Chaque trimestre : relire ce document, recalculer le cout par utilisateur actif (§6), mettre
   a jour `suivi-projet.md`.
6. Chaque nouveau service payant : ajouter une ligne en §2 et a `docs/20-inventaire-actifs.md`.

### Modele de fichier de suivi

```markdown
| Mois | VPS C1 | Stockage hors site C2 | Domaine C3 | Messagerie C4 | CI GitHub (min) | Autres | Total HT | Total TTC | Utilisateurs actifs | Cout HT / utilisateur actif | Remarques |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AAAA-MM | | | | | | | | | | | |
```

Utilisateur actif : compte ayant au moins une connexion ou une visite dans le mois
(definition proposee **[A VALIDER]**, calculable depuis `api_events`, sans nouvelle collecte).

## 6. Lien avec le prix Premium (`docs/11`)

Le prix Premium n'est pas fixe (`docs/11`, etape « Fixer l'offre »). Le budget donne le plancher :

```
cout infrastructure par utilisateur actif = (C1 + C2 + C3/12 + C4) / utilisateurs actifs

prix plancher TTC d'un abonnement = cout par utilisateur actif
    + commission de paiement (F3 ou F4)
    + part des couts fixes futurs (F1, F2, F5, F6) / nombre d'abonnes
    puis marge de securite et TVA
```

- Les couts d'infrastructure sont quasi fixes (un VPS) : le cout par utilisateur baisse avec le
  nombre d'utilisateurs, jusqu'au seuil de montee en gamme (F7).
- Les achats integres retiennent une commission plus lourde que Stripe : le prix net par abonne
  differe selon le canal (ADR 0015). Le prix affiche doit couvrir le canal le plus cher **[A VALIDER]**.
- Pendant la beta, tous les comptes sont Premium offerts : le cout par utilisateur actif est un
  cout net sans recette.
- Le calcul devient possible apres les trois premiers releves mensuels.

## 7. Points a verifier par le concepteur

1. Offre exacte du VPS OVH, prix HT, periodicite, date de renouvellement (C1).
2. Volume et prix du stockage objet hors site (C2), trafic sortant des verifications hebdomadaires.
3. Registrar du domaine, prix annuel, renouvellement automatique (C3).
4. Offre de messagerie OVH utilisee pour `contact@` et le SMTP, et si elle est incluse dans une autre offre (C4).
5. Inclure ou non l'abonnement IA du concepteur dans le budget produit (C8).
6. Statut juridique et regime de TVA (HT/TTC, TVA sur Apple, Google, Stripe ; F1 a F4, F6).
7. Valider les seuils (§4), la definition d'utilisateur actif et l'emplacement du fichier de suivi (§5).
8. Decider de l'opportunite d'un second fournisseur de sauvegarde (F5).
