# Ouverture beta testeurs

## But et cadre

La beta est une phase d'apprentissage avec un petit groupe d'apiculteurs. Elle
sert a valider les parcours terrain et a prioriser la suite du produit, pas a
remplacer le suivi habituel d'un rucher.

Commencer avec 3 a 5 testeurs, pour une periode de deux semaines. Augmenter le
groupe seulement si les criteres d'acceptation restent verts.

Pendant la beta privee, les nouveaux comptes recoivent Premium automatiquement.
Ce reglage est limite a l'environnement beta et ne permet pas a un navigateur
de choisir son propre plan. Il est active par `BETA_NEW_USERS_PREMIUM=true`
dans `.env.target` sur le VPS. Le remettre a `false` avant une ouverture
publique ou l'introduction d'un abonnement payant.

Apres leur premiere connexion, les comptes sans visite voient un guide leger
sur le tableau de bord. Son action unique conduit successivement vers le
premier rucher, la premiere ruche puis la premiere visite. Le guide disparait
automatiquement apres cette visite.

## Message d'invitation

> Beevarium est une beta privee pour suivre un rucher depuis un navigateur.
> Creez votre compte avec le lien « Creer un compte » de l'ecran de connexion,
> ajoutez un rucher et une ruche, puis
> enregistrez une visite. Vos retours nous aideront a prioriser les ameliorations. Ne saisissez
> ni mot de passe ni information sensible dans un retour.

Lien a communiquer : `https://beta.beevarium.fr/app/`. L'inscription est
libre : toute personne qui a le lien peut creer un compte (Premium pendant la
beta).

## Consignes courtes pour le testeur

1. Creer un compte et conserver son mot de passe ; le lien « Mot de passe
   oublie » permet de le reinitialiser.
2. Ajouter un rucher, puis une ruche avec son identifiant habituel.
3. Enregistrer une visite complete pour une ruche.
4. Consulter le tableau de bord et les statistiques.
5. Depuis le pied de page, utiliser « Envoyer un retour » apres connexion pour
   signaler un probleme, poser une question ou proposer une idee.
6. Sur telephone, essayer une visite sans reseau puis revenir en ligne et
   verifier que la synchronisation est terminee.

Le protocole detaille et les contraintes observees sur mobile sont dans
`docs/10-audit-mobile-et-test-terrain.md`.

## Canal de retours

Le formulaire `https://beta.beevarium.fr/app/feedback.html` est accessible
depuis le pied de page pour un utilisateur connecte. Il demande uniquement :

- le type de retour : probleme, idee, question ou autre ;
- un message d'au moins 10 caracteres ;
- un contexte facultatif.

Les retours sont rattaches au compte connecte et ne sont visibles que par leur
auteur dans l'API. Ils sont supprimes si le compte est supprime. Ne pas demander
de captures d'ecran contenant des donnees personnelles ; demander une
description reproductible a la place.

## Procedure de support

### Triage quotidien

Depuis le VPS, consulter les nouveaux retours :

```bash
cd ~/app
bash scripts/linux/list_beta_feedback.sh .env.target          # non traites
bash scripts/linux/list_beta_feedback.sh .env.target --tous   # avec l'historique
bash scripts/linux/classer_beta_feedback.sh .env.target "v1.36.2" <id8> [<id8> ...]
```

Un retour traite est classe (`traite_le`, `note_traitement`), jamais supprime :
il sort de la liste par defaut et n'est plus reinvestigue.

Classer chaque retour dans le backlog avec : date, parcours concerne,
reproductibilite, impact et priorite.

### Priorites

| Niveau | Definition | Delai cible |
|---|---|---|
| P0 | Impossible de s'inscrire, se connecter, enregistrer une visite ou risque de perte/fuite de donnees | Suspendre les invitations et corriger avant reprise |
| P1 | Fonction majeure difficile a utiliser sans contournement simple | Prise en compte dans le prochain cycle |
| P2 | Confort, idee ou cosmetique | Regrouper apres les retours du groupe |

Pour un P0, relever l'heure, le compte concerne, le parcours et le navigateur,
puis verifier `https://beta.beevarium.fr/health` et Uptime Kuma. Ne jamais
demander de mot de passe, de jeton ou d'export de donnees privees.

### Reponse au testeur

Accuser reception sous deux jours ouvrables. Indiquer soit qu'un correctif est
prevu, soit le contournement, soit que la demande est placee au backlog. Ne pas
promettre de date avant que le correctif soit planifie et valide.

## Criteres d'acceptation de l'ouverture

Le groupe initial peut etre invite quand tous les points sont vrais :

- le gate release candidate est vert sur le commit diffuse ;
- l'endpoint public `/health` repond avec la version attendue et une base
  connectee ;
- sauvegarde locale, copie hors site et restauration de controle sont vertes ;
- Uptime Kuma surveille l'API avec des reponses `200` ;
- inscription et reinitialisation de mot de passe ont ete verifiees sur une
  vraie boite e-mail ;
- le formulaire de retours est accessible, stocke un retour authentifie et
  refuse une requete anonyme ;
- au moins un test terrain sur telephone couvre la saisie et le retour reseau.

Ne pas ouvrir plus largement tant que le dernier point, offline mobile reel,
n'est pas valide.