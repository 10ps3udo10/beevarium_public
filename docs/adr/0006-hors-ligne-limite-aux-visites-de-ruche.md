# ADR 0006 : Hors ligne limite aux visites de ruche

- Date : 2026-08-13
- Statut : Accepte

## Contexte

Les ruchers sont souvent sans reseau. Une synchronisation generale cree des doublons et des ecrasements silencieux difficiles a corriger.

## Decision

Seules les visites manuelles de ruche se saisissent hors ligne. File IndexedDB sur l'appareil (videe a la deconnexion) ; envoi sequentiel dans l'ordre de saisie, reprise 1 s, 3 s, 10 s ; `Idempotency-Key` par operation, liee a l'utilisateur et serialisee par verrou PostgreSQL ; conflit explicite par version, jamais de fusion automatique. Tags, transvasement et changement de type voyagent dans le payload de la visite et s'appliquent dans la meme transaction (2026-10-04). Ruchers, ruches, reines et audio restent en ligne.

## Alternatives ecartees

Synchronisation de tout le modele (conflits non maitrises) ; `localStorage` (taille et objets structures) ; synchronisation parallele (ordre non garanti).

## Consequences

Toute extension du hors ligne doit conserver idempotence, ordre, absence d'ecrasement et tests de conflit. Un echec apres un enregistrement reussi ne doit jamais remettre la visite en file (correctif 1.36.5).

## Sources

Commits `27c0468` (2026-08-13), `1c532bd` ; `docs/03-architecture.md` ; validation terrain du 2026-10-16.
