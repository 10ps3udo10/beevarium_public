from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user


router = APIRouter(prefix="/cadres", tags=["cadres"])


def _build_cadre_age_row(db: Session, ruche: models.Ruche, current_year: int) -> schemas.CadreAgeDetailResponse:
    rows = (
        db.query(
            models.GestionCadres.annee_cire.label("annee_cire"),
            func.sum(models.GestionCadres.quantite).label("quantite"),
        )
        .filter(models.GestionCadres.ruche_id == ruche.id, models.GestionCadres.annee_cire.is_not(None))
        .group_by(models.GestionCadres.annee_cire)
        .order_by(models.GestionCadres.annee_cire.asc())
        .all()
    )

    buckets: list[schemas.CadreAgeBucket] = []
    ages: list[int] = []
    total_cadres_avec_annee_cire = 0
    cadres_plus_de_3_ans = 0

    for row in rows:
        age_cire = max(current_year - int(row.annee_cire), 0)
        quantite = int(row.quantite or 0)
        total_cadres_avec_annee_cire += quantite
        ages.extend([age_cire] * quantite)
        if age_cire > 3:
            cadres_plus_de_3_ans += quantite
        buckets.append(schemas.CadreAgeBucket(age_cire=age_cire, quantite=quantite))

    age_moyen_cire = sum(ages) / len(ages) if ages else None
    age_max_cire = max(ages) if ages else None

    return schemas.CadreAgeDetailResponse(
        ruche_id=ruche.id,
        identifiant_personnalise=ruche.identifiant_personnalise,
        total_cadres_declares=total_cadres_avec_annee_cire,
        total_cadres_avec_annee_cire=total_cadres_avec_annee_cire,
        age_moyen_cire=round(age_moyen_cire, 2) if age_moyen_cire is not None else None,
        age_max_cire=age_max_cire,
        cadres_plus_de_3_ans=cadres_plus_de_3_ans,
        alerte_renouvellement=cadres_plus_de_3_ans > 0,
        buckets=buckets,
    )


@router.get("/stats/par-ruche", response_model=list[schemas.CadreAgeDetailResponse])
def get_cadre_age_stats_by_ruche(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_year = datetime.now().year
    ruches = (
        db.query(models.Ruche)
        .filter(models.Ruche.user_id == current_user.id, models.Ruche.archived_at.is_(None))
        .order_by(models.Ruche.identifiant_personnalise.asc())
        .all()
    )
    return [_build_cadre_age_row(db, ruche, current_year) for ruche in ruches]


@router.get("/alertes/renouvellement", response_model=list[schemas.CadreAgeDetailResponse])
def get_cadre_renewal_alerts(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    all_stats = get_cadre_age_stats_by_ruche(current_user=current_user, db=db)
    return [item for item in all_stats if item.alerte_renouvellement]
