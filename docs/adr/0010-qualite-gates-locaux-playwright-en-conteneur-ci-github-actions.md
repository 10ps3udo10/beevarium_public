# ADR 0010 : Qualite : gates locaux, Playwright en conteneur, CI GitHub Actions

- Date : 2026-08-27
- Statut : Accepte

## Contexte

Une regression du client peut rendre l'application inutilisable alors que l'API reste verte (incident du 2026-08-27).

## Decision

Gate rapide pendant le developpement, gate complet avant livraison (`gate_fast.sh --full-integration` : assets, audit de securite pip-audit et Trivy, smoke, integration, Playwright). Playwright tourne dans un conteneur, sequentiellement. Jamais de smoke sur la beta. Depuis le 2026-10-28, la CI GitHub Actions rejoue le gate complet sur une stack jetable, avec gitleaks et Bandit ; Dependabot propose les mises a jour.

## Alternatives ecartees

Tests unitaires seuls (ne voient pas le navigateur) ; CI payante (plan gratuit suffisant).

## Consequences

Un test n'est jamais supprime ou affaibli pour obtenir une suite verte ; la simulation apiculteur reste hors gate (longue) : a relancer avant une release importante.

## Sources

Commits `e614a46` (2026-08-27), `bf72bf8` (2026-10-28) ; `docs/05-qualite-et-tests.md`.
