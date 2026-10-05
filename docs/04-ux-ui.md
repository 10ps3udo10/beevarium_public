# Cahier des charges UX/UI beta Beevarium

## 1. Objectif

Transformer le client web actuel, encore proche d un prototype technique, en une beta utilisable sur desktop et mobile pour un apiculteur en situation terrain.

Priorites:

- rendre la connexion et le profil propres;
- donner une navigation stable et comprehensible;
- separer les espaces Ruchers, Atelier, Visites et Statistiques;
- reduire le nombre de controles visibles en permanence;
- privilegier les actions reversibles et les confirmations pour les actions sensibles;
- conserver les parcours backend deja valides.

La beta vise la fiabilite et la clarte. Les effets visuels, cartes geographiques avancees et fonctions IA complexes restent hors perimetre immediat.

## 2. Decision de navigation

### Navigation principale

Les onglets sont conserves sous forme de pastilles ou boutons segmentes, avec un seul onglet actif:

1. Tableau de bord
2. Ruchers
3. Atelier
4. Visites
5. Statistiques

`Statistiques` remplace `Synthese` et `Tendances` comme onglet principal unique. Il regroupe les indicateurs de synthese et les comparaisons de tendances. Cette decision evite deux ecrans proches et limite la navigation sur mobile.

La navigation doit etre:

- horizontale et scrollable sur mobile;
- visible en haut de l espace de travail;
- persistante pendant la session;
- compatible avec un lien profond ulterieur, par exemple `#ruchers` ou `/app/ruchers`;
- utilisable au clavier avec un vrai etat actif et `aria-selected`.

### Connexion et profil

La connexion devient une page dediee, sans navigation principale ni configuration technique visible.

- URL cible: `/app/login` ou vue initiale dediee equivalent.
- Apres connexion: redirection vers `/app/` et le Tableau de bord.
- Une pastille de profil apparait en haut a droite uniquement apres connexion.
- Cette pastille ouvre un menu avec: profil, statut Premium/Free, parametres, deconnexion.
- Le bloc `Acces API` est retire de l interface normale.
- La configuration API reste disponible dans un panneau de parametres reserve au diagnostic, non visible par defaut.
- La page de connexion ne contient aucun bouton demo dans la version testeur finale. Un mode demo explicite pourra exister en staging, mais ne doit pas dominer le parcours.

## 3. Structure de l espace de travail

Le titre global devient simplement:

> Espace de travail

Le sous-titre marketing ou technique est supprime.

Les boutons `Rafraichir`, `Charger synthese` et `Analyser tendances` ne sont plus presents dans tous les onglets.

Regle d affichage:

- Tableau de bord: chargement initial et bouton discret `Actualiser` si necessaire;
- Ruchers: actions propres aux ruchers et aux ruches;
- Atelier: actions propres a l atelier et aux stocks;
- Visites: recherche, filtres et saisie;
- Statistiques: filtres de periode et bouton ou actualisation automatique;
- les filtres de date et le contexte actif sont affiches uniquement dans Statistiques.

## 4. Onglet Tableau de bord

Le Tableau de bord est une vue de lecture rapide. Il ne doit pas devenir un formulaire geant.

### Categories proposees

#### Vue generale

- nombre de ruchers actifs;
- nombre total de ruches;
- nombre de ruches au rucher;
- nombre de ruches a l atelier;
- nombre de visites sur la periode recente;
- derniere synchronisation;
- etat reseau et nombre d operations offline en attente.

#### Vigilance terrain

- ruches sans visite recente;
- ruches avec reine non renseignee;
- reines depassant un age configurable;
- cadres anciens, par exemple plus de trois ans;
- ruches inactives ou sans statut exploitable;
- erreurs ou conflits de synchronisation a traiter.

#### Reines

- age moyen des reines;
- nombre de reines actives;
- reines a remplacer ou sans historique;
- repartition par race et provenance si les donnees sont suffisantes.

#### Cadres et production

- cadres moyens par ruche;
- cadres de couvain moyens;
- ruches a revisiter;
- recoltes recentes lorsque les donnees sont disponibles.

Chaque categorie est un groupe de cartes compactes. Les cartes servent a entrer dans Ruchers, Visites ou Statistiques; elles ne doivent pas ouvrir des formulaires lourds directement.

## 5. Onglet Ruchers

### Vue par defaut

- bouton `Ajouter un rucher` au-dessus de la grille;
- formulaire de creation masque par defaut;
- grille d icones ou cartes de ruchers;
- cinq cartes maximum par ligne sur grand ecran;
- deux ou trois colonnes sur tablette;
- une colonne ou une grille compacte sur mobile;
- chaque carte affiche au minimum nom, statut, nombre de ruches et indication de peuplement.

