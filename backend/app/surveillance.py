"""Ruches a surveiller : criteres valides avec le concepteur (D1, 2026-10-03).

Le tag `a surveiller` correspondant est derive : calcule a la lecture, il
apparait et disparait seul selon l'etat de la ruche, sans toucher a un tag
`a surveiller` pose a la main.
"""
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app import models

QUEEN_AGE_YEARS = 2
LOW_NOTE = 2
LOW_BROOD_RATIO = 0.3
SEASON_MONTHS = range(4, 10)  # avril a septembre
MAX_DAYS_WITHOUT_VISIT_SEASON = 21
MAX_DAYS_WITHOUT_VISIT_OFF_SEASON = 60
WATCH_TAG = "a surveiller"


def _as_date(value) -> date | None:
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


def watch_reasons(db: Session, hives: list[models.Ruche], now: datetime | None = None) -> dict[UUID, list[str]]:
    """Motifs de surveillance des ruches en rucher, en trois requetes au total."""
    now = now or datetime.now(timezone.utc)
    today = now.date()
    in_season = today.month in SEASON_MONTHS
    field_hives = [hive for hive in hives if not hive.is_at_atelier and hive.rucher_id is not None and hive.archived_at is None]
    hive_ids = [hive.id for hive in field_hives]
    if not hive_ids:
        return {}

    last_visits = {
        visit.ruche_id: visit
        for visit in (
            db.query(models.VisiteRuche)
            .filter(models.VisiteRuche.ruche_id.in_(hive_ids))
            .order_by(models.VisiteRuche.ruche_id, models.VisiteRuche.date_visite.desc())
            .distinct(models.VisiteRuche.ruche_id)
            .all()
        )
    }
    queens = {
        queen.ruche_id: queen
        for queen in db.query(models.Reine).filter(models.Reine.ruche_id.in_(hive_ids), models.Reine.statut == "active").all()
    }
    status_tags: dict[str, set[UUID]] = {"orpheline": set(), "colonie morte": set()}
    for tag in db.query(models.RucheTag).filter(models.RucheTag.ruche_id.in_(hive_ids), models.RucheTag.libelle.in_(status_tags)).all():
        if tag.expires_at is None or tag.expires_at > now:
            status_tags[tag.libelle].add(tag.ruche_id)
    orphans = status_tags["orpheline"]
    # Une colonie morte ne porte plus d'autre tag : elle sort de la surveillance.
    dead = status_tags["colonie morte"]

    reasons: dict[UUID, list[str]] = {}
    for hive in field_hives:
        if hive.id in dead:
            continue
        motifs: list[str] = []
        queen = queens.get(hive.id)
        if queen is not None:
            age = (now - queen.date_mise_en_place).days / 365.25
            if age >= QUEEN_AGE_YEARS:
                motifs.append(f"Reine de {age:.1f} an(s)")
        visit = last_visits.get(hive.id)
        if visit is not None:
            if visit.note_ruche is not None and visit.note_ruche <= LOW_NOTE:
                motifs.append(f"Note faible ({visit.note_ruche}/5)")
            if visit.presence_ponte is False:
                motifs.append("Pas de ponte a la derniere visite")
            elif visit.reine_vue is False:
                motifs.append("Reine non vue a la derniere visite")
            frames = visit.nombre_cadres_total or hive.nombre_cadres
            if in_season and frames and visit.nombre_cadres_couvain is not None:
                ratio = visit.nombre_cadres_couvain / frames
                if ratio < LOW_BROOD_RATIO:
                    motifs.append(f"Couvain faible ({round(ratio * 100)} %)")
        reference_date = _as_date(visit.date_visite) if visit is not None else _as_date(hive.created_at)
        max_days = MAX_DAYS_WITHOUT_VISIT_SEASON if in_season else MAX_DAYS_WITHOUT_VISIT_OFF_SEASON
        if reference_date is not None and (today - reference_date).days > max_days:
            motifs.append(f"Pas de visite depuis {(today - reference_date).days} jours")
        if hive.id in orphans:
            motifs.append("Tag orpheline")
        if motifs:
            reasons[hive.id] = motifs
    return reasons
