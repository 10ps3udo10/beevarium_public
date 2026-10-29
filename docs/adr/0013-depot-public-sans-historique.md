# ADR 0013 : Depot public sans historique

- Date : 2026-10-03
- Statut : Accepte

## Contexte

Montrer le projet publiquement sans exposer l'historique d'exploitation (acces, incidents, donnees de demonstration).

## Decision

Depot d'exploitation prive ; copie publique a un seul commit produite par `export_public.sh` (fichiers suivis uniquement, fichiers prives exclus, blocage sur motif sensible), envoyee en force apres feu vert. La CI y est visible mais ses jobs ne tournent pas ; Dependabot n'y est pas exporte.

## Alternatives ecartees

Publier l'historique (fuite possible d'anciennes informations) ; depot public seul.

## Consequences

Le depot public est ecrase a chaque export : pas de contribution externe pour l'instant ; pas de licence (decision D5).

## Sources

Decision D5 (`suivi-projet.md`) ; commits `32717ac`, `e7622c3`.
