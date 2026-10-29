# ADR 0018 : Double authentification TOTP et role administrateur

- Date : 2026-10-28
- Statut : Propose

## Contexte

Le suivi des retours beta et des chiffres d'usage passait par des scripts SSH sur le VPS (R9). Un espace d'administration dans l'application expose des donnees de tous les comptes : il doit etre protege plus fortement qu'un simple mot de passe.

## Decision

- TOTP (RFC 6238, SHA-1, 6 chiffres, pas de 30 s) implemente en stdlib dans `backend/app/totp.py` : aucune nouvelle dependance. Fenetre -1/0/+1 pas ; un pas deja utilise est refuse (`mfa_last_step`, mise a jour atomique) ; 8 codes de secours a usage unique, stockes sous forme d'empreinte SHA-256 ; 5 echecs par 15 minutes et par compte.
- Connexion en deux etapes : avec MFA active, `/auth/login` ne delivre ni cookie ni jeton de session mais un `mfa_token` de type `mfa` (5 minutes) refuse partout sauf sur `/auth/login/mfa`.
- Le secret TOTP est stocke en clair dans `users.mfa_secret` : la stdlib n'offre pas de chiffrement symetrique (AES) et une cle applicative stockee a cote de la base n'apporterait qu'une protection limitee. Risque : une fuite de la base (ou d'une sauvegarde) permet de generer les codes ; elle donnerait deja acces aux empreintes de mots de passe. A reevaluer si une dependance de chiffrement est acceptee (chiffrement du secret avec une cle d'environnement).
- MFA facultative pour les testeurs, obligatoire pour l'administration (`/admin/*` renvoie 403 sans MFA active).
- `is_admin` n'est modifiable que par `scripts/linux/set_admin.sh` (acces SSH au VPS) : aucune route API ne l'attribue.

## Alternatives ecartees

Bibliotheque `pyotp` (dependance pour 40 lignes) ; chiffrement du secret par une cle d'environnement avec dependance `cryptography` (reporte) ; MFA par e-mail ou SMS (cout, delivrabilite) ; role administrateur attribuable depuis l'application (escalade de privileges possible).

## Consequences

Perte du telephone et des codes de secours : la MFA du compte ne peut etre reinitialisee que manuellement en base par le concepteur (pas d'outil dedie a ce jour). L'activation ou la desactivation revoque les autres sessions (`token_version`). Les donnees MFA sont supprimees avec le compte (cascade) et jamais exportees.

## Sources

`backend/app/totp.py`, `backend/app/mfa.py`, `backend/app/routers/admin.py`, `docs/13-registre-rgpd.md`.
