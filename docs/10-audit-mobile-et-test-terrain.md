# Audit mobile et test terrain

## Audit statique - 2026-08-31

Tests effectues sur la beta publique, sans session, aux formats `375 x 812` et
`390 x 844`.

| Surface | Resultat | Consequence pour les maquettes |
|---|---|---|
| Ecran de connexion | Pas de defilement horizontal ; champs et boutons principaux font 43 a 45 px de haut | Conserver des actions principales pleine largeur, avec une hauteur minimale de 44 px |
| Pied de page | Les liens mesurent environ 16 px de haut | Les liens legaux et le lien de retour doivent avoir une zone tactile d'au moins 44 px, sans necessairement agrandir le texte |
| Page de retours sans session | Pas de defilement horizontal ; le formulaire est masque et le message demande une connexion | Dans la refonte, garder un etat non connecte explicite avec une action visible vers la connexion |
| Hierarchie visuelle | Le formulaire de connexion tient dans le premier ecran, footer inclus apres un court defilement | Privilegier les informations essentielles avant tout contenu secondaire |

Cet audit ne remplace pas un essai connecte sur un telephone reel. Les
maquettes devront aussi prevoir le clavier logiciel, les selecteurs natifs et
les etats hors ligne. Retour terrain a integrer a la refonte : l'interface est
percue comme trop chargee, certains cadres et boutons debordent legerement,
et la densite doit etre revue avant une nouvelle validation sur mobile.

## Contraintes d ecran mobile

Ecrans prioritaires a verifier sur telephone : connexion, tableau de
bord, liste et detail d'un rucher, ajout de ruche, puis saisie de visite.

Contraintes a garder sur chaque ecran :

- une action principale evidente et des actions secondaires discretes ;
- aucun bouton ou cadre qui depasse sur `375 px` de large ;
- cibles tactiles d'au moins 44 px, y compris pour le pied de page ;
- moins de cartes et d'informations simultanees ;
- contexte rucher et ruche visible avant une saisie de visite ;
- guide de premiere prise en main court, sans ajouter une nouvelle navigation.

## Protocole terrain sur telephone

Faire ce test avec un compte beta Premium, sur Safari iPhone ou Chrome Android.
Prevoir 10 minutes, sans saisir de donnees sensibles.

### Avant de commencer

1. Ouvrir `https://beta.beevarium.fr/app/` et se connecter.
2. Creer un rucher et une ruche de test, ou choisir une ruche existante.
3. Ouvrir l'onglet **Visites** et selectionner la ruche.

### Saisie hors ligne

1. Couper les donnees mobiles et le Wi-Fi depuis les reglages du telephone.
2. Renseigner une visite : note, cadres totaux et cadres de couvain suffisent.
3. Enregistrer la visite.
4. Verifier le message indiquant que la visite est enregistree localement et
   que la synchronisation est en attente.
5. Fermer puis rouvrir l'onglet du navigateur. La visite ne doit pas disparaitre
   de la file locale.

### Retour reseau

1. Reactiver le reseau, puis revenir dans Beevarium.
2. Attendre le message de synchronisation terminee.
3. Actualiser la page une fois.
4. Verifier que la visite apparait dans l'historique de la bonne ruche, une seule
   fois, avec les valeurs saisies.

### A noter dans le formulaire de retour

Envoyer un retour depuis le lien **Envoyer un retour** avec :

- telephone et navigateur ;
- etape exacte ou le comportement a change ;
- message affiche par Beevarium ;
- resultat apres retour reseau : synchronise, en attente, conflit ou perdu.

## Critere de validation terrain

Le test est valide seulement si la visite reste presente apres fermeture de
l'onglet, se synchronise sans doublon au retour reseau et reste visible apres
rechargement. Un conflit doit etre explique par l'interface et laisser un choix
explicite de resolution.