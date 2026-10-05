# Refonte visuelle

> **Decision 2026-10-03** : les maquettes Excalidraw sont abandonnees. Les
> agents ne les lisent plus et ne s'en servent plus comme reference. Les
> intentions ci-dessous restent valables comme principes ; la reference visuelle
> est l'application actuelle, validee onglet par onglet par le concepteur.

## Intention

Transformer Beevarium en une application plus legere, tactile et chaleureuse,
proche d'un carnet de rucher moderne. La refonte doit garder la rigueur d'un
outil de suivi, mais remplacer l'empilement de cartes par des surfaces plus
respirantes, des lignes dessinees et une hierarchie plus nette.

Cette refonte est visuelle, mais pas seulement. L'objectif principal est de
rendre Beevarium plus utilisable et de mieux presenter les informations utiles
au but de l'application : aider l'apiculteur a comprendre son cheptel, decider
quoi faire et saisir ses observations rapidement sur le terrain.

Intentions retenues (issues des premiers jets, desormais abandonnes) :

- une navigation par onglets conservee ;
- sur desktop, cette navigation est a gauche ;
- sur mobile, elle doit devenir un panneau glissant depuis le bord gauche ;
- moins d'informations visibles en meme temps ;
- plus de popups pour les actions de creation et de modification ;
- des listes plus lisibles, proches de fiches ou lignes de carnet ;
- des boutons d'action dans la palette Beevarium.

## Direction graphique

Palette cible apres revue des maquettes :

| Role | Couleur proposee | Usage |
|---|---|---|
| Sauge principale | `#78917f` | navigation active, actions principales, jauges |
| Sauge sombre | `#425348` | accents forts, titres secondaires, pictogrammes |
| Sauge pale | `#dfe8dc` | fonds d'etats doux et aplats discrets |
| Papier casse | `#f8f5ed` | fond principal clair et doux |
| Encre graphite | `#2f302d` | textes, contours et lignes dessinees |
| Miel discret | `#d6a336` | micro-accent uniquement : pastilles, repere, detail |
| Alerte | `#b85b38` | erreurs et actions destructives, jamais pour les actions courantes |

Le jaune ne doit plus porter les actions principales ni le fond global. Il doit
rester en tres petites touches modernes, afin d'eviter un rendu trop date.

Style manuscrit : l'utiliser comme accent, pas pour tout le texte. Les donnees
metier doivent rester tres lisibles.

Proposition typographique :

- titres, petits labels et annotations : une police manuscrite lisible de type
  `Kalam`, `Patrick Hand` ou equivalente ;
- textes de formulaire, tableaux, chiffres et navigation : une sans-serif ronde
  et lisible de type `Nunito Sans`, `Atkinson Hyperlegible` ou equivalente ;
- les chiffres des indicateurs doivent rester tabulaires et stables.

Traitement des composants :

- bordures legerement irregulieres ou double-trait tres discret ;
- boutons avec fond sauge pour l'action principale et contour graphite pour les
  actions secondaires ;
- popups conservees avec arriere-plan floute, mais harmonisees avec les memes
  rayons, bordures et champs ;
- eviter le tout-carte : utiliser des bandes, listes et sections ouvertes.

## Organisation proposee par onglet

### Tableau de bord

Etat au 2026-09-02 : **valide localement par le concepteur**, avant gate complet
et deploiement. Les choix valides sont :

- titre unique `Tableau de bord`, sans bandeau de priorite invente ;
- aucun bouton `Nouvelle visite` dans cet onglet ;
- couvain affiche une seule fois ;
- jauge explicite `Ruches avec reine active`, exprimee en `reines/ruches` ;
- graphique `Visites par mois · annee en cours`, de janvier a decembre sur une
  seule ligne ; les mois sans visite n'affichent pas de zero ;
- contenu charge en environ 0,5 a 0,7 s sur le profil local de 190 ruches,
  contre environ 8,1 s avant optimisation.

L'optimisation retire le chargement de l'historique complet des visites du
rafraichissement du tableau de bord. Cet historique est charge a l'ouverture de
l'onglet Visites ; les ruches de tous les ruchers sont chargees en parallele.

Direction navigation desktop : les onglets vivent dans une zone invisible collee
au bord gauche de l'ecran. Elle est masquee au repos, apparait au survol du
bouton menu ou du panneau, et se replie automatiquement en quittant cette zone.
Le bouton menu est fixe a 16 px du bord gauche. Le contenu principal utilise une
gouttiere de 24 px sur les fenetres courantes, sans element rogne a droite.

Les maquettes indiquent des statistiques regroupees par familles et plusieurs
formats visuels. Proposition :

- conserver seulement une priorite claire et quelques indicateurs visuels ;
- limiter le texte d'explication : le tableau de bord doit se lire comme une
  page de carnet, pas comme une notice ;
- afficher les chiffres regroupes dans un ledger compact, sans multiplier les
  cartes ;
- choisir le format de chaque donnee selon son usage : nombre brut, pourcentage,
  jauge circulaire ou liste courte ;
