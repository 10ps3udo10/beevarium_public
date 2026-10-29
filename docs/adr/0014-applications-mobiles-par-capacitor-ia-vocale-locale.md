# ADR 0014 : Applications mobiles par Capacitor, IA vocale locale

- Date : 2026-08-31
- Statut : Propose

## Contexte

Publication future sur les stores ; saisie vocale au rucher, mains occupees, souvent sans reseau.

## Decision

Encapsuler le client web existant avec Capacitor (memes ecrans, meme IndexedDB, APIs natives) apres stabilisation de la beta. Transcription vocale par Whisper `base` telecharge a la demande et execute sur le telephone, sans envoi d'audio au serveur ; le serveur ne recoit que le texte pour l'extraction structuree.

## Alternatives ecartees

React Native ou Flutter (reecriture du client) ; transcription serveur (audio personnel envoye, cout, depend du reseau).

## Consequences

A mesurer sur telephones reels avant decision definitive (taille du modele, temps de transcription).

## Sources

Commits `e822b50` (2026-08-13), `7e9071d` (2026-08-31) ; `docs/07-roadmap.md`.
