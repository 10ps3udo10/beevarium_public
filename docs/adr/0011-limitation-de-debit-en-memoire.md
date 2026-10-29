# ADR 0011 : Limitation de debit en memoire

- Date : 2026-09-20
- Statut : Accepte

## Contexte

Proteger connexion, inscription, reinitialisation et suppression de compte contre le forcage, avec une seule instance de l'API.

## Decision

Limiteur a fenetre glissante en memoire du processus (`backend/app/rate_limit.py`), cle par IP (lue dans `X-Forwarded-For` derriere Caddy) et par compte.

## Alternatives ecartees

Redis (un service de plus pour une seule instance).

## Consequences

Compteurs remis a zero a chaque redemarrage et non partages entre instances : a revoir si l'API passe a plusieurs instances. L'IP retenue est la derniere valeur de `X-Forwarded-For`, ajoutee par Caddy (audit R4 du 2026-10-28, `docs/14-audit-securite.md`, S1).

## Sources

Commit `9d49c5f`.
