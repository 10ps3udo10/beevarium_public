from datetime import date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.ownership import get_owned_ruche
from app.security import get_current_user


router = APIRouter(prefix="/recoltes", tags=["recoltes"])


def _apply_recolte_date_filters(query, year: int | None, start_date: date | None, end_date: date | None):
    if year is not None:
        query = query.filter(extract("year", models.Recolte.date_recolte) == year)
    if start_date is not None:
        query = query.filter(models.Recolte.date_recolte >= datetime.combine(start_date, time.min))
    if end_date is not None:
        query = query.filter(models.Recolte.date_recolte <= datetime.combine(end_date, time.max))
    return query



def _validate_owned_visite_ruche(db: Session, visite_ruche_id: UUID | None, user_id: UUID, ruche_id: UUID) -> None:
    if visite_ruche_id is None:
        return

    visite = db.get(models.VisiteRuche, visite_ruche_id)
    if visite is None or visite.ruche_id != ruche_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visite ruche introuvable")

    get_owned_ruche(db, visite.ruche_id, user_id)


@router.get("", response_model=list[schemas.RecolteResponse])
def list_recoltes(
    ruche_id: UUID | None = None,
    year: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Recolte).join(models.Ruche, models.Recolte.ruche_id == models.Ruche.id)
    query = query.filter(models.Ruche.user_id == current_user.id)
    if ruche_id is not None:
        get_owned_ruche(db, ruche_id, current_user.id)
        query = query.filter(models.Recolte.ruche_id == ruche_id)
    query = _apply_recolte_date_filters(query, year, start_date, end_date)
    return query.order_by(models.Recolte.date_recolte.desc()).all()


