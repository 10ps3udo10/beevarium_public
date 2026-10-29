# ADR 0007 : Sauvegardes locales et hors site chiffrees, restaurations de controle

- Date : 2026-08-27
- Statut : Accepte

## Contexte

La beta porte des donnees reelles de testeurs sur un seul VPS.

## Decision

Dump quotidien a 03h15 UTC, verifie (gzip, taille minimale), conserve 14 jours ; copie hors site chiffree AES-256 avant envoi (rclone, stockage objet, 14 jours) ; restauration reelle de controle chaque semaine ; sauvegarde avant toute migration beta. Planification par timers systemd utilisateur (sans root).

## Alternatives ecartees

cron (absent du VPS) ; copie hors site en clair (adresses e-mail et empreintes de mots de passe) ; sauvegarde sans restauration de controle.

## Consequences

La copie hors site est chez le meme fournisseur et il n'y a pas de copie hors ligne : risque residuel note pour l'exercice de reprise (R1).

## Sources

Commits `dcf9479`, `899cdd3`, `ce61558` ; `docs/06-exploitation.md`.