- ajouter un graphique `visites par mois` pour la saison en cours ;
- repousser les details dans les onglets specialises ou les popups.

### Ruchers

Etat au 2026-09-02 : **valide localement par le concepteur**. Deux etats sont
implementes : tuiles seules, puis tuiles avec rucher selectionne.

- grille de tuiles de ruchers sur desktop, quatre par ligne, avec statut et
  type de terrain ;
- ruchers inactifs visuellement grises ;
- apres selection : tableau des ruches du rucher, actions de contexte visibles ;
- les actions de ruche sont au-dessus du tableau ; les details secondaires ne
  s'intercalent pas dans la liste ;
- lignes du tableau des ruches a 39 px, comme la maquette ;
- creation/modification en popup.

### Atelier

Etat au 2026-09-03 : inventaire aligne localement sur la maquette, en tuiles
compactes de quatre colonnes sur desktop.

- sections par type de materiel, puis format : `Corps · Dadant`, `Corps · Ruchette`, `Toit · Ruchette` ; le format n'est pas une categorie de materiel ;
- ne jamais afficher `Ruchette` comme categorie de stock autonome : une ruchette est un format de ruche ou de materiel, pas un type de materiel ;
- trois chiffres seulement par ligne : en service, a l'atelier, total ;
- bouton `Modifier` secondaire, non rouge ;
- ruches a l'atelier dans une liste separee, avec action de deplacement.
- l'utilisateur peut ajouter une ligne de materiel meme sans stock existant et
  creer directement une ruche a l'Atelier.

### Visites

Etat au 2026-09-03 : actions et filtres alignes localement sur la maquette.

- actions principales : nouvelle visite, nouvelle recolte, revue IA ;
- filtres rucher, ruche, statut, source et periode dans une zone compacte ;
- historique sous forme de liste/tableau leger ;
- formulaire de visite en popup pleine hauteur sur mobile ;
- toujours afficher le contexte choisi avant la saisie : rucher + ruche.
- l'historique affiche le rucher et la ruche, jamais la note ; il est pagine a
  100 lignes et filtre cote serveur pour rester rapide avec un gros cheptel.

### Statistiques

L'ecran statistique doit etre plus analytique que le tableau de bord.

- filtres en haut ;
- resultats sous forme de synthese + tableaux ;
- conserver les indicateurs existants mais les renommer et grouper ;
- eviter de repeter exactement les memes tuiles que le tableau de bord.

Etat au 2026-10-03 : Statistiques refondues par portee (vue globale, fiche
rucher, fiche ruche en lecture seule avec graphe cadres/couvain), rechargement
automatique au changement de rucher, ruche ou periode ; saison en cours par
defaut et saison derniere disponible.

## Regles responsive

- largeur cible mobile de reference : `375 px` ; aucun debordement horizontal ;
- zone tactile minimale : 44 px pour boutons, liens footer, onglets et lignes
  cliquables ;
- les tableaux deviennent des listes detaillees sur mobile ;
- la navigation par onglets reste scrollable horizontalement si necessaire ;
- un seul niveau d'action primaire par ecran ;
- le clavier mobile ne doit pas cacher le bouton de validation d'une popup.

## Plan de mise en oeuvre recommande

Regle de travail : decouper le travail selon le perimetre impacte, sans brider
la taille des taches. Ne pas lancer un gate complet ni un deploiement tant que le
rendu local desktop et mobile n'est pas visuellement valide par le concepteur.

1. Introduire les assets dans l'app : logo compact, mot-symbole, variables CSS,
   polices et composants communs.
2. Refaire le shell : fond papier, header, onglets, footer tactile, popups.
3. Reprendre les onglets dans cet ordre : Tableau de bord, Ruchers, Visites,
   Atelier, Statistiques. Tableau de bord et Ruchers sont valides ; prochaine
   tranche : Visites.
4. A chaque onglet : capture mobile et desktop, verification sans debordement,
   puis test E2E existant.
5. Rejouer un test terrain mobile reel apres la refonte complete.

## Points ouverts

- Reprendre Visites (affichage mobile a corriger, cf. `suivi-projet.md` B7), en gardant les actions en tete, les filtres
  compacts et l'historique leger.
- L'optimisation de l'historique global de Visites reste a envisager pour les
  gros cheptels : il fonctionne, mais affiche actuellement toutes les visites.
- Refaire un build Docker complet avant de deployer : le gate complet local est
  vert, mais un rebuild de fin de session a ete bloque une fois par une
  indisponibilite reseau de Docker Hub ; les derniers assets ont ete copies
  temporairement dans le conteneur local pour terminer la validation.
- Choisir definitivement les polices, en tenant compte du chargement offline.
- Decider si le logo complet apparait seulement a la connexion ou aussi dans
  l'app connectee.
- Definir les graphes du tableau de bord avec les donnees existantes, sans
  inventer d'indicateurs non calcules.
- Garder la variante `logo_sans_texte_versionIA.jpg` pour le module IA ou ne pas
  l'utiliser afin de limiter la dispersion visuelle.