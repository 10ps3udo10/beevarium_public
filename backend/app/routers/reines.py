from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.ownership import get_owned_ruche
from app.security import get_current_user


router = APIRouter(prefix="/ruches", tags=["reines"])



@router.get("/{ruche_id}/reines", response_model=list[schemas.ReineResponse])
def list_reines(ruche_id: UUID, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_owned_ruche(db, ruche_id, current_user.id)
    return db.query(models.Reine).filter(models.Reine.ruche_id == ruche_id).order_by(models.Reine.date_mise_en_place.desc()).all()


@router.post("/{ruche_id}/reines", response_model=schemas.ReineResponse, status_code=status.HTTP_201_CREATED)
def create_reine(ruche_id: UUID, payload: schemas.ReineCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ruche = get_owned_ruche(db, ruche_id, current_user.id)
    active = db.query(models.Reine).filter(models.Reine.ruche_id == ruche_id, models.Reine.statut == "active").first()
    if active is not None:
        active.statut = "terminee"
        active.date_fin = payload.date_mise_en_place
        active.motif_fin = payload.origine
    reine = models.Reine(ruche_id=ruche_id, **payload.model_dump())
    db.add(reine)
    # La fiche ruche porte aussi un resume de la reine (colonne Reine, tri,
    # formulaire) : il doit refleter la reine qui vient d'etre installee.
    ruche.reine_race = payload.race
    ruche.reine_provenance = payload.provenance
    ruche.reine_annee_marquage = payload.date_mise_en_place.year
    db.commit()
    db.refresh(reine)
    return reine