# ADR 0002 : API FastAPI, PostgreSQL 16 et migrations SQL versionnees

- Date : 2026-08-11
- Statut : Accepte

## Contexte

Application de gestion apicole avec des regles metier relationnelles (ruchers, ruches, visites, stock), developpee par une personne avec des agents IA.

## Decision

API Python FastAPI, SQLAlchemy 2 et Pydantic 2 ; PostgreSQL 16. Le schema vit en SQL : `db/init/001_schema.sql` pour une base neuve et `db/migrations/AAAAMMJJ_*.sql` appliquees par ordre alphabetique et tracees dans `schema_migrations` (`deploy_apply_migrations.sh`). Les contraintes et cascades sont dans la base, pas seulement dans l'ORM.

## Alternatives ecartees

Alembic (genere des migrations a relire, une couche de plus) ; base NoSQL (relations fortes, contraintes metier).

## Consequences

Typage et OpenAPI generes ; une migration ne doit jamais etre renommee une fois appliquee ; une nouvelle colonne demande la migration et la mise a jour de `001_schema.sql`.

## Sources

Commit `d0dc669` ; `docs/03-architecture.md` ; `docs/06-exploitation.md` (migrations).
