# Engagement de service de la beta (R7)

> **Propositions a valider par le concepteur.** Aucun chiffre ci-dessous n'est
> encore un engagement : ce sont des objectifs realistes pour un editeur seul
> et une beta gratuite. Une fois valides, les publier aux testeurs (page
> d'accueil ou e-mail) en les presentant comme des objectifs, pas des garanties.

## 1. Disponibilite cible

**Objectif propose : 99 % par mois civil**, mesure par Uptime Kuma sur
`https://beta.beevarium.fr/health` (voir section 6).

| Calcul | Valeur |
|---|---|
| Mois moyen | 365,25 / 12 = 30,44 jours = 730,5 h |
| Indisponibilite toleree à 1 % | 730,5 h x 0,01 = 7,3 h, soit **environ 7 h 18 min par mois** |
| Mois de 30 jours (720 h) | 7 h 12 min |
| Mois de 31 jours (744 h) | 7 h 26 min |

Pour comparaison : 99,9 % ne laisserait que 44 min par mois, ce qu'un editeur
seul, sans astreinte de nuit, ne peut pas tenir. Un deploiement dure quelques
minutes (redemarrage du conteneur) et compte dans l'indisponibilite, sauf
maintenance annoncee.

Compte pour la disponibilite : toute periode ou `/health` ne repond pas
`status: ok` avec `database: connected`. Ne compte pas : maintenance annoncee
(section 2), causes exclues (section 6).

## 2. Maintenance annoncee

- Fenetre habituelle proposee : **dimanche entre 05:00 et 07:00 heure de
  Paris**, hors saison de forte activite terrain (matin en semaine).
- Annonce au moins 48 h avant (e-mail ou page d'accueil) pour toute coupure
  prevue de plus de 5 minutes (migration lourde, changement de VPS).
- Les deploiements courants (coupure de moins de 5 minutes) peuvent avoir lieu
  hors fenetre ; le mode hors ligne permet de continuer a saisir les visites.
- Une maintenance annoncee est declaree dans Uptime Kuma (maintenance) : elle
  est exclue du calcul mensuel.

## 3. Delais de prise en charge

Gravites de [docs/15-incidents.md](15-incidents.md). Un delai de prise en
charge est le delai avant que le concepteur commence a traiter, pas le delai
de resolution. Horaires : jours ouvres, pas d'astreinte de nuit ni de week-end
(propositions).

| Gravite | Definition | Prise en charge | Objectif de resolution (propose) |
|---|---|---|---|
| G1 critique | Beta indisponible, perte ou fuite de donnees | Immediate des reception de l'alerte, en journee ; au plus tard le lendemain matin si l'alerte survient la nuit ou le week-end | Contournement ou retour arriere sous 4 h de travail effectif |
| G2 majeur | Fonction principale cassee, donnees incorrectes | Dans la journee (jour ouvre) | Correctif sous 3 jours ouvres |
| G3 mineur | Gene sans perte de donnees, contournement possible | Prochaine release | Selon la prochaine release |
| G4 quasi-incident | Defaut detecte avant tout effet | Prochaine release | Selon la prochaine release |

Fuite de donnees personnelles : notification a la CNIL sous 72 h (RGPD,
article 33), quelle que soit la gravite du jour.

## 4. Objectifs de reprise

Reprise de [docs/16-analyse-risques.md](16-analyse-risques.md) :

- **Perte de donnees maximale : 24 h** (sauvegarde quotidienne a 03:15 UTC,
  copie chiffree hors site a 03:45 UTC). Une visite saisie hors ligne reste
  dans l'appareil jusqu'a sa synchronisation.
- **Remise en service : 4 h proposees** sur un nouveau VPS a partir de la
  sauvegarde hors site. Valeur a confirmer par l'exercice chronometre R1.

## 5. Contact

- Support et signalement : `contact@beevarium.fr`, et le formulaire de
  feedback de l'application (`feedback.html`).
- Etat du service : message sur la page d'accueil ou e-mail aux testeurs en
  cas d'incident G1 ou G2 qui les touche.
- Reponse a un message non urgent : sous 2 jours ouvres (proposition).

## 6. Exclusions

- **Phase beta** : service gratuit, fourni en l'etat, sans garantie ni
  compensation financiere ; fonctionnalites et donnees de test pouvant
  evoluer.
- **Force majeure** : catastrophe, panne electrique ou reseau generale, acte
  malveillant massif (deni de service distribue).
- **Fournisseurs** : panne du VPS OVH, du DNS, du fournisseur d'e-mail ou des
  services tiers (Stripe, stores d'applications). L'indisponibilite est
  tout de meme mesuree et consignee, mais exclue de l'objectif.
- **Cote utilisateur** : reseau mobile absent, navigateur ou appareil non
  pris en charge.
- Les delais de la section 3 sont des objectifs de bonne foi, pas des
  obligations contractuelles.

## 7. Mesure et suivi

- Sonde : moniteur Uptime Kuma sur `/health` (intervalle 60 s), complete par
  le watchdog (alertes e-mail).
- Tableau mensuel genere par `scripts/uptime_report.py` (procedure dans
  [docs/06-exploitation.md](06-exploitation.md), section 8) et archive dans
  `docs/exploitation/disponibilite-AAAA-MM.md`.
- Revue chaque debut de mois : objectif atteint ou non ; si non, incident ou
  entree au registre de [docs/15-incidents.md](15-incidents.md).
