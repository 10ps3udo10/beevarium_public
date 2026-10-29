#!/usr/bin/env python3
"""Envoi d'e-mails de supervision par le SMTP de `.env.target`, depuis l'hote.

Partage par `watchdog.py` et `scripts/linux/scan_images.sh`.

Usage en ligne de commande (corps lu sur l'entree standard) :
  python3 scripts/alert_mail.py <env-file> "<sujet>" [--dry-run] < corps.txt
"""

from __future__ import annotations

import smtplib
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


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
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    env = read_env(Path(args[0]))
    subject, body = args[1], sys.stdin.read()
    if "--dry-run" in sys.argv:
        print(f"[dry-run] A : {env.get('ALERT_EMAIL', 'contact@beevarium.fr')}\n[dry-run] Sujet : {subject}\n\n{body}")
        return 0
    if not env.get("SMTP_HOST"):
        print("SMTP_HOST absent : e-mail non envoye", file=sys.stderr)
        return 1
    send_alert(env, subject, body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