Le terme `icone` peut etre traduit par une carte visuelle simple: une icone de rucher, le nom et deux indicateurs. Il ne faut pas sacrifier la lisibilite a une illustration decorative.

### Selection d un rucher

Au clic sur une carte:

- la carte devient active;
- les informations du rucher s affichent sous la grille;
- la liste des ruches est affichee dessous;
- la selection est conservee lors d une action puis restauree au retour.

### Liste des ruches

Version beta:

- nom ou identifiant;
- statut actif/inactif;
- type de ruche;
- reine active en bref: presente, race, annee ou age;
- derniere visite;
- action principale.

La presentation peut commencer par des cartes denses sur mobile et un tableau sur desktop. Les colonnes seront configurables en V2.

### Actions d une ruche

Le clic sur une ruche ouvre une fiche ou un panneau d actions:

- voir details et statistiques;
- ajouter une visite;
- deplacer la ruche;
- remplacer la reine;
- modifier la ruche.

Regles de retour:

- apres ajout de visite: retour a la liste du rucher;
- apres deplacement: retour a la liste du rucher ou a l Atelier selon la destination;
- apres remplacement de reine: retour a la fiche du rucher avec confirmation;
- apres details et statistiques: ouverture de Statistiques avec la ruche deja selectionnee.

### Actions globales

La beta autorise uniquement:

- selection de plusieurs ruches;
- deplacement par lot;
- annulation explicite avant execution.

Les autres actions globales sont reportees car elles peuvent etre destructrices ou difficiles a annuler.

## 6. Onglet Atelier

L Atelier est un espace fonctionnel separe des ruchers.

### Ruches

- liste des ruches presentes a l atelier;
- statut affiche comme `Inactive` ou `A l atelier` selon le vocabulaire final retenu;
- deplacement individuel;
- selection multiple et deplacement par lot;
- creation d une nouvelle ruche;
- acces aux memes actions de details, visite et reine si elles sont pertinentes.

### Materiel

Bloc dedie aux stocks:

- hausses;
- planchers;
- corps;
- ruchettes;
- toits;
- nourrisseurs;
- autres types de materiel configurables.

Pour chaque ligne:

- quantite a l atelier;
- quantite en service;
- total theorique;
- bouton modifier;
- historique ou date de derniere modification si disponible.

Les modifications de stock doivent demander une valeur claire et afficher une confirmation de succes. Les quantites negatives sont interdites cote API et cote interface.

## 7. Onglet Visites

### Historique

La vue par defaut est l historique des visites avec:

- date;
- rucher;
- ruche;
- statut `Complete` ou `Brouillon`;
- source `Manuelle` ou `IA`;
- note ou resume court;
- filtre par statut;
- filtre par rucher et ruche;
- recherche;
- modification d une visite existante.

### Saisie manuelle

Un bouton `Saisie manuelle` ouvre une boite de dialogue ou une page courte. Le parcours est explicite:

1. selectionner le rucher;
2. selectionner la ruche;
3. renseigner les observations;
4. renseigner les actions et interventions;
5. enregistrer comme brouillon ou complete;
6. afficher une confirmation;
7. revenir a l historique filtre sur la visite creee.

Le formulaire doit etre decoupe en groupes: observation, couvain et reserves, reine, cadres, actions et commentaire. Les champs secondaires restent repliables.

### Saisie IA

Le bouton `Saisie IA` est visible mais marque `Bientot disponible` ou reserve aux comptes Premium tant que le parcours n est pas stabilise. Il ne doit pas perturber la saisie manuelle.

## 8. Onglet Statistiques

`Statistiques` regroupe l ancienne Synthese et les Tendances.

### Filtres

- periode predefinie: aujourd hui, 7 jours, 30 jours, 90 jours, saison, depuis la reine;
- date de debut et date de fin;
- tous les ruchers ou un rucher;
- toutes les ruches ou une ruche;
- rechargement automatique apres modification d un filtre;
- bouton `Reinitialiser`.

### Indicateurs

- ruches suivies;
- visites ruche et rucher;
- taux de reine vue;
- note moyenne;
- cadres totaux et cadres de couvain;
- evolution par rapport a la periode precedente;
- ruches sans visite recente;
- age et renouvellement des reines;
- age des cadres;
- recoltes lorsque disponibles.

La vue doit commencer par les indicateurs essentiels, puis afficher les details et alertes. Les tableaux et graphiques avances restent optionnels pour la V2.

## 9. Regle d unicite des ruches

### Regle metier

