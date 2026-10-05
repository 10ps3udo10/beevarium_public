from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user


router = APIRouter(prefix="/references", tags=["references"])


REFERENCE_MODELS = {
    "type-ruche": models.RefTypeRuche,
    "statut-ruche": models.RefStatutRuche,
    "action-visite": models.RefActionVisite,
    "type-intervention": models.RefTypeIntervention,
    "action-cadre": models.RefActionCadre,
    "type-materiel": models.RefTypeMateriel,
}


def _get_reference_model(reference_type: str):
    model = REFERENCE_MODELS.get(reference_type)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type de dictionnaire introuvable")
    return model


def _get_owned_or_system_option(db: Session, model, option_id: UUID, user_id: UUID):
    option = db.get(model, option_id)
    if option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option introuvable")
    if not option.is_system and option.user_id == user_id:
        return option
    if option.is_system:
        return option
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option introuvable")


@router.get("/{reference_type}", response_model=list[schemas.ReferenceOptionResponse])
def list_reference_options(
    reference_type: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model = _get_reference_model(reference_type)
    return (
        db.query(model)
        .filter(or_(model.is_system.is_(True), model.user_id == current_user.id))
        .order_by(model.is_system.desc(), model.libelle.asc())
        .all()
    )


@router.post("/{reference_type}", response_model=schemas.ReferenceOptionResponse, status_code=status.HTTP_201_CREATED)
def create_reference_option(
    reference_type: str,
    payload: schemas.ReferenceOptionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model = _get_reference_model(reference_type)

    existing_option = (
        db.query(model)
        .filter(
            model.libelle == payload.libelle,
            or_(model.is_system.is_(True), model.user_id == current_user.id),
        )
        .first()
    )
    if existing_option is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette option existe deja")

    option = model(libelle=payload.libelle, user_id=current_user.id, is_system=False)
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


@router.put("/{reference_type}/{option_id}", response_model=schemas.ReferenceOptionResponse)
def update_reference_option(
    reference_type: str,
    option_id: UUID,
    payload: schemas.ReferenceOptionUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model = _get_reference_model(reference_type)
    option = _get_owned_or_system_option(db, model, option_id, current_user.id)

    if option.is_system:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Une option systeme ne peut pas etre modifiee")

    duplicate = (
        db.query(model)
        .filter(
            model.libelle == payload.libelle,
            model.id != option_id,
            or_(model.is_system.is_(True), model.user_id == current_user.id),
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette option existe deja")

    option.libelle = payload.libelle
    db.commit()
    db.refresh(option)
    return option


@router.delete("/{reference_type}/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference_option(
    reference_type: str,
    option_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model = _get_reference_model(reference_type)
    option = _get_owned_or_system_option(db, model, option_id, current_user.id)

    if option.is_system:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Une option systeme ne peut pas etre supprimee")

    db.delete(option)
    db.commit()
    return None