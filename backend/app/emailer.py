"""Envoi d e-mails transactionnels.

Si aucun serveur SMTP n est configure, le message est journalise au lieu d etre
envoye. Cela permet de developper et de tester le parcours complet sans
dependre d un fournisseur.
"""

from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
import logging
import smtplib

from app.config import settings

logger = logging.getLogger("beevarium.email")


def smtp_is_configured() -> bool:
    return bool(settings.smtp_host)


def send_email(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> bool:
    """Retourne True si le message a ete remis au serveur SMTP."""
    if not smtp_is_configured():
        logger.warning("SMTP non configure, e-mail non envoye a %s (%s)", to_email, subject)
        # Le contenu contient un lien sensible: il n est expose qu en developpement,
        # ou il remplace la boite mail pour tester le parcours de bout en bout.
        if settings.environment.lower() in {"dev", "test", "local"}:
            logger.warning("Contenu de l e-mail non envoye:\n%s", text_body)
        return False

    sender_domain = settings.smtp_from_email.rpartition("@")[2] or "beevarium.fr"

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    message["To"] = to_email
    # Date et Message-ID sont exiges par la RFC 5322: leur absence penalise
    # fortement la delivrabilite et fait fabriquer ces en-tetes par le destinataire.
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=sender_domain)
    message["Auto-Submitted"] = "auto-generated"
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        if settings.smtp_use_tls:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                server.starttls()
                if settings.smtp_username:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(message)
        else:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                if settings.smtp_username:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(message)
    except (smtplib.SMTPException, OSError):
        # L echec ne doit jamais remonter au client: il revelerait l existence du compte.
        logger.exception("Echec d envoi d e-mail a %s (%s)", to_email, subject)
        return False

    logger.info("E-mail envoye a %s (%s)", to_email, subject)
    return True


def send_password_reset_email(to_email: str, prenom: str | None, reset_url: str) -> bool:
    salutation = f"Bonjour {prenom}," if prenom else "Bonjour,"
    ttl = settings.password_reset_ttl_minutes
    body = f"""{salutation}

Vous avez demande la reinitialisation de votre mot de passe Beevarium.

Cliquez sur ce lien pour choisir un nouveau mot de passe :
{reset_url}

Ce lien est valable {ttl} minutes et ne peut servir qu une seule fois.

Si vous n etes pas a l origine de cette demande, ignorez cet e-mail :
votre mot de passe reste inchange.

L equipe Beevarium
"""
    html = f"""<!DOCTYPE html>
<html lang="fr">
<body style="font-family: Arial, Helvetica, sans-serif; color: #2b2b2b; line-height: 1.5;">
  <p>{salutation}</p>
  <p>Vous avez demande la reinitialisation de votre mot de passe Beevarium.</p>
  <p><a href="{reset_url}" style="background:#c8860d;color:#ffffff;padding:12px 20px;border-radius:6px;text-decoration:none;display:inline-block;">Choisir un nouveau mot de passe</a></p>
  <p style="font-size:13px;color:#666;">Ou copiez ce lien dans votre navigateur :<br>{reset_url}</p>
  <p>Ce lien est valable {ttl} minutes et ne peut servir qu une seule fois.</p>
  <p>Si vous n etes pas a l origine de cette demande, ignorez cet e-mail : votre mot de passe reste inchange.</p>
  <p>L equipe Beevarium</p>
</body>
</html>"""
    return send_email(
        to_email,
        "Reinitialisation de votre mot de passe Beevarium",
        body,
        html_body=html,
    )
