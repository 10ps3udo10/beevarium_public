# ADR 0016 : Suppression de compte par cascade SQL, export par requetes explicites

- Date : 2026-10-28
- Statut : Accepte

## Contexte

Droits RGPD d'acces, de portabilite et d'effacement en libre-service (R10).

## Decision

`DELETE /users/me` (mot de passe exige) supprime la ligne `users` par une requete SQL directe : toutes les tables liees suivent par `ON DELETE CASCADE`, verifie sur chaque cle etrangere ; `api_events` passe en `SET NULL`. `GET /users/me/export` lit chaque table par une requete litterale listee dans `_EXPORT_QUERIES` (`routers/users.py`).

## Alternatives ecartees

Suppression par l'ORM (charge les relations et peut tenter de mettre leurs cles a NULL) ; suppression logique (donnees conservees, contraire a l'effacement) ; export generique par introspection du schema (risque d'exporter des secrets techniques).

## Consequences

Toute nouvelle table liee a un compte doit avoir sa cascade et son entree dans `_EXPORT_QUERIES` ; les donnees restent jusqu'a 14 jours dans les sauvegardes.

## Sources

Commit `d70dab3` ; `docs/13-registre-rgpd.md`.
