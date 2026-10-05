from datetime import UTC, datetime, timedelta
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.emailer import send_password_reset_email
from app.rate_limit import anonymous_limiter
from app.security import (
    create_access_token,
    generate_password_reset_token,
    get_current_user,
    hash_password,
    hash_password_reset_token,
    password_needs_rehash,
    verify_password,
)

logger = logging.getLogger("beevarium.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.environment.lower() in {"staging", "prod", "production"},
        samesite="strict",
        path="/",
    )


@router.post("/register", response_model=schemas.AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, response: Response, request: Request, db: Session = Depends(get_db)):
    if settings.environment.lower() not in {"dev", "test", "local"} and not anonymous_limiter.allow(
        f"register:ip:{_client_ip(request)}", limit=10, window=timedelta(hours=1)
    ):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Reessayez plus tard")
    email = _normalize_email(str(payload.email))
    existing_user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email deja utilise")

    allow_requested_premium = settings.environment.lower() in {"dev", "test", "local"}
    user = models.User(
        email=email,
        prenom=payload.prenom,
        auth_provider="local",
        password_hash=hash_password(payload.password),
        is_premium=settings.beta_new_users_premium or (allow_requested_premium and payload.is_premium),
    )
    db.add(user)
    db.flush()
    db.add(models.Atelier(user_id=user.id, nom="Atelier"))
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.token_version)
    _set_session_cookie(response, token)
    return schemas.AuthResponse(
        access_token=token,
        user=schemas.UserResponse.model_validate(user),
    )


@router.post("/login", response_model=schemas.AuthResponse)
def login(payload: schemas.LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    email = _normalize_email(str(payload.email))
    ip = _client_ip(request)
    ip_key = f"login:ip:{ip}"
    email_key = f"login:email:{email}"
    if not (
        anonymous_limiter.check(ip_key, limit=30, window=timedelta(minutes=15))
        and anonymous_limiter.check(email_key, limit=10, window=timedelta(minutes=15))
    ):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Reessayez plus tard")
    user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
    if user is None or user.auth_provider != "local":
        anonymous_limiter.record(ip_key)
        anonymous_limiter.record(email_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")

    if not verify_password(payload.password, user.password_hash):
        anonymous_limiter.record(ip_key)
        anonymous_limiter.record(email_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user.id, user.token_version)
    _set_session_cookie(response, token)
    return schemas.AuthResponse(
        access_token=token,
        user=schemas.UserResponse.model_validate(user),
    )


@router.post("/logout", response_model=schemas.LogoutResponse)
def logout(response: Response, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.token_version += 1
    db.add(current_user)
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return schemas.LogoutResponse(message="Deconnexion prise en compte")


@router.get("/me", response_model=schemas.UserResponse)
def read_me(response: Response, request: Request, current_user: models.User = Depends(get_current_user)):
    # Migration douce des anciens clients Bearer vers le cookie HttpOnly.
    if request.cookies.get(settings.session_cookie_name) is None:
        authorization = request.headers.get("Authorization", "")
        if authorization.lower().startswith("bearer "):
            _set_session_cookie(response, authorization.split(" ", 1)[1])
    return current_user


# Reponse volontairement identique que le compte existe ou non, pour ne pas
# permettre de tester quels e-mails sont inscrits.
_FORGOT_PASSWORD_MESSAGE = (
    "Si un compte existe pour cette adresse, un e-mail de reinitialisation vient d etre envoye."
)


@router.post("/forgot-password", response_model=schemas.MessageResponse, response_model_exclude_none=True)
def forgot_password(payload: schemas.ForgotPasswordRequest, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email = _normalize_email(str(payload.email))
    ip = _client_ip(request)
    if not (
        anonymous_limiter.allow(f"forgot:ip:{ip}", limit=20, window=timedelta(hours=1))
        and anonymous_limiter.allow(f"forgot:email:{email}", limit=settings.password_reset_max_per_hour, window=timedelta(hours=1))
    ):
        return schemas.MessageResponse(message=_FORGOT_PASSWORD_MESSAGE)
    user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
    debug_reset_url = None

    if user is not None and user.auth_provider == "local":
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
        recent_requests = (
            db.query(models.PasswordResetToken)
            .filter(
                models.PasswordResetToken.user_id == user.id,
                models.PasswordResetToken.created_at >= one_hour_ago,
            )
            .count()
        )

        if recent_requests >= settings.password_reset_max_per_hour:
            logger.warning("Trop de demandes de reinitialisation", extra={"user_id": str(user.id)})
        else:
            # Une nouvelle demande annule les liens precedents encore valides.
            db.query(models.PasswordResetToken).filter(
                models.PasswordResetToken.user_id == user.id,
                models.PasswordResetToken.used_at.is_(None),
            ).update({models.PasswordResetToken.used_at: datetime.now(UTC)})

            raw_token, token_hash = generate_password_reset_token()
            db.add(
                models.PasswordResetToken(
                    user_id=user.id,
                    token_hash=token_hash,
                    expires_at=datetime.now(UTC)
                    + timedelta(minutes=settings.password_reset_ttl_minutes),
                )
            )
            db.commit()

            reset_url = (
                f"{settings.public_base_url.rstrip('/')}/app/reset-password.html?token={raw_token}"
            )
            background_tasks.add_task(send_password_reset_email, user.email, user.prenom, reset_url)
            if settings.environment.lower() in {"dev", "test", "local"}:
                debug_reset_url = reset_url

    return schemas.MessageResponse(message=_FORGOT_PASSWORD_MESSAGE, debug_reset_url=debug_reset_url)


@router.post("/reset-password", response_model=schemas.MessageResponse)
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = hash_password_reset_token(payload.token)
    reset_token = (
        db.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.token_hash == token_hash)
        .first()
    )

    if (
        reset_token is None
        or reset_token.used_at is not None
        or reset_token.expires_at <= datetime.now(UTC)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de reinitialisation invalide ou expire",
        )

    user = db.query(models.User).filter(models.User.id == reset_token.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de reinitialisation invalide ou expire",
        )

    user.password_hash = hash_password(payload.password)
    # Invalide toutes les sessions ouvertes: un mot de passe change deconnecte partout.
    user.token_version += 1
    reset_token.used_at = datetime.now(UTC)
    db.add(user)
    db.add(reset_token)
    db.commit()

    logger.info("Mot de passe reinitialise", extra={"user_id": str(user.id)})
    return schemas.MessageResponse(message="Mot de passe mis a jour. Vous pouvez vous connecter.")
