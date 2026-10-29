from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app import mfa, models, schemas, totp
from app.config import settings
from app.database import get_db
from app.rate_limit import anonymous_limiter
from app.security import create_access_token, get_current_user, set_session_cookie, verify_password


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=schemas.UserResponse)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=schemas.UserResponse)
def update_current_user(
    payload: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.prenom is not None:
        current_user.prenom = payload.prenom
    if payload.tag_favorites is not None:
        current_user.tag_favorites = payload.tag_favorites

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


# Export RGPD (droit d'acces et portabilite) : toutes les donnees rattachees au
# compte, table par table. Une nouvelle table liee a un utilisateur, un rucher,
# une ruche ou une visite doit etre ajoutee ici (et dans docs/13-registre-rgpd.md).
# Exclus : hash du mot de passe, jetons de reinitialisation, cles d'idempotence
# (copies techniques de reponses deja exportees), secret TOTP et codes de secours.
_EXPORT_QUERIES = {
    "ruchers": "SELECT t.* FROM ruchers t WHERE t.user_id = :user_id ORDER BY t.id",
    "visites_rucher": "SELECT t.* FROM visites_rucher t JOIN ruchers p ON p.id = t.rucher_id WHERE p.user_id = :user_id ORDER BY t.id",
    "ateliers": "SELECT t.* FROM ateliers t WHERE t.user_id = :user_id ORDER BY t.id",
    "ruches": "SELECT t.* FROM ruches t WHERE t.user_id = :user_id ORDER BY t.id",
    "ruche_tags": "SELECT t.* FROM ruche_tags t WHERE t.user_id = :user_id ORDER BY t.id",
    "reines": "SELECT t.* FROM reines t JOIN ruches r ON r.id = t.ruche_id WHERE r.user_id = :user_id ORDER BY t.id",
    "visites_ruche": "SELECT t.* FROM visites_ruche t JOIN ruches r ON r.id = t.ruche_id WHERE r.user_id = :user_id ORDER BY t.id",
    "actions_visite": "SELECT t.* FROM actions_visite t JOIN visites_ruche v ON v.id = t.visite_ruche_id "
    "JOIN ruches r ON r.id = v.ruche_id WHERE r.user_id = :user_id ORDER BY t.visite_ruche_id",
    "gestion_cadres": "SELECT t.* FROM gestion_cadres t JOIN ruches r ON r.id = t.ruche_id WHERE r.user_id = :user_id ORDER BY t.id",
    "interventions_sanitaires": "SELECT t.* FROM interventions_sanitaires t JOIN ruches r ON r.id = t.ruche_id WHERE r.user_id = :user_id ORDER BY t.id",
    "mouvements_hausses": "SELECT t.* FROM mouvements_hausses t JOIN ruches r ON r.id = t.ruche_id WHERE r.user_id = :user_id ORDER BY t.id",
    "recoltes": "SELECT t.* FROM recoltes t JOIN ruches r ON r.id = t.ruche_id WHERE r.user_id = :user_id ORDER BY t.id",
    "ruche_transvasements": "SELECT t.* FROM ruche_transvasements t WHERE t.user_id = :user_id ORDER BY t.id",
    "materiel_atelier": "SELECT t.* FROM materiel_atelier t WHERE t.user_id = :user_id ORDER BY t.id",
    "modeles_ruche": "SELECT t.* FROM modeles_ruche t WHERE t.user_id = :user_id ORDER BY t.id",
    "ref_action_cadre": "SELECT t.* FROM ref_action_cadre t WHERE t.user_id = :user_id ORDER BY t.id",
    "ref_action_visite": "SELECT t.* FROM ref_action_visite t WHERE t.user_id = :user_id ORDER BY t.id",
    "ref_statut_ruche": "SELECT t.* FROM ref_statut_ruche t WHERE t.user_id = :user_id ORDER BY t.id",
    "ref_type_intervention": "SELECT t.* FROM ref_type_intervention t WHERE t.user_id = :user_id ORDER BY t.id",
    "ref_type_materiel": "SELECT t.* FROM ref_type_materiel t WHERE t.user_id = :user_id ORDER BY t.id",
    "ref_type_ruche": "SELECT t.* FROM ref_type_ruche t WHERE t.user_id = :user_id ORDER BY t.id",
    "retours_beta": "SELECT t.id, t.category, t.message, t.context, t.created_at, t.traite_le, t.note_traitement "
    "FROM beta_feedback t WHERE t.user_id = :user_id ORDER BY t.created_at",
    "journal_technique": "SELECT t.method, t.path, t.status_code, t.created_at FROM api_events t "
    "WHERE t.user_id = :user_id ORDER BY t.created_at",
}


@router.get("/me/export")
def export_current_user(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    donnees = {
        nom: jsonable_encoder([dict(ligne) for ligne in db.execute(text(requete), {"user_id": current_user.id}).mappings()])
        for nom, requete in _EXPORT_QUERIES.items()
    }
    return {
        "format": "beevarium-export-v1",
        "exporte_le": datetime.now(UTC).isoformat(),
        "compte": schemas.UserResponse.model_validate(current_user).model_dump(mode="json"),
        "donnees": donnees,
    }


def _check_password(user: models.User, password: str) -> None:
    mfa.check_rate_limit(user)
    if not user.password_hash or not verify_password(password, user.password_hash):
        anonymous_limiter.record(mfa.limiter_key(user))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mot de passe incorrect")


def _renew_session(user: models.User, response: Response, db: Session) -> str:
    """Active/desactive la MFA invalide les autres sessions ; la session courante recoit un nouveau jeton."""
    user.token_version += 1
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.token_version)
    set_session_cookie(response, token)
    return token


@router.post("/me/mfa/setup", response_model=schemas.MfaSetupResponse)
def mfa_setup(
    payload: schemas.MfaPasswordRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_password(current_user, payload.password)
    if current_user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Double authentification deja activee")
    # Secret en attente : il ne protege rien tant que /mfa/enable n'a pas valide un premier code.
    current_user.mfa_secret = totp.generate_secret()
    current_user.mfa_last_step = None
    db.add(current_user)
    db.commit()
    return schemas.MfaSetupResponse(
        secret=current_user.mfa_secret,
        otpauth_uri=totp.otpauth_uri(current_user.mfa_secret, current_user.email),
    )


@router.post("/me/mfa/enable", response_model=schemas.MfaEnableResponse)
def mfa_enable(
    payload: schemas.MfaCodeRequest,
    response: Response,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Double authentification deja activee")
    if not current_user.mfa_secret:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lancez d'abord la configuration")
    mfa.check_rate_limit(current_user)
    if not mfa.verify_code(db, current_user, payload.code, allow_recovery=False):
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Code invalide")
    current_user.mfa_enabled_at = datetime.now(UTC)
    db.execute(delete(models.MfaRecoveryCode).where(models.MfaRecoveryCode.user_id == current_user.id))
    codes = mfa.generate_recovery_codes(db, current_user)
    token = _renew_session(current_user, response, db)
    return schemas.MfaEnableResponse(
        recovery_codes=codes,
        access_token=token,
        user=schemas.UserResponse.model_validate(current_user),
    )


@router.post("/me/mfa/disable", response_model=schemas.AuthResponse, response_model_exclude_none=True)
def mfa_disable(
    payload: schemas.MfaDisableRequest,
    response: Response,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Double authentification non activee")
    _check_password(current_user, payload.password)
    if not mfa.verify_code(db, current_user, payload.code, allow_recovery=True):
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Code invalide")
    current_user.mfa_secret = None
    current_user.mfa_enabled_at = None
    current_user.mfa_last_step = None
    db.execute(delete(models.MfaRecoveryCode).where(models.MfaRecoveryCode.user_id == current_user.id))
    token = _renew_session(current_user, response, db)
    return schemas.AuthResponse(access_token=token, user=schemas.UserResponse.model_validate(current_user))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user(
    payload: schemas.AccountDeleteRequest,
    response: Response,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Suppression definitive : ruchers, ruches, visites, recoltes, stock et retours
    # partent en cascade ; le journal technique est anonymise (SET NULL).
    limiter_key = f"delete-account:user:{current_user.id}"
    if not anonymous_limiter.check(limiter_key, limit=5, window=timedelta(minutes=15)):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Reessayez plus tard")
    if not current_user.password_hash or not verify_password(payload.password, current_user.password_hash):
        anonymous_limiter.record(limiter_key)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mot de passe incorrect")
    # Suppression SQL directe : la cascade est faite par PostgreSQL, pas par l'ORM.
    db.execute(delete(models.User).where(models.User.id == current_user.id))
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: UUID, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse")

    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    return user
