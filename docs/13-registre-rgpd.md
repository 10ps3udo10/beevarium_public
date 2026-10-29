# Registre des traitements (RGPD)

Registre tenu par l'editeur de Beevarium (article 30 du RGPD), aligne sur le
code au 2026-10-28. Version publique pour les utilisateurs :
`backend/app/static/app/privacy.html`. A mettre a jour avec toute nouvelle
table, tout nouveau sous-traitant ou toute nouvelle finalite.

## Responsable et sous-traitants

- Responsable : l'editeur de Beevarium, `contact@beevarium.fr`.
- Sous-traitant : OVH SAS (France) : VPS, envoi des e-mails, stockage hors site
  des sauvegardes chiffrees avant envoi. Aucun transfert hors de l'Union
  europeenne.
- Outils de developpement (GitHub, depot prive et CI) : code et donnees de test
  fictives uniquement, jamais de donnees d'utilisateurs.

## Traitements

| Traitement | Finalite | Base legale | Donnees (tables) | Conservation |
|---|---|---|---|---|
| Compte | Creer le compte, s'authentifier | Execution du service | `users` : e-mail, prenom, empreinte PBKDF2 du mot de passe, offre, tags favoris | Tant que le compte existe |
| Double authentification | Securite du compte (facultative, obligatoire pour l'administration) | Execution du service | `users` : secret TOTP (en clair, voir ADR), date d'activation, dernier pas utilise ; `mfa_recovery_codes` (empreintes SHA-256 des codes de secours) | Supprime avec le compte ou a la desactivation ; jamais exporte |
| Donnees apicoles | Gerer ruchers, ruches et visites | Execution du service | `ruchers` (dont GPS facultatif), `visites_rucher`, `ruches`, `ruche_tags`, `reines`, `visites_ruche`, `actions_visite`, `gestion_cadres`, `interventions_sanitaires`, `mouvements_hausses`, `recoltes`, `ruche_transvasements`, `ateliers`, `materiel_atelier`, `modeles_ruche`, `ref_*` personnelles | Tant que le compte existe |
| Retours beta | Ameliorer l'application | Interet legitime | `beta_feedback` | Tant que le compte existe |
| Reinitialisation du mot de passe | Securite du compte | Execution du service | `password_reset_tokens` (empreinte du jeton) | 30 minutes de validite, supprime avec le compte |
| Saisie hors ligne | Ne pas perdre ni dupliquer une visite | Execution du service | `idempotency_keys` ; file IndexedDB sur l'appareil, videe a la deconnexion | Supprime avec le compte |
| Journal technique | Securite, diagnostic | Interet legitime | `api_events` : date, methode, chemin, code, duree, compte | 6 mois (purge par `backup_daily.sh`) ; detache du compte a sa suppression |
| Sauvegardes | Continuite de service | Interet legitime | Copie complete de la base, chiffree hors site | 14 jours, puis effacement automatique |

Aucun cookie de mesure d'audience ni publicitaire : un seul cookie de session,
strictement necessaire.

## Droits des personnes

- Acces et portabilite : `GET /users/me/export` (Profil, Mes donnees,
  `Exporter mes donnees`) : fichier JSON de toutes les tables ci-dessus, sans
  l'empreinte du mot de passe, les jetons de reinitialisation, le secret TOTP,
  les codes de secours ni les cles d'idempotence. La liste des tables exportees est `_EXPORT_QUERIES` dans
  `backend/app/routers/users.py` : toute nouvelle table liee a un compte doit
  y etre ajoutee.
- Effacement : `DELETE /users/me` (Profil, Mes donnees, mot de passe exige,
  limite a 5 essais par 15 minutes). Suppression SQL du compte ; toutes les
  tables liees suivent par `ON DELETE CASCADE`, `api_events` passe en
  `SET NULL`. Les donnees restent dans les sauvegardes jusqu'a 14 jours, sans
  restauration selective.
- Rectification : depuis l'application (prenom, donnees apicoles).
- Autres demandes et opposition : `contact@beevarium.fr`, reponse sous un mois.
  Reclamation possible aupres de la CNIL.

## Securite

Mots de passe hashes (PBKDF2-SHA256, 600 000 iterations), JWT revocables par
`token_version`, cookie `HttpOnly` et `Secure` hors developpement, HTTPS par
Caddy, sauvegardes chiffrees avant envoi, acces au VPS par cle SSH sans root.
Details : `docs/06-exploitation.md`.
