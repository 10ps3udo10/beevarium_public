# ADR 0012 : Journal technique conserve 6 mois

- Date : 2026-10-05
- Statut : Accepte

## Contexte

`api_events` atteignait 108 Mo en 7 semaines ; donnees personnelles (compte, chemins) soumises au RGPD.

## Decision

Purge des evenements de plus de 6 mois avant chaque sauvegarde (`API_EVENTS_RETENTION_MONTHS`), index sur `created_at`. A la suppression d'un compte, ses evenements sont detaches (`SET NULL`).

## Alternatives ecartees

Conservation plus longue (fourchette CNIL de 6 mois a 1 an, pas de besoin identifie).

## Consequences

La purge ne bloque pas la sauvegarde si elle echoue.

## Sources

Commit `dc46e54` ; `docs/13-registre-rgpd.md`.
