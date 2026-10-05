# Roadmap

Ce document remplace les anciens `09-phase10-roadmap-v1.1-v1.2.md` et
`12-beta-and-store-release-plan.md`.

---

## 1. Ou en est le produit

La beta web est **en ligne** sur https://beta.beevarium.fr depuis le 15 aout 2026,
en HTTPS, derriere Caddy, sur un VPS OVH Debian 12.

Version beta deployee : `v1.33.10-atelier-visite-fixes`.

Tranche concepteur locale du 2026-09-08 : corrections UI, partition, stocks,
hausses, favoris tags persistants, visites et recoltes en cours de validation.

Rattrapage tags/Atelier/statistiques local valide techniquement le 2026-09-08 :
popup tags de visite complete, catalogue categorise, favoris visibles pendant la
visite, saisie annee de cire et moyenne ponderee des cadres, Atelier en deux
colonnes. Validation concepteur encore requise avant diffusion.

### Perimetre couvert

- Comptes Free et Premium, avec limite de 2 ruchers en Free
- Ruchers, Atelier, ruches, deplacements simples et en masse
- Reines : historique, remplacement, age, rattachement automatique aux visites
- Visites rucher et ruche : saisie, edition, validation metier
- Recoltes : saisie, historique, suppression, statistiques
- Materiel d'atelier et suivi des cadres
- Statistiques et synthese de periode avec tendances
- Revue des brouillons IA Premium
- File locale IndexedDB des visites et synchronisation au retour du reseau
- Pages legales : mentions, confidentialite, conditions

### Perimetre volontairement exclu de la beta

- Synchronisation offline des ruchers, ruches, reines et de l'audio
- Ingestion de capteurs
- Alertes de supervision externe
- Publication native sur les stores

---

## 2. Ce qui bloque l'ouverture a des testeurs externes

La beta fonctionne, mais elle n'est pas encore prete pour des utilisateurs qui ne
sont pas le concepteur. Par ordre de priorite :

### P0 - Indispensable avant d'inviter qui que ce soit

- **Inscription autonome.** Couverte par smoke et E2E locaux ; a revalider sur
  `~/app-dev` avant toute invitation externe.
- **Mot de passe oublie.** Parcours autonome implemente localement et couvert par
  tests d'integration ; a valider sur `~/app-dev` avec SMTP avant beta externe.
- **Sauvegardes.** Sauvegardes quotidiennes locales et hors site chiffrees en
  place ; verifier une restauration recente avant ouverture externe.
- **Isolation des comptes.** Rattrapage largement couvert, renforce localement le
  2026-09-06 sur tags, reines et deplacements ; refaire le gate complet sur
  `~/app-dev` avant diffusion.
- **Menage des comptes de smoke.** La beta a ete purgee et les smokes doivent
  rester diriges vers l'environnement dedie `~/app-dev`, jamais vers la beta.

### P1 - Fortement souhaitable

- Page d'accueil sur `beevarium.fr`, aujourd'hui parquee chez OVH
- Message d'accueil et parcours de premiere prise en main
- Canal de retour utilisateur, meme minimal
- Validation sur telephone reel, en conditions terrain
- **Test d'usage simule avant les beta testeurs.** Parcourir l'application comme
  un apiculteur sur un jeu de donnees realiste : creer et modifier ruchers et
  ruches, saisir visites et recoltes, consulter Atelier, stock, statistiques et
  tableau de bord. Documenter les blocages, incoherences metier et frottements
  UX, puis corriger les P0/P1 avant toute invitation externe.
- **Tags cumulables de ruche.** Socle livre et tranche avancee implementee
  localement le 2026-09-06 ; a valider en test d'usage simule avant beta externe.

### P2 - Peut attendre les premiers retours

- Alertes de supervision externe
- Statistiques avancees supplementaires
- Contrat d'ingestion capteurs
- Architecture paiement et abonnement preparee ; implementation apres validation beta et decisions juridiques

---

## 3. Criteres pour ouvrir la beta

- Zero erreur bloquante sur inscription, connexion, saisie de visite et synthese
- Reinitialisation de mot de passe autonome
- Sauvegarde automatique verifiee par une restauration reelle
- File offline testee sur au moins un navigateur mobile reel
- Conflit offline explique et resolvable par l'utilisateur
- Gate complet vert sur le commit diffuse

---

## 4. Trajectoire stores

### Choix technique

Encapsuler le client web existant avec **Capacitor** une fois la beta stabilisee.
Le backend FastAPI reste heberge et commun au web et au mobile.

Ce choix evite une reimplementation React Native ou Flutter, reutilise le client
et IndexedDB deja en place, ouvre l'acces aux fonctions natives plus tard
(notifications, stockage, reseau) et permet de distribuer Android et iOS depuis la
meme base de code.

### Pre-requis

- URL d'API HTTPS stable sur un domaine de production
- Politique de confidentialite et conditions d'utilisation conformes RGPD
- Icone, ecran de lancement, identifiant d'application
- Gestion des erreurs reseau et conflits offline validee sur mobile reel
- Compte Apple Developer et Google Play Console
- Signature Android et certificats iOS geres hors Git
- Modele economique implemente : achats in-app pour le passage en Premium
- Prototype de transcription locale Whisper `base` telechargee a la demande,
  avec mesure de performance sur appareils reels

### Ordre recommande

1. Stabiliser la beta web et corriger les retours
2. Preparer Capacitor, un build Android interne et un prototype Whisper local
3. Test interne Google Play
4. TestFlight iOS
5. Soumission apres stabilisation

### Ce qui doit faire reporter les stores

- Perte de donnees ou conflits incompris en offline mobile reel
- URL d'API non stable
- Politique de confidentialite ou comptes stores non prets
- Absence de mecanisme de paiement pour le Premium

---

## 5. Principe de priorisation

- **P0** : ferme un risque d'usage terrain, ou rend utilisable un parcours deja
  supporte par l'API
- **P1** : augmente la valeur de suivi sans introduire d'infrastructure critique
- **P2** : depend d'une validation d'architecture, de volume ou de materiel, et ne
  bloque pas la prochaine livraison

---

## 6. V2 - Elevage, plan de rucher et registres

### Calendrier d'elevage - V2.1 ciblee

Outil de planification pour preparer une campagne d'elevage : colonie a
multiplier, nombre de reines ou cellules souhaitees, dates cibles et methode
(starter, finisseur, banque a males, nuclei, insemination si retenue). Il devra
produire un calendrier d'actions : mise en place des colonies et banques,
preparation du starter, greffage, transfert des cellules, constitution des
nuclei et controle de ponte.

Avant implementation : formaliser les protocoles pris en charge, leurs delais
et variantes regionales, les dependances de materiel et les cas d'echec. Le
calendrier ne doit jamais presenter une recommandation biologique comme une
certitude universelle.

### Lignees et evaluation - V2.1 ciblee

Suivre les souches et leurs descendances : meres, filles, generations F0/F1/F2,
croisements, origine et evaluations. Le modele devra permettre de comparer une
lignee sans confondre identite de colonie, reine historique et descendance.

### Plan physique de rucher - V2

Vue quadrillee ou les ruches sont placees et deplacees comme des pieces. Elle
sert a selectionner rapidement une ruche selon sa position reelle et doit rester
coherente avec les deplacements vers un autre rucher ou l'Atelier.

### Exports de registres - V2

Exporter en un clic les registres d'elevage et les documents utiles ou
obligatoires, avec choix du format CSV, XLSX ou PDF. Identifier auparavant les
registres cibles, leurs obligations selon le pays, les donnees minimales, les
periodes et les exigences de mise en page.
