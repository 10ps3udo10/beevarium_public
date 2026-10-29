# ADR 0017 : Configuration du VPS par Ansible, bash conserve pour le deploiement

- Date : 2026-10-28
- Statut : Propose

## Contexte

L'etat du VPS (SSH, pare-feu, Caddyfile, Docker, timers) n'etait pas verifiable depuis le depot et se reconstruirait de memoire apres un incident (risque R1/R7, audit S11). Le deploiement, lui, est couvert par `deploy.sh` (ADR 0009).

## Decision

`ansible/vps.yml` et des roles par sujet (`base`, `ssh_hardening`, `firewall`, `docker`, `caddy`, `beevarium_user`, `lynis`) decrivent la configuration du VPS Debian 12 (ADR 0004). Lancement depuis un conteneur par `scripts/linux/ansible_vps.sh` (`--check` d'abord, `CONFIRM_VPS=oui` pour appliquer). L'inventaire reel reste hors Git. Le deploiement de l'application reste en bash (ADR 0009) ; les sauvegardes et la supervision gardent leurs scripts (ADR 0007, 0008), Ansible n'en installe que les timers.

## Alternatives ecartees

Tout en bash (pas d'idempotence ni de mode simulation) ; Ansible aussi pour le deploiement (reste ecarte, ADR 0009) ; Terraform ou image preconfiguree (disproportionne pour un seul VPS).

## Consequences

Le depot devient la reference de la configuration du VPS ; toute modification manuelle doit etre reportee dans un role. Le Caddyfile du VPS est ecrase au premier passage : le comparer au modele avant. A accepter puis ajouter a `docs/adr/README.md` apres une premiere application reussie.

## Sources

`ansible/` ; `docs/06-exploitation.md` section 11 ; `docs/14-audit-securite.md` (A1, A2, A4, A5, S11).
