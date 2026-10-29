# ADR 0004 : Hebergement : VPS OVH Debian 12, Docker Compose et Caddy

- Date : 2026-08-27
- Statut : Accepte

## Contexte

Beta a cout faible, donnees hebergees en France, exploitation par une seule personne.

## Decision

Un VPS OVH Debian 12 ; la meme definition Docker Compose en local et sur le VPS ; Caddy seul composant expose (TLS Let's Encrypt), API et base liees a 127.0.0.1, pare-feu limite a SSH, 80 et 443. Beta (`~/app`, port 18000) et test (`~/app-dev`, port 18001) cohabitent dans des stacks separees (`STACK_NAME`, volumes et ports distincts). Acces SSH par cle, jamais root.

## Alternatives ecartees

PaaS (cout recurrent, donnees hors de France selon l'offre) ; Kubernetes (surdimensionne).

## Consequences

Point unique de defaillance assume pour la beta : couvert par les sauvegardes hors site (0007) et l'exercice de reprise prevu (R1).

## Sources

`docs/06-exploitation.md` ; `docs/07-roadmap.md`.
