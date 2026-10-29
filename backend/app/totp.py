"""TOTP (RFC 6238, SHA-1, 6 chiffres, pas de 30 s) en stdlib uniquement."""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

STEP_SECONDS = 30
DIGITS = 6


def generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def current_step(now: float | None = None) -> int:
    return int((time.time() if now is None else now) // STEP_SECONDS)


def code_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**DIGITS).zfill(DIGITS)


def verify(secret: str, code: str, last_step: int | None = None, now: float | None = None) -> int | None:
    """Retourne le pas accepte (fenetre -1/0/+1) ou None. Un pas deja utilise est refuse (anti-rejeu)."""
    code = (code or "").strip().replace(" ", "")
    if len(code) != DIGITS or not code.isdigit():
        return None
    center = current_step(now)
    accepted = None
    for step in (center - 1, center, center + 1):
        if hmac.compare_digest(code_at(secret, step), code) and (last_step is None or step > last_step):
            accepted = step
    return accepted


def otpauth_uri(secret: str, email: str, issuer: str = "Beevarium") -> str:
    label = quote(f"{issuer}:{email}", safe="")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer, safe='')}&algorithm=SHA1&digits={DIGITS}&period={STEP_SECONDS}"
