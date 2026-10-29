# ADR 0008 : Supervision par alertes e-mail, outils de suivi non exposes

- Date : 2026-08-27
- Statut : Accepte

## Contexte

Une personne exploite la beta : il faut etre prevenu d'une panne sans surveiller un tableau de bord.

## Decision

`scripts/watchdog.py` toutes les 5 minutes (timer systemd utilisateur) : alerte e-mail a l'apparition d'un probleme, rappel toutes les 6 h, fonctionne meme API arretee. Netdata et Uptime Kuma lies a 127.0.0.1, consultes par tunnel SSH ; le socket Docker passe par `docker-socket-proxy`. E-mails via OVH en SMTP STARTTLS avec SPF, DKIM et DMARC.

## Alternatives ecartees

Service de supervision externe (cout, donnees) ; montage direct de `docker.sock` (equivaut a root).

## Consequences

Pas encore d'engagement de service mesure ni de tableau mensuel (R7).

## Sources

Commits `49faecd`, `3876237` ; `docs/06-exploitation.md`.
