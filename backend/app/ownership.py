"""Controles d'appartenance partages par les routes metier.

Une ressource d'un autre compte est rendue en 404, comme une ressource
inexistante, pour ne pas reveler son existence.
"""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models


def get_owned_ruche(db: Session, ruche_id: UUID, user_id: UUID) -> models.Ruche:
    ruche = db.get(models.Ruche, ruche_id)
    if ruche is None or ruche.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ruche introuvable")
    return ruche


def get_owned_rucher(db: Session, rucher_id: UUID, user_id: UUID) -> models.Rucher:
    rucher = db.get(models.Rucher, rucher_id)
    if rucher is None or rucher.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rucher introuvable")
    return rucher
