from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.creation_rapide import ensure_rucher_quota
from app.database import get_db
from app.ownership import get_owned_rucher
from app.security import get_current_user


router = APIRouter(prefix="/ruchers", tags=["ruchers"])


@router.get("", response_model=list[schemas.RucherResponse])
def list_ruchers(
    nom: str | None = None,
    statut_activite: str | None = None,
    statut_peuplement: str | None = None,
    type_terrain: str | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Rucher).filter(models.Rucher.user_id == current_user.id)
    if nom is not None:
        query = query.filter(models.Rucher.nom.ilike(f"%{nom}%"))
    if statut_activite is not None:
        query = query.filter(models.Rucher.statut_activite == statut_activite)
    if statut_peuplement is not None:
        query = query.filter(models.Rucher.statut_peuplement == statut_peuplement)
    if type_terrain is not None:
        query = query.filter(models.Rucher.type_terrain == type_terrain)

    return query.order_by(models.Rucher.created_at.desc()).all()


@router.post("", response_model=schemas.RucherResponse, status_code=status.HTTP_201_CREATED)
def create_rucher(
    payload: schemas.RucherCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_rucher_quota(db, current_user)

    rucher = models.Rucher(**payload.model_dump(), user_id=current_user.id)
    db.add(rucher)
    db.commit()
    db.refresh(rucher)
    return rucher


@router.get("/{rucher_id}", response_model=schemas.RucherResponse)
def get_rucher(rucher_id: UUID, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rucher = get_owned_rucher(db, rucher_id, current_user.id)
    return rucher


@router.put("/{rucher_id}", response_model=schemas.RucherResponse)
def update_rucher(
    rucher_id: UUID,
    payload: schemas.RucherUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rucher = get_owned_rucher(db, rucher_id, current_user.id)

    for field, value in payload.model_dump().items():
        setattr(rucher, field, value)

    db.commit()
    db.refresh(rucher)
    return rucher


@router.post("/{rucher_id}/archive", response_model=schemas.RucherResponse)
def archive_rucher(
    rucher_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rucher = get_owned_rucher(db, rucher_id, current_user.id)

    rucher.statut_activite = "inactif"
    db.commit()
    db.refresh(rucher)
    return rucher


@router.delete("/{rucher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rucher(rucher_id: UUID, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rucher = get_owned_rucher(db, rucher_id, current_user.id)

    # Supprimer un rucher occupe laisserait ses ruches sans emplacement
    # (rucher_id mis a NULL hors Atelier) : il faut d'abord les deplacer.
    hives_count = db.query(models.Ruche).filter(models.Ruche.rucher_id == rucher.id).count()
    if hives_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rucher non vide : deplace d'abord ses {hives_count} ruche(s).",
        )

    db.delete(rucher)
    db.commit()
    return None
