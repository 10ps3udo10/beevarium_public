#!/usr/bin/env python3
"""Surveillance de la beta : envoie un e-mail quand un controle echoue.

Lance toutes les 5 minutes par le timer systemd `beevarium-watchdog.timer`.
Controles : sante publique de l'API, conteneurs en marche, espace disque,
fraicheur des sauvegardes locales et hors site, restaurations de controle.

Un e-mail part quand un probleme apparait, puis toutes les 6 heures tant qu'il
dure, et une fois au retour a la normale. L'envoi passe par le SMTP de
`.env.target`, directement depuis l'hote : il fonctionne meme API arretee.

Usage : python3 scripts/watchdog.py [.env.target] [--dry-run]
"""

from __future__ import annotations

import json
import shutil
import smtplib
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
BACKUPS = REPO / "artifacts" / "backups"
STATE_FILE = REPO / "artifacts" / "watchdog-state.json"
REMINDER = timedelta(hours=6)
DISK_LIMIT_PERCENT = 85
# Le VPS compte en UTC ; les e-mails donnent l'heure de Paris.
PARIS = ZoneInfo("Europe/Paris")


def paris(moment: datetime) -> str:
    return f"{moment.astimezone(PARIS):%d/%m/%Y a %H:%M} (heure de Paris)"


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check_report(name: str, label: str, date_key: str, max_age: timedelta, now: datetime) -> str | None:
    path = BACKUPS / name
    if not path.exists():
        return f"{label} : rapport {name} absent"
    report = json.loads(path.read_text())
    if report.get("status") != "ok":
        return f"{label} : statut {report.get('status')!r}"
    when = parse_time(report.get(date_key)) or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    if now - when > max_age:
        return f"{label} : derniere execution le {paris(when)}"
    return None


def run_checks(env: dict[str, str], now: datetime) -> list[str]:
    problems: list[str] = []
    url = env.get("WATCHDOG_HEALTH_URL", "https://beta.beevarium.fr/health")
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            health = json.loads(response.read())
        if health.get("status") != "ok" or health.get("database") != "connected":
            problems.append(f"API : sante degradee {health}")
    except Exception as error:  # noqa: BLE001 - toute erreur reseau est une alerte
        problems.append(f"API : {url} injoignable ({error})")

    stack = env.get("STACK_NAME") or "beevarium"
    for container in (f"{stack}_api_target", f"{stack}_db_target"):
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container],
            capture_output=True, text=True, check=False,
        )
        if result.stdout.strip() != "true":
            problems.append(f"Conteneur {container} arrete")

    usage = shutil.disk_usage("/")
    percent = round(usage.used * 100 / usage.total)
    if percent >= DISK_LIMIT_PERCENT:
        problems.append(f"Disque : {percent} % utilise")

    checks = [
        ("last-backup.json", "Sauvegarde locale", "created_at", timedelta(hours=26)),
        ("last-restore-check.json", "Restauration de controle", "verified_at", timedelta(days=8)),
    ]
    if env.get("BACKUP_OFFSITE_REMOTE"):
        checks += [
            ("last-offsite.json", "Copie hors site", "created_at", timedelta(hours=26)),
            ("last-offsite-check.json", "Restauration hors site", "verifie_le", timedelta(days=8)),
        ]
    for name, label, date_key, max_age in checks:
        problem = check_report(name, label, date_key, max_age, now)
        if problem:
            problems.append(problem)
    return problems


def send_alert(env: dict[str, str], subject: str, body: str) -> None:
    recipient = env.get("ALERT_EMAIL", "contact@beevarium.fr")
    sender = env.get("SMTP_FROM_EMAIL", "no-reply@beevarium.fr")
    message = EmailMessage()
    message["From"] = f"Beevarium supervision <{sender}>"
    message["To"] = recipient
    message["Subject"] = subject
    message["Date"] = formatdate(usegmt=True)
    message["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    message["Auto-Submitted"] = "auto-generated"
    message.set_content(body)
    host, port = env["SMTP_HOST"], int(env.get("SMTP_PORT", "587"))
    username, password = env.get("SMTP_USERNAME"), env.get("SMTP_PASSWORD")
    if env.get("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            if username:
                server.login(username, password or "")
            server.send_message(message)
    else:
        with smtplib.SMTP_SSL(host, port, timeout=15) as server:
            if username:
                server.login(username, password or "")
            server.send_message(message)


def main() -> int:
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    env = read_env(REPO / (args[0] if args else ".env.target"))
    now = datetime.now(timezone.utc)
    problems = run_checks(env, now)

    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"problems": [], "notified_at": None}
    previous = state.get("problems", [])
    notified_at = parse_time(state.get("notified_at"))
    subject = None
    if problems and (problems != previous or notified_at is None or now - notified_at >= REMINDER):
        subject = f"[Beevarium] ALERTE : {len(problems)} probleme(s)"
        body = "Controles en echec :\n\n" + "\n".join(f"- {item}" for item in problems)
    elif not problems and previous:
        subject = "[Beevarium] Retour a la normale"
        body = "Tous les controles sont de nouveau verts.\n\nProblemes resolus :\n\n" + "\n".join(f"- {item}" for item in previous)

    print(f"[watchdog] {now:%Y-%m-%d %H:%M} UTC : {len(problems)} probleme(s)")
    for item in problems:
        print(f"  - {item}")
    if subject and not dry_run:
        if not env.get("SMTP_HOST"):
            print("[watchdog] SMTP_HOST absent : alerte non envoyee", file=sys.stderr)
            return 1
        send_alert(env, subject, body + f"\n\nVerifie le {paris(now)}.")
        notified_at = now
        print(f"[watchdog] e-mail envoye : {subject}")
    if not dry_run:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps({
            "problems": problems,
            "notified_at": notified_at.isoformat() if notified_at and problems else None,
            "checked_at": now.isoformat(),
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