L identifiant de ruche est unique par utilisateur, independamment de sa localisation. Une ruche `A` ne peut donc pas exister simultanement dans un rucher et a l atelier.

### Implementation requise

- ajouter une contrainte ou un index unique sur `(user_id, identifiant_personnalise)`;
- definir la normalisation: trim obligatoire, comparaison insensible a la casse recommandee;
- refuser les doublons a la creation et a la modification;
- retourner une erreur metier lisible: `Cet identifiant de ruche est deja utilise.`;
- traiter les doublons existants avant la migration;
- ajouter des tests d integration pour creation, modification et deplacement;
- verifier que le deplacement ne genere pas de faux conflit puisque l identifiant reste sur la meme ligne.

La migration ne doit pas etre appliquee automatiquement tant qu un rapport des doublons existants n a pas ete produit et traite.

## 10. Plan d action priorise

### Lot 0 - Stabilisation et garde-fous

- figer le vocabulaire: `Statistiques`, `A l atelier`, `Complete`, `Brouillon`;
- documenter les routes et etats de navigation;
- ajouter la contrainte d unicite apres audit des donnees;
- conserver un backup avant migration;
- definir les erreurs et confirmations des actions sensibles.

### Lot 1 - Shell applicatif et connexion

- creer la page de connexion;
- cacher la configuration API dans Parametres > Diagnostic;
- ajouter la pastille profil et le menu utilisateur;
- transformer `/app/` en espace de travail post-connexion;
- ajouter les onglets et les liens profonds;
- tester mobile et desktop.

### Lot 2 - Tableau de bord

- remplacer le grand empilement par les categories de statistiques;
- ajouter les cartes d alertes et actions rapides;
- supprimer les boutons globaux inutiles;
- charger les donnees apres connexion;
- ajouter des etats vides, chargement et erreur.

### Lot 3 - Ruchers et ruches

- grille de cartes de ruchers;
- formulaire de creation masque;
- liste de ruches avec informations essentielles;
- fiche ruche et actions;
- retours coherents apres chaque action;
- deplacement individuel et par lot;
- ajout de ruche par dialogue.

### Lot 4 - Atelier et materiel

- liste des ruches a l atelier;
- deplacements individuels et par lot;
- creation de ruche;
- inventaire du materiel;
- modification des stocks avec garde-fous.

### Lot 5 - Visites

- historique filtrable;
- statut complete/brouillon;
- saisie manuelle en dialogue ou page dediee;
- modification et confirmation;
- retour automatique a l historique.

### Lot 6 - Statistiques

- regroupement synthese/tendances;
- filtres periode et scope;
- actualisation automatique;
- indicateurs prioritaires;
- acces depuis une ruche avec scope preselectionne.

### Lot 7 - Qualite beta

- tests integration des parcours critiques;
- test mobile reel;
- test offline et reprise reseau;
- smoke strict HTTPS;
- backup et rollback verifies;
- session pilote avec 3 a 5 testeurs.

## 11. Hors perimetre immediat

- saisie IA complete;
- personnalisation des colonnes;
- cartes geographiques avancees;
- graphiques complexes et exports;
- notifications externes;
- synchronisation offline des entites autres que les visites;
- publication native stores.

## 12. Criteres d acceptation beta UX

La beta UX est acceptable lorsque:

- un utilisateur non technique arrive sur une page de connexion claire;
- aucune URL API ni configuration Docker n apparait dans le parcours normal;
- apres connexion, il comprend les cinq onglets sans explication orale;
- il cree un rucher sans voir les champs avances avant de cliquer;
- il retrouve ses ruches en au plus deux actions;
- il ajoute une visite et revient a la liste attendue;
- il deplace une ruche individuellement ou par lot avec confirmation;
- il consulte une statistique pour un rucher ou une ruche sans recharger manuellement;
- il distingue clairement les visites completes et brouillons;
- l interface est utilisable sur mobile en portrait;
- un doublon d identifiant est bloque par l API avec un message comprehensible;
- les parcours critiques sont couverts par des tests et le smoke HTTPS reste vert.

## 13. Questions a trancher avant Lot 1

- retenir `Statistiques` plutot que deux onglets `Synthese` et `Tendances`;
- retenir `A l atelier` comme libelle utilisateur et conserver `Atelier` pour l onglet;
- choisir si le profil s ouvre par clic ou hover: clic recommande pour mobile;
- choisir si le dashboard affiche les alertes avant les indicateurs ou l inverse: indicateurs puis alertes recommande;
- definir les seuils de reine agee et cadre ancien;
- decider si une visite peut etre complete sans note globale;
- decider si les actions de deplacement par lot exigent une confirmation forte.
