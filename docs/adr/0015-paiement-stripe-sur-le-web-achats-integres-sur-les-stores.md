# ADR 0015 : Paiement : Stripe sur le web, achats integres sur les stores

- Date : 2026-08-31
- Statut : Propose

## Contexte

L'offre Premium sera payante apres la beta.

## Decision

Web : Stripe Billing et Checkout (carte, Apple Pay, Google Pay), PayPal ensuite si besoin. Stores : achats integres Apple et Google. Le droit Premium est calcule cote serveur apres un webhook signe, dedoublonne et idempotent ; le client n'envoie jamais `is_premium`.

## Alternatives ecartees

PayPal en premier (un fournisseur de plus a rapprocher) ; Stripe dans les applications natives (refuse par les regles des stores).

## Consequences

Non active pendant la beta (comptes Premium offerts) ; statut juridique, prix et comptes fournisseurs a etablir.

## Sources

Commit `c601fa0` ; `docs/11-paiements-et-abonnements.md`.
