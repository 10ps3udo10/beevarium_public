from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user


router = APIRouter(prefix="/atelier", tags=["atelier"])


@router.get("", response_model=schemas.AtelierResponse)
def get_atelier(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    atelier = db.query(models.Atelier).filter(models.Atelier.user_id == current_user.id).first()
    if atelier is None:
        atelier = models.Atelier(user_id=current_user.id, nom="Atelier")
        db.add(atelier)
        db.commit()
        db.refresh(atelier)
    return atelier