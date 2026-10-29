# ADR 0005 : Authentification : PBKDF2, JWT revocable et cookie HttpOnly

- Date : 2026-09-20
- Statut : Accepte

## Contexte

Comptes personnels avec donnees d'exploitation ; besoin de revoquer une session (deconnexion, reinitialisation) sans stockage de session cote serveur.

## Decision

Mots de passe en PBKDF2-SHA256 a 600 000 iterations avec sel (un ancien hash a 100 000 est recalcule a la connexion). JWT HS256 portant `ver` = `token_version` : incrementer la version invalide toutes les sessions. Session portee par un cookie `HttpOnly`, `SameSite=strict`, `Secure` hors developpement. Reinitialisation par jeton a usage unique de 30 minutes stocke en SHA-256, reponse identique que le compte existe ou non. Colonnes `auth_provider` et `provider_subject` pretes pour Apple et Google.

## Alternatives ecartees

Sessions en base (une table et un nettoyage de plus) ; jeton en `localStorage` (expose au XSS) ; bcrypt ou Argon2 (dependance native ; PBKDF2 suffit au niveau recommande).

## Consequences

Toute modification d'auth passe par les tests d'integration dedies ; `debug_reset_url` reste limite au developpement.

## Sources

Commits `09fa682`, `b897487` (2026-08-27), `9d49c5f`, `57fb7e6` (2026-09-20) ; `backend/app/security.py`.
