from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user


router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=schemas.BetaFeedbackResponse, status_code=status.HTTP_201_CREATED)
def create_feedback(
    payload: schemas.BetaFeedbackCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    feedback = models.BetaFeedback(user_id=current_user.id, **payload.model_dump())
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/mine", response_model=list[schemas.BetaFeedbackResponse])
def list_my_feedback(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.BetaFeedback)
        .filter(models.BetaFeedback.user_id == current_user.id)
        .order_by(models.BetaFeedback.created_at.desc())
        .all()
    )