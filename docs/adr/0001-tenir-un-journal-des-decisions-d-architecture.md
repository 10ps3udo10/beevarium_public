# ADR 0001 : Tenir un journal des decisions d'architecture

- Date : 2026-10-28
- Statut : Accepte

## Contexte

Les choix techniques etaient disperses entre `docs/03`, `docs/06`, le suivi et l'historique Git. Un nouvel intervenant (agent IA, jury, futur contributeur) ne pouvait pas retrouver pourquoi un choix avait ete fait.

## Decision

Un fichier court par decision dans `docs/adr/`, numerote, au format Contexte / Decision / Alternatives / Consequences / Sources. Les decisions passees sont reconstituees avec leur date d'origine (premiere trace Git) ; les suivantes sont ecrites au moment du choix. Une decision remplacee n'est pas effacee : son statut passe a `Remplace par NNNN`. Les regles metier restent dans `suivi-projet.md` section 2 (D1, A1...).

## Alternatives ecartees

Un document unique (devient illisible) ; un outil dedie (adr-tools : dependance inutile).

## Consequences

Toute nouvelle decision technique structurante ajoute un ADR dans le meme commit que le code.

## Sources

Feuille de route R6 (`docs/07-roadmap.md` section 7).
