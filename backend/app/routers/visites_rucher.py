from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.ownership import get_owned_rucher
from app.security import get_current_user


router = APIRouter(prefix="/visites-rucher", tags=["visites-rucher"])



@router.get("", response_model=list[schemas.VisiteRucherResponse])
def list_visites_rucher(
    rucher_id: UUID | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.VisiteRucher).join(models.Rucher, models.VisiteRucher.rucher_id == models.Rucher.id)
    query = query.filter(models.Rucher.user_id == current_user.id)
    if rucher_id is not None:
        get_owned_rucher(db, rucher_id, current_user.id)
        query = query.filter(models.VisiteRucher.rucher_id == rucher_id)
    return query.order_by(models.VisiteRucher.date_visite.desc()).all()


@router.post("", response_model=schemas.VisiteRucherResponse, status_code=status.HTTP_201_CREATED)
def create_visite_rucher(
    payload: schemas.VisiteRucherCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_rucher(db, payload.rucher_id, current_user.id)
    visite = models.VisiteRucher(**payload.model_dump())
    db.add(visite)
    db.commit()
    db.refresh(visite)
    return visite


@router.get("/{visite_rucher_id}", response_model=schemas.VisiteRucherResponse)
def get_visite_rucher(
    visite_rucher_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    visite = db.get(models.VisiteRucher, visite_rucher_id)
    if visite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visite rucher introuvable")
    get_owned_rucher(db, visite.rucher_id, current_user.id)
    return visite


@router.put("/{visite_rucher_id}", response_model=schemas.VisiteRucherResponse)
def update_visite_rucher(
    visite_rucher_id: UUID,
    payload: schemas.VisiteRucherUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    visite = db.get(models.VisiteRucher, visite_rucher_id)
    if visite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visite rucher introuvable")

    get_owned_rucher(db, visite.rucher_id, current_user.id)
    get_owned_rucher(db, payload.rucher_id, current_user.id)

    for field, value in payload.model_dump().items():
        setattr(visite, field, value)

    db.commit()
    db.refresh(visite)
    return visite


@router.delete("/{visite_rucher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visite_rucher(
    visite_rucher_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    visite = db.get(models.VisiteRucher, visite_rucher_id)
    if visite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visite rucher introuvable")

    get_owned_rucher(db, visite.rucher_id, current_user.id)

    db.delete(visite)
    db.commit()
    return None