# Decisions d'architecture (ADR)

Journal des choix techniques structurants (voir ADR 0001). Les regles metier
decidees par le concepteur restent dans `suivi-projet.md` section 2.

Nouvelle decision : copier un ADR existant, prendre le numero suivant, statut
`Propose` puis `Accepte` ; une decision remplacee garde son fichier avec le
statut `Remplace par NNNN`. Date : premiere trace dans Git ou date du choix.

| ADR | Date | Decision | Statut |
|---|---|---|---|
| [0001](0001-tenir-un-journal-des-decisions-d-architecture.md) | 2026-10-28 | Tenir un journal des decisions d'architecture | Accepte |
| [0002](0002-api-fastapi-postgresql-16-et-migrations-sql-versionnees.md) | 2026-08-11 | API FastAPI, PostgreSQL 16 et migrations SQL versionnees | Accepte |
| [0003](0003-client-web-vanilla-en-modules-es-sans-build-servi-par-l-api.md) | 2026-08-11 | Client web vanilla en modules ES, sans build, servi par l'API | Accepte |
| [0004](0004-hebergement-vps-ovh-debian-12-docker-compose-et-caddy.md) | 2026-08-27 | Hebergement : VPS OVH Debian 12, Docker Compose et Caddy | Accepte |
| [0005](0005-authentification-pbkdf2-jwt-revocable-et-cookie-httponly.md) | 2026-09-20 | Authentification : PBKDF2, JWT revocable et cookie HttpOnly | Accepte |
| [0006](0006-hors-ligne-limite-aux-visites-de-ruche.md) | 2026-08-13 | Hors ligne limite aux visites de ruche | Accepte |
| [0007](0007-sauvegardes-locales-et-hors-site-chiffrees-restaurations-de-controle.md) | 2026-08-27 | Sauvegardes locales et hors site chiffrees, restaurations de controle | Accepte |
| [0008](0008-supervision-par-alertes-e-mail-outils-de-suivi-non-exposes.md) | 2026-08-27 | Supervision par alertes e-mail, outils de suivi non exposes | Accepte |
| [0009](0009-deploiement-par-script-bash-un-tag-git-par-deploiement.md) | 2026-10-05 | Deploiement par script bash, un tag Git par deploiement | Accepte |
| [0010](0010-qualite-gates-locaux-playwright-en-conteneur-ci-github-actions.md) | 2026-08-27 | Qualite : gates locaux, Playwright en conteneur, CI GitHub Actions | Accepte |
| [0011](0011-limitation-de-debit-en-memoire.md) | 2026-09-20 | Limitation de debit en memoire | Accepte |
| [0012](0012-journal-technique-conserve-6-mois.md) | 2026-10-05 | Journal technique conserve 6 mois | Accepte |
| [0013](0013-depot-public-sans-historique.md) | 2026-10-03 | Depot public sans historique | Accepte |
| [0014](0014-applications-mobiles-par-capacitor-ia-vocale-locale.md) | 2026-08-31 | Applications mobiles par Capacitor, IA vocale locale | Propose |
| [0015](0015-paiement-stripe-sur-le-web-achats-integres-sur-les-stores.md) | 2026-08-31 | Paiement : Stripe sur le web, achats integres sur les stores | Propose |
| [0016](0016-suppression-de-compte-par-cascade-sql-export-par-requetes-explicites.md) | 2026-10-28 | Suppression de compte par cascade SQL, export par requetes explicites | Accepte |
| [0017](0017-configuration-du-vps-par-ansible.md) | 2026-10-28 | Configuration du VPS par Ansible, bash conserve pour le deploiement | Propose |
| [0018](0018-double-authentification-totp-et-role-administrateur.md) | 2026-10-28 | Double authentification TOTP et role administrateur | Propose |
