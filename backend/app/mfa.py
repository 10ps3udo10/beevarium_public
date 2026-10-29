"""Verification des codes de la double authentification (TOTP ou code de secours)."""

from datetime import UTC, datetime, timedelta
import hashlib
import secrets

from fastapi import HTTPException, status
from sqlalchemy import or_, update
from sqlalchemy.orm import Session

from app import models, totp
from app.rate_limit import anonymous_limiter

RECOVERY_CODE_COUNT = 8


def limiter_key(user: models.User) -> str:
    return f"mfa:user:{user.id}"


def check_rate_limit(user: models.User) -> None:
    if not anonymous_limiter.check(limiter_key(user), limit=5, window=timedelta(minutes=15)):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Reessayez plus tard")


def _hash_recovery_code(code: str) -> str:
    normalized = code.strip().lower().replace("-", "").replace(" ", "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def generate_recovery_codes(db: Session, user: models.User) -> list[str]:
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = secrets.token_hex(5)
        codes.append(f"{raw[:5]}-{raw[5:]}")
        db.add(models.MfaRecoveryCode(user_id=user.id, code_hash=_hash_recovery_code(raw)))
    return codes


def verify_code(db: Session, user: models.User, code: str, *, allow_recovery: bool) -> bool:
    """Valide un code (limiteur deja verifie par l'appelant). Consomme le pas TOTP ou le code de secours.

    Echec : enregistre dans le limiteur. Succes : modifications ajoutees a la session (commit par l'appelant).
    """
    code = code.strip()
    step = totp.verify(user.mfa_secret, code, user.mfa_last_step) if user.mfa_secret else None
    if step is not None:
        # Mise a jour atomique : deux requetes simultanees avec le meme code ne passent pas toutes les deux.
        consumed = db.execute(
            update(models.User)
            .where(models.User.id == user.id, or_(models.User.mfa_last_step.is_(None), models.User.mfa_last_step < step))
            .values(mfa_last_step=step)
        ).rowcount
        if consumed:
            return True
    elif allow_recovery and len(code.replace("-", "")) == 10:
        consumed = db.execute(
            update(models.MfaRecoveryCode)
            .where(
                models.MfaRecoveryCode.user_id == user.id,
                models.MfaRecoveryCode.code_hash == _hash_recovery_code(code),
                models.MfaRecoveryCode.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        ).rowcount
        if consumed:
            return True
    anonymous_limiter.record(limiter_key(user))
    return False
