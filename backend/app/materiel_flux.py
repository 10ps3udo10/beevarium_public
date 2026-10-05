"""Mouvements de materiel entre le stock de l'Atelier et les ruches.

Le stock "range" (`materiel_atelier.quantite_atelier`) est saisi ; le materiel
porte par les ruches est calcule depuis leurs champs `has_*`, `nombre_cadres`,
`format_ruche` et les mouvements de hausses. Les flux ci-dessous font passer
des elements d'un cote a l'autre lors de la creation d'une ruche depuis le
stock, du demontage d'une ruche ou d'un transvasement.
"""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models

# Element de ruche -> libelle du type de materiel systeme.
ELEMENT_TYPES = {
    "plancher": "Plancher",
    "corps": "Corps",
    "couvre_cadre": "Couvre-cadre",
    "toit": "Toit",
    "partition": "Partition",
    "grille": "Grille a reine",
    "nourrisseur": "Nourrisseur",
    "cadres": "Cadre",
    "hausses": "Hausse",
}

ELEMENT_FIELDS = {
    "plancher": "has_plancher",
    "corps": "has_corps",
    "toit": "has_toit",
    "partition": "has_partition",
    "grille": "has_grille_a_reine",
    "nourrisseur": "has_nourrisseur",
}

ELEMENT_LABELS = {
    "plancher": "plancher",
    "corps": "corps",
    "couvre_cadre": "couvre-cadre",
    "toit": "toit",
    "partition": "partition",
    "grille": "grille a reine",
    "nourrisseur": "nourrisseur",
    "cadres": "cadre(s)",
    "hausses": "hausse(s)",
}


# Dadant, Langstroth et Warre sont des formats de cadre ; une ruchette est un
# corps plus etroit qui porte des cadres du meme format (Dadant en pratique).
# Cadres et partitions se rangent donc au format du cadre, jamais "ruchette".
FRAME_FORMAT_LABELS = {"cadre", "partition"}


def frame_format(format_ruche: str | None) -> str | None:
    return "dadant" if (format_ruche or "").strip().lower() == "ruchette" else format_ruche


def stock_format(type_label: str | None, format_materiel: str | None) -> str | None:
    """Format sous lequel un type de materiel est range dans le stock."""
    if (type_label or "").strip().lower() in FRAME_FORMAT_LABELS:
        return frame_format(format_materiel)
    return format_materiel


def default_frame_count(format_ruche: str | None) -> int:
    """Capacite par defaut d'un corps selon son format."""
    normalized = (format_ruche or "").strip().lower()
    if normalized in {"ruchette", "nucleus"}:
        return 6
    if normalized == "warre":
        return 8
    return 10


def hive_hausses(db: Session, ruche: models.Ruche) -> int:
    value = (
        db.query(func.coalesce(func.sum(models.MouvementHausse.quantite_delta), 0))
        .filter(models.MouvementHausse.ruche_id == ruche.id)
        .scalar()
    )
    return max(int(value or 0), 0)


def hive_elements(db: Session, ruche: models.Ruche, include_frames: bool = True, include_hausses: bool = True) -> dict[str, int]:
    """Elements physiques portes par une ruche, en quantites."""
    elements = {key: 1 for key, field in ELEMENT_FIELDS.items() if getattr(ruche, field)}
    if ruche.has_corps:
        elements["couvre_cadre"] = 1
    if include_frames:
        frames = ruche.nombre_cadres if ruche.nombre_cadres is not None else default_frame_count(ruche.format_ruche)
        if frames:
            elements["cadres"] = frames
    if include_hausses:
        hausses = hive_hausses(db, ruche)
        if hausses:
            elements["hausses"] = hausses
    return elements


def _material_type(db: Session, element: str) -> models.RefTypeMateriel:
    label = ELEMENT_TYPES[element]
    option = (
        db.query(models.RefTypeMateriel)
        .filter(models.RefTypeMateriel.is_system.is_(True), func.lower(models.RefTypeMateriel.libelle) == label.lower())
        .first()
    )
    if option is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Type de materiel systeme manquant : {label}")
    return option


def _stock_rows(db: Session, user_id: UUID, type_id: UUID, format_materiel: str | None):
    return (
        db.query(models.MaterielAtelier)
        .filter(
            models.MaterielAtelier.user_id == user_id,
            models.MaterielAtelier.ref_type_materiel_id == type_id,
            models.MaterielAtelier.format_materiel.is_(None) if format_materiel is None else models.MaterielAtelier.format_materiel == format_materiel,
        )
        .order_by(models.MaterielAtelier.quantite_atelier.desc())
        .with_for_update()
        .all()
    )


def take_from_stock(db: Session, user_id: UUID, format_materiel: str | None, elements: dict[str, int]) -> None:
    """Retire des elements du stock range ; refuse tout si un element manque."""
    missing: list[str] = []
    plan: list[tuple[list[models.MaterielAtelier], int]] = []
    for element, quantity in elements.items():
        if quantity <= 0:
            continue
        element_format = stock_format(ELEMENT_TYPES[element], format_materiel)
        rows = _stock_rows(db, user_id, _material_type(db, element).id, element_format)
        available = sum(row.quantite_atelier for row in rows)
        if available < quantity:
            missing.append(f"{ELEMENT_LABELS[element]} ({available}/{quantity})")
        plan.append((rows, quantity))
    if missing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stock atelier insuffisant ({format_materiel or 'format non renseigne'}) : {', '.join(missing)}",
        )
    for rows, quantity in plan:
        for row in rows:
            used = min(row.quantite_atelier, quantity)
            row.quantite_atelier -= used
            quantity -= used
            if quantity == 0:
                break


def return_to_stock(db: Session, user_id: UUID, format_materiel: str | None, elements: dict[str, int]) -> None:
    """Remet des elements dans le stock range, en creant la ligne si besoin."""
    for element, quantity in elements.items():
        if quantity <= 0:
            continue
        type_id = _material_type(db, element).id
        element_format = stock_format(ELEMENT_TYPES[element], format_materiel)
        rows = _stock_rows(db, user_id, type_id, element_format)
        if rows:
            rows[0].quantite_atelier += quantity
        else:
            db.add(models.MaterielAtelier(
                user_id=user_id,
                ref_type_materiel_id=type_id,
                format_materiel=element_format,
                quantite_atelier=quantity,
                quantite_en_service=0,
            ))
            db.flush()
