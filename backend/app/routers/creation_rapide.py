from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.creation_rapide import analyse_file, create_hives, ensure_rucher_quota, import_lines, normalize_format, validate_hive_type, verify_lines
from app.database import get_db
from app.ownership import get_owned_rucher
from app.security import get_current_user


router = APIRouter(tags=["creation-rapide"])


def _require_premium(user: models.User) -> None:
    if not user.is_premium:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Fonction reservee aux comptes premium")


@router.post("/ruchers/creation-rapide", response_model=schemas.CreationRapideResponse, status_code=status.HTTP_201_CREATED)
def creation_rapide(
    payload: schemas.CreationRapideRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cree un rucher et ses ruches, ou des ruches dans un rucher existant.

    Tout ou rien : un identifiant deja pris ou la limite gratuite de ruchers
    annulent l'ensemble.
    """
    if (payload.rucher is None) == (payload.rucher_id is None):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Indiquer un nouveau rucher ou un rucher existant")
    for hive in payload.ruches:
        if hive.format_ruche:
            known, error = normalize_format(hive.format_ruche)
            if error:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)
            hive.format_ruche = known
    if payload.rucher_id is not None:
        rucher = get_owned_rucher(db, payload.rucher_id, current_user.id)
    else:
        ensure_rucher_quota(db, current_user)
        rucher = models.Rucher(**payload.rucher.model_dump(), user_id=current_user.id)
        db.add(rucher)
        db.flush()
    try:
        created = create_hives(db, current_user, rucher, payload.ruches)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un identifiant de ruche est deja utilise")
    db.refresh(rucher)
    return schemas.CreationRapideResponse(rucher=rucher, ruches_creees=created)


@router.get("/modeles-ruche", response_model=list[schemas.ModeleRucheResponse])
def list_modeles(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_premium(current_user)
    return (
        db.query(models.ModeleRuche)
        .filter(models.ModeleRuche.user_id == current_user.id)
        .order_by(models.ModeleRuche.nom.asc())
        .all()
    )


@router.post("/modeles-ruche", response_model=schemas.ModeleRucheResponse, status_code=status.HTTP_201_CREATED)
def create_modele(
    payload: schemas.ModeleRucheCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_premium(current_user)
    name = payload.nom.strip()
    exists = (
        db.query(models.ModeleRuche)
        .filter(models.ModeleRuche.user_id == current_user.id, func.lower(func.trim(models.ModeleRuche.nom)) == name.lower())
        .first()
    )
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un modele porte deja ce nom")
    validate_hive_type(db, current_user.id, payload.ref_type_ruche_id)
    data = payload.model_dump()
    data["nom"] = name
    if data["format_ruche"]:
        known, error = normalize_format(data["format_ruche"])
        if error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)
        data["format_ruche"] = known
    modele = models.ModeleRuche(**data, user_id=current_user.id)
    db.add(modele)
    db.commit()
    db.refresh(modele)
    return modele


@router.delete("/modeles-ruche/{modele_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_modele(modele_id: UUID, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_premium(current_user)
    modele = db.get(models.ModeleRuche, modele_id)
    if modele is None or modele.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modele introuvable")
    db.delete(modele)
    db.commit()


@router.post("/import/ruches/analyse", response_model=schemas.ImportVerificationResponse)
def import_analyse(
    payload: schemas.ImportAnalyseRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lit le fichier, devine les colonnes et verifie chaque ligne, sans rien creer."""
    _require_premium(current_user)
    headers, mapping, lines = analyse_file(payload)
    if not lines:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Aucune ligne de donnees sous l'en-tete")
    result = verify_lines(db, current_user, lines)
    result.colonnes = headers
    result.correspondance = mapping
    return result


@router.post("/import/ruches/verifier", response_model=schemas.ImportVerificationResponse)
def import_verifier(
    payload: schemas.ImportVerificationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reverifie des lignes corrigees dans l'apercu."""
    _require_premium(current_user)
    return verify_lines(db, current_user, payload.lignes)


@router.post("/import/ruches", response_model=schemas.ImportResultat, status_code=status.HTTP_201_CREATED)
def import_valider(
    payload: schemas.ImportVerificationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cree ruchers et ruches si aucune ligne n'est en erreur ; sinon rien."""
    _require_premium(current_user)
    try:
        result = import_lines(db, current_user, payload.lignes)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un identifiant de ruche est deja utilise")
    return result
