# ADR 0003 : Client web vanilla en modules ES, sans build, servi par l'API

- Date : 2026-08-11
- Statut : Accepte

## Contexte

Le plan initial (Sprint 0) prevoyait Flutter. Le besoin prioritaire etait une beta web utilisable sur telephone, sans chaine de build a maintenir.

## Decision

Client HTML, CSS et JavaScript vanilla en modules ES natifs sous `backend/app/static/app/`, sans bundler ni framework, servi par le conteneur API sous `/app` : un seul artefact, aucun CORS. Une reevaluation (2026-10-04) a ecarte un portage Rust/WASM.

## Alternatives ecartees

Flutter et React Native (le web suffit pour la beta, Capacitor viendra ensuite, voir 0014) ; React ou Vue (build et dependances) ; Rust/WASM avec Leptos, Yew ou Dioxus (le client est limite par le reseau et la base, pas par le calcul : aucun gain perceptible, cout de build et risque de regression).

## Consequences

Une erreur de syntaxe dans un module bloque tout le client alors que l'API reste verte : `check_client_assets.sh` et les parcours Playwright sont obligatoires sur toute modification du client.

## Sources

Commits `d0dc669`, `1c532bd` ; `docs/03-architecture.md` (evaluation Rust).