@router.post("", response_model=schemas.RecolteResponse, status_code=status.HTTP_201_CREATED)
def create_recolte(
    payload: schemas.RecolteCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_ruche(db, payload.ruche_id, current_user.id)
    _validate_owned_visite_ruche(db, payload.visite_ruche_id, current_user.id, payload.ruche_id)

    recolte = models.Recolte(**payload.model_dump())
    db.add(recolte)
    db.commit()
    db.refresh(recolte)
    return recolte


def _get_stats_by_ruche_query(db: Session, user_id: UUID, year: int | None, start_date: date | None, end_date: date | None):
    query = (
        db.query(
            models.Ruche.id.label("ruche_id"),
            models.Ruche.identifiant_personnalise.label("identifiant_personnalise"),
            func.count(models.Recolte.id).label("total_recoltes"),
            func.coalesce(func.sum(models.Recolte.poids_miel_kg), 0).label("poids_total_kg"),
            func.coalesce(func.avg(models.Recolte.poids_miel_kg), 0).label("poids_moyen_kg"),
        )
        .join(models.Recolte, models.Recolte.ruche_id == models.Ruche.id)
        .filter(models.Ruche.user_id == user_id)
        .group_by(models.Ruche.id, models.Ruche.identifiant_personnalise)
    )
    query = _apply_recolte_date_filters(query, year, start_date, end_date)
    return query.order_by(func.coalesce(func.sum(models.Recolte.poids_miel_kg), 0).desc(), models.Ruche.identifiant_personnalise.asc())


@router.get("/stats/par-ruche", response_model=list[schemas.RecolteStatsByRuche])
def get_recolte_stats_by_ruche(
    year: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = _get_stats_by_ruche_query(db, current_user.id, year, start_date, end_date).all()
    return [
        schemas.RecolteStatsByRuche(
            ruche_id=row.ruche_id,
            identifiant_personnalise=row.identifiant_personnalise,
            total_recoltes=row.total_recoltes,
            poids_total_kg=float(row.poids_total_kg),
            poids_moyen_kg=float(row.poids_moyen_kg),
        )
        for row in rows
    ]


def _get_stats_by_rucher_query(db: Session, user_id: UUID, year: int | None, start_date: date | None, end_date: date | None):
    query = (
        db.query(
            models.Rucher.id.label("rucher_id"),
            models.Rucher.nom.label("nom_rucher"),
            func.count(models.Recolte.id).label("total_recoltes"),
            func.coalesce(func.sum(models.Recolte.poids_miel_kg), 0).label("poids_total_kg"),
            func.coalesce(func.avg(models.Recolte.poids_miel_kg), 0).label("poids_moyen_kg"),
        )
        .join(models.Ruche, models.Ruche.rucher_id == models.Rucher.id)
        .join(models.Recolte, models.Recolte.ruche_id == models.Ruche.id)
        .filter(models.Rucher.user_id == user_id)
        .group_by(models.Rucher.id, models.Rucher.nom)
    )
    query = _apply_recolte_date_filters(query, year, start_date, end_date)
    return query.order_by(func.coalesce(func.sum(models.Recolte.poids_miel_kg), 0).desc(), models.Rucher.nom.asc())


@router.get("/stats/par-rucher", response_model=list[schemas.RecolteStatsByRucher])
def get_recolte_stats_by_rucher(
    year: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = _get_stats_by_rucher_query(db, current_user.id, year, start_date, end_date).all()
    return [
        schemas.RecolteStatsByRucher(
            rucher_id=row.rucher_id,
            nom_rucher=row.nom_rucher,
            total_recoltes=row.total_recoltes,
            poids_total_kg=float(row.poids_total_kg),
            poids_moyen_kg=float(row.poids_moyen_kg),
        )
        for row in rows
    ]


@router.get("/stats/periode-glissante", response_model=schemas.RecolteStatsRollingPeriod)
def get_recolte_stats_rolling_period(
    days: int = 30,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if days <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Le nombre de jours doit etre positif")

    start_dt = datetime.now() - timedelta(days=days)
    row = (
        db.query(
            func.count(models.Recolte.id).label("total_recoltes"),
            func.coalesce(func.sum(models.Recolte.poids_miel_kg), 0).label("poids_total_kg"),
            func.coalesce(func.avg(models.Recolte.poids_miel_kg), 0).label("poids_moyen_kg"),
        )
        .join(models.Ruche, models.Recolte.ruche_id == models.Ruche.id)
        .filter(models.Ruche.user_id == current_user.id, models.Recolte.date_recolte >= start_dt)
        .one()
    )
    return schemas.RecolteStatsRollingPeriod(
        days=days,
        total_recoltes=row.total_recoltes,
        poids_total_kg=float(row.poids_total_kg),
        poids_moyen_kg=float(row.poids_moyen_kg),
    )


@router.get("/stats/par-annee", response_model=list[schemas.RecolteStatsByYear])
def get_recolte_stats_by_year(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(
            extract("year", models.Recolte.date_recolte).label("annee"),
            func.count(models.Recolte.id).label("total_recoltes"),
            func.coalesce(func.sum(models.Recolte.poids_miel_kg), 0).label("poids_total_kg"),
            func.coalesce(func.avg(models.Recolte.poids_miel_kg), 0).label("poids_moyen_kg"),
        )
        .join(models.Ruche, models.Recolte.ruche_id == models.Ruche.id)
        .filter(models.Ruche.user_id == current_user.id)
        .group_by(extract("year", models.Recolte.date_recolte))
        .order_by(extract("year", models.Recolte.date_recolte).desc())
        .all()
    )
    return [
        schemas.RecolteStatsByYear(
            annee=int(row.annee),
            total_recoltes=row.total_recoltes,
            poids_total_kg=float(row.poids_total_kg),
            poids_moyen_kg=float(row.poids_moyen_kg),
        )
        for row in rows
    ]


@router.get("/stats/par-saison", response_model=list[schemas.RecolteStatsSeason])
def get_recolte_stats_by_season(
    season_start_month: int = 3,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if season_start_month < 1 or season_start_month > 12:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Le mois de debut de saison doit etre compris entre 1 et 12")

    recoltes = (
        db.query(models.Recolte)
        .join(models.Ruche, models.Recolte.ruche_id == models.Ruche.id)
        .filter(models.Ruche.user_id == current_user.id)
        .order_by(models.Recolte.date_recolte.desc())
        .all()
    )

    seasons: dict[tuple[int, int], dict[str, float | int | str]] = {}
    for recolte in recoltes:
        recolte_date = recolte.date_recolte.date()
        season_year = recolte_date.year if recolte_date.month >= season_start_month else recolte_date.year - 1
        key = (season_year, season_start_month)
        if key not in seasons:
            seasons[key] = {
                "saison_label": f"Saison {season_year}",
                "season_start_year": season_year,
                "season_start_month": season_start_month,
                "total_recoltes": 0,
                "poids_total_kg": 0.0,
            }
        seasons[key]["total_recoltes"] += 1
        seasons[key]["poids_total_kg"] += float(recolte.poids_miel_kg)

    results = []
    for key in sorted(seasons.keys(), reverse=True):
        item = seasons[key]
        total_recoltes = int(item["total_recoltes"])
        poids_total_kg = float(item["poids_total_kg"])
        results.append(
            schemas.RecolteStatsSeason(
                saison_label=str(item["saison_label"]),
                season_start_year=int(item["season_start_year"]),
                season_start_month=int(item["season_start_month"]),
                total_recoltes=total_recoltes,
                poids_total_kg=poids_total_kg,
                poids_moyen_kg=poids_total_kg / total_recoltes if total_recoltes else 0.0,
            )
        )
    return results


@router.get("/{recolte_id}", response_model=schemas.RecolteResponse)
def get_recolte(
    recolte_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recolte = db.get(models.Recolte, recolte_id)
    if recolte is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recolte introuvable")
    get_owned_ruche(db, recolte.ruche_id, current_user.id)
    return recolte


@router.put("/{recolte_id}", response_model=schemas.RecolteResponse)
def update_recolte(
    recolte_id: UUID,
    payload: schemas.RecolteUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recolte = db.get(models.Recolte, recolte_id)
    if recolte is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recolte introuvable")

    get_owned_ruche(db, recolte.ruche_id, current_user.id)
    get_owned_ruche(db, payload.ruche_id, current_user.id)
    _validate_owned_visite_ruche(db, payload.visite_ruche_id, current_user.id, payload.ruche_id)

    for field, value in payload.model_dump().items():
        setattr(recolte, field, value)

    db.commit()
    db.refresh(recolte)
    return recolte


@router.delete("/{recolte_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recolte(
    recolte_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recolte = db.get(models.Recolte, recolte_id)
    if recolte is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recolte introuvable")

    get_owned_ruche(db, recolte.ruche_id, current_user.id)

    db.delete(recolte)
    db.commit()
    return None