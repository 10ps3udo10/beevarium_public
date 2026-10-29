from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces administrateur requis")
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Activez la double authentification pour administrer")
    return current_user


@router.get("/feedback", response_model=list[schemas.AdminFeedbackResponse])
def list_feedback(tous: bool = False, _admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    query = (
        select(models.BetaFeedback, models.User.email)
        .join(models.User, models.User.id == models.BetaFeedback.user_id)
        .order_by(models.BetaFeedback.created_at.desc())
        .limit(500)
    )
    if not tous:
        query = query.where(models.BetaFeedback.traite_le.is_(None))
    return [
        schemas.AdminFeedbackResponse(
            id=row.id,
            email=email,
            category=row.category,
            message=row.message,
            context=row.context,
            created_at=row.created_at,
            traite_le=row.traite_le,
            note_traitement=row.note_traitement,
        )
        for row, email in db.execute(query).all()
    ]


@router.post("/feedback/{feedback_id}/traiter", response_model=schemas.AdminFeedbackResponse)
def traiter_feedback(
    feedback_id: UUID,
    payload: schemas.AdminFeedbackTraiterRequest,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(models.BetaFeedback, feedback_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retour introuvable")
    row.traite_le = datetime.now(UTC)
    row.note_traitement = payload.note
    db.add(row)
    db.commit()
    db.refresh(row)
    return schemas.AdminFeedbackResponse(
        id=row.id,
        email=row.user.email,
        category=row.category,
        message=row.message,
        context=row.context,
        created_at=row.created_at,
        traite_le=row.traite_le,
        note_traitement=row.note_traitement,
    )


@router.get("/stats", response_model=schemas.AdminStatsResponse)
def stats(_admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    since = datetime.now(UTC) - timedelta(days=30)
    # Compte actif = au moins une requete authentifiee journalisee (api_events) sur 30 jours.
    return schemas.AdminStatsResponse(
        comptes=db.scalar(select(func.count()).select_from(models.User)),
        comptes_actifs_30j=db.scalar(
            select(func.count(func.distinct(models.ApiEvent.user_id))).where(
                models.ApiEvent.user_id.is_not(None), models.ApiEvent.created_at >= since
            )
        ),
        visites_30j=db.scalar(select(func.count()).select_from(models.VisiteRuche).where(models.VisiteRuche.date_visite >= since)),
    )
