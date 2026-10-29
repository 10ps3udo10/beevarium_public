# Backlog V1 Priorise

## Regles de priorisation
- P0: indispensable pour livrer V1 utilisable.
- P1: important, peut etre decale apres beta si besoin.
- P2: utile mais non bloquant.

## Epic A - Compte et abonnement
### P0
- Creation compte, connexion, deconnexion.
- Profil utilisateur avec prenom.
- Flag premium pour gerer les droits.

## Epic B - Ruchers
### P0
- Creer, renommer, archiver un rucher.
- Position GPS et type terrain.
- Statut activite (actif/inactif), peuplement (peuple/vide).
### P1
- Recherche/filtre des ruchers.

## Epic C - Ruches
### P0
- Creer et modifier une ruche avec identifiant libre.
- Affecter a un rucher ou atelier.
- Type ruche et statut ruche via dictionnaires extensibles.
- Deplacer une ou plusieurs ruches (transhumance).

## Epic D - Visites et suivi terrain
### P0
- Creation visite manuelle ruche.
- Critere: reine vue, ponte, couvain, reserves, agressivite, note.
- Actions multiples dans une visite.
- Intervention sanitaire depuis fiche visite.
- Edition a posteriori d une visite.
### P1
- Visite globale rucher (meteo, note globale, impression).

## Epic E - Cadres
### P0
- Declarer mouvements de cadres pendant visite.
- Stock theorique par annee de cire.
- Afficher indicateurs age des cadres par ruche.
### P1
- Alerte renouvellement cadres > 3 ans.

## Epic F - Recoltes et stats
### P0
- Saisie recolte liee a une ruche.
- Vue historique par ruche.
### P1
- Stats globales par rucher.

## Epic G - Dictionnaires extensibles
### P0
- CRUD pour: type ruche, statut ruche, actions visite, type intervention, actions cadres, type materiel.
- Ajout rapide d option depuis formulaire.

## Epic H - Materiel atelier
### P1
- Inventaire atelier (corps, hausses, planchers, etc.).
- Quantite atelier vs quantite en service.

## Epic I - IA vocale Premium
### P0
- Upload audio.
- Transcription.
- Extraction JSON structure.
- Enregistrement visite.
- Statut brouillon si ambigu/incomplet.
### P1
- Ecran de revue des brouillons IA.

## Epic J - Qualite et exploitation
### P0
- Journal d evenements et erreurs API.
- Healthcheck backend et DB.
- Validation des payloads et contraintes metier.
### P1
- Suite de tests API minimale (smoke + parcours critiques).

## Epic K - Test d'usage pilote
### P1
- Scenario exploratoire simule sur un jeu de donnees realiste avant beta externe.
- Parcours complets : ruchers, ruches, visites, recoltes, Atelier, stock,
	tableau de bord et statistiques.
- Journal des anomalies UX, metier et de performance ; correction des P0/P1
	avant invitation des testeurs.

## Epic L - Tags de ruche
### P1
- Tags multiples, visibles et assignables hors visite. **Socle manuel livre localement le 2026-09-05 ; favoris predefinis et premiers effets metier en cours**.
- Tags manuels et derives des observations de visite, avec regles explicites de
	creation, retrait, priorite et historique.
- Refonte UX des listes, tuiles et fiches afin de garder la lecture rapide.

## Epic M - Elevage, lignees et registres (V2/V2.1)
### V2
- Plan de rucher quadrille : positionner, deplacer et selectionner une ruche
	selon son emplacement physique.
- Exports CSV, XLSX et PDF de registres d'elevage et documents administratifs,
	apres cadrage des obligations ciblees.
### V2.1
- Calendrier d'elevage parametre par objectif et protocole : starter, finisseur,
	banque a males, nuclei, cellules royales et insemination si applicable.
- Jalons dates pour la preparation, le greffage, les transferts et les controles.
- Gestion des lignees : meres, filles, F0/F1/F2, croisements et evaluations.

## Epic N - Retours UX beta septembre 2026
### P0/P1 avant testeurs externes
- Corriger les actions Ruchers bloquees ou incoherentes : remplacer la reine,
	modification/creation en popup, selection videe au changement de rucher,
	deplacement de selection en popup.
- Corriger la recherche Visites : compteur coherent, filtre par rucher seul,
	distinction visites/recoltes et filtre par type.
- Finaliser Statistiques selon maquette : actualisation automatique, espacement,
	verification des mises a jour directes.
- Clarifier les indicateurs du tableau de bord : periode des visites, sens d'une
	ligne de stock, proximite labels/jauges.
- Reprendre l'Atelier : selection visible des ruches, modification en popup,
	bouton deplacement dans la bonne section, hierarchie typographique des tuiles.
