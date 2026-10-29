# Audit de securite (R4)

Audit du 2026-10-28 sur la version `main` (apres 1.36.5) et sur la beta en
lecture seule. Complete l'audit des dependances du 2026-10-21
(`security_audit.sh` dans le gate et la CI).

## Perimetre et methode

| Cible | Outil | Mode |
|---|---|---|
| Stack locale `http://localhost:8000` | OWASP ZAP 2.16.1 `zap-baseline.py` (client `/app/`) | Passif |
| Stack locale, 86 routes de `openapi.json` | ZAP `zap-api-scan.py`, compte de test authentifie | Actif (injections, XSS, divulgation d'erreurs) |
| `https://beta.beevarium.fr`, `https://beevarium.fr` | `curl` (en-tetes, CORS, redirection), `openssl s_client` (versions TLS) | Lecture publique |
| VPS `<vps>` | `nc` sur 10 ports, banniere et methodes d'authentification SSH | Exterieur, sans identifiant |
| Code | Bandit (`-ll`), relecture ciblee (IP client, limiteur, en-tetes) | Statique |

Aucun scan actif ni test d'intrusion contre la beta : elle porte des donnees
reelles. Rapports ZAP : `artifacts/zap/` (non versionne).

## Resultats

Points conformes : seuls 22, 80 et 443 sont ouverts (PostgreSQL, API,
supervision et socket Docker fermes) ; TLS 1.0 et 1.1 refuses, TLS 1.2 et 1.3
acceptes ; HTTP redirige en 308 vers HTTPS ; CSP stricte, HSTS, `nosniff`,
`X-Frame-Options DENY`, `Referrer-Policy no-referrer` ; CORS sans
`Access-Control-Allow-Origin` pour une origine etrangere ; scan actif de
l'API : 0 echec sur 113 regles, aucune erreur 500 ; Bandit : 0 alerte moyenne
ou haute ; OpenSSH 9.2p1 `deb12u10` a jour.

| # | Constat | Gravite | Statut |
|---|---|---|---|
| S1 | L'IP client etait la **premiere** valeur de `X-Forwarded-For`, fournie par le client : contournement possible de la limitation de debit par IP (connexion, inscription, reinitialisation) si le proxy conserve l'en-tete entrant | Moyenne | Corrige : derniere valeur, ajoutee par Caddy (`routers/auth.py`) |
| S2 | Documentation interactive `/docs`, `/redoc`, `/openapi.json` publique sur la beta : cartographie complete de l'API | Faible | Corrige : servie seulement en `dev`, `test`, `local` (`main.py`) |
| S3 | En-tete `server: uvicorn` revele le serveur d'application | Faible | Corrige : `--no-server-header` (`Dockerfile`) |
| S4 | Pas d'isolation inter-origines (ZAP 90004, Spectre) | Faible | Corrige : `Cross-Origin-Opener-Policy` et `Cross-Origin-Resource-Policy` `same-origin` |
| S5 | **SSH accepte l'authentification par mot de passe** (`publickey,password`) : exposition au forcage | Moyenne | A faire sur le VPS (A1) |
| S6 | `beevarium.fr` (page d'accueil statique) n'envoie aucun en-tete de securite (HSTS, CSP, `nosniff`) ; `server: Caddy` sur les deux domaines | Faible | A faire dans le Caddyfile (A2) |
| S7 | Polices chargees depuis Google Fonts : l'adresse IP de chaque visiteur part chez Google, non mentionne dans la politique de confidentialite ; pas d'integrite (SRI) possible sur cette feuille dynamique (ZAP 90003) | Moyenne (RGPD) | Corrige : polices libres hebergees (A3) |
| S8 | `style-src 'unsafe-inline'` dans la CSP (ZAP 10055), requis par des styles en ligne du client | Faible | Accepte pour la beta ; a retirer avec un nettoyage du client (A6) |
| S9 | Limiteur de debit en memoire : remis a zero au redemarrage, non partage ; 10 echecs par adresse e-mail bloquent la connexion de ce compte 15 minutes (deni de service cible possible) | Faible | Accepte (instance unique, ADR 0011) |
| S10 | Pas de jeton anti-CSRF (ZAP 10202) | Info | Accepte : cookie `SameSite=strict` et corps JSON, aucune requete inter-sites possible |
| S11 | Caddyfile et configuration SSH/pare-feu non versionnes : etat du VPS non verifiable depuis le depot | Faible | Pret dans `ansible/` (non applique) : Caddyfile, `sshd_config.d`, UFW versionnes (R14) |

Faux positifs ou sans objet : `Non-Storable Content` (10049, `no-cache`
voulu), `Unexpected Content-Type` (100001, pages HTML), `Modern Web
Application` et `ZAP is Out of Date` (information).

## Plan d'actions correctives

| # | Action | Qui | Priorite | Statut |
|---|---|---|---|---|
| A0 | S1 a S4 corriges dans le code | Agent | P1 | Fait, deploye en 1.37.0 (2026-10-28) |
| A1 | Desactiver le mot de passe SSH : `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PermitRootLogin no` dans `/etc/ssh/sshd_config.d/`, `sudo sshd -t` puis `sudo systemctl reload ssh` **en gardant une session ouverte** ; verifier fail2ban (`sudo fail2ban-client status sshd`) | Concepteur | P1 | Pret dans `ansible/` (non applique) |
| A2 | Caddyfile : bloc `header` commun aux deux sites (`-Server`, HSTS, `X-Content-Type-Options nosniff`, `Referrer-Policy no-referrer`, CSP adaptee a la page statique), `sudo caddy validate` puis reload | Concepteur | P2 | Pret dans `ansible/` (non applique) |
| A3 | Heberger Kalam et Nunito Sans (SIL OFL, fichiers Fontsource 5.3.0) dans `static/app/fonts/` et `site/assets/fonts/`, retirer Google de la CSP | Agent | P2 | Fait, deploye en 1.37.0 (2026-10-28) |
| A4 | Lynis sur le VPS (`sudo apt install lynis && sudo lynis audit system`), traiter les avertissements | Concepteur | P2 | Pret dans `ansible/` (non applique) |
| A5 | Versionner Caddyfile, `sshd_config.d` et regles UFW (R14) | Agent puis concepteur | P2 | Pret dans `ansible/` (non applique) |
| A6 | Supprimer les styles en ligne du client, retirer `'unsafe-inline'` | Agent | P3 | A faire |
| A8 | Scan quotidien des images des conteneurs du VPS (Trivy) avec alerte e-mail : `scripts/linux/scan_images.sh`, installation dans [docs/06-exploitation.md](06-exploitation.md) | Agent puis concepteur | P2 | Script pret, installation sur le VPS a faire |
| A7 | Rejouer ce protocole (ZAP baseline et API sur la stack locale) avant chaque release majeure | Agent | P3 | Continu |

Commande de controle SSH depuis le poste, sans identifiant :
`ssh -o PreferredAuthentications=none -o PubkeyAuthentication=no audit@<vps>`
doit repondre `Permission denied (publickey).` une fois A1 applique.
