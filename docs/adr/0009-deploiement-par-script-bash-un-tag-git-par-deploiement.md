# ADR 0009 : Deploiement par script bash, un tag Git par deploiement

- Date : 2026-10-05
- Statut : Accepte

## Contexte

Les deploiements enchainaient une dizaine de commandes manuelles sur deux environnements, avec risque d'oubli (sauvegarde, gate).

## Decision

`scripts/linux/deploy.sh` sur le VPS : app-dev (pull, migrations, release, gate) puis beta apres confirmation `beta` (sauvegarde, migrations, release, health watch), arret a la premiere erreur, refus d'un clone modifie. Un tag `vX.Y.Z-slug` par deploiement, aligne sur l'image Docker ; retour arriere par `deploy_rollback.sh` vers l'image precedente. Le deploiement beta est lance par le concepteur.

## Alternatives ecartees

Ansible pour le deploiement (a installer et maintenir ; reserve a la configuration du VPS, R14) ; deploiement automatique depuis la CI (beta a donnees reelles : decision humaine voulue).

## Consequences

Les evolutions sont groupees en une release par deploiement (preference du concepteur, 2026-10-28).

## Sources

Commit `c056113` ; `docs/06-exploitation.md`.
