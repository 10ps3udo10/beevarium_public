from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.materiel_flux import FRAME_FORMAT_LABELS, default_frame_count, stock_format
from app.security import get_current_user


router = APIRouter(prefix="/materiel-atelier", tags=["materiel-atelier"])


AUTO_COUNTED_LABELS = {"cadre", "partition", "corps", "plancher", "couvre-cadre", "toit", "hausse", "grille a reine", "nourrisseur"}


def _normalize_materiel_label(label: str | None) -> str:
    return (label or "").strip().lower()


def _type_label(db: Session, ref_type_materiel_id: UUID | None) -> str:
    option = db.get(models.RefTypeMateriel, ref_type_materiel_id) if ref_type_materiel_id else None
    return _normalize_materiel_label(option.libelle if option else None)


def _find_stock_row(db: Session, user_id: UUID, type_id: UUID | None, format_materiel: str | None):
    """Ligne unique d'un couple type + format (index uq_materiel_atelier_type_format)."""
    return (
        db.query(models.MaterielAtelier)
        .filter(
            models.MaterielAtelier.user_id == user_id,
            models.MaterielAtelier.ref_type_materiel_id.is_(None) if type_id is None else models.MaterielAtelier.ref_type_materiel_id == type_id,
            models.MaterielAtelier.format_materiel.is_(None) if format_materiel is None else models.MaterielAtelier.format_materiel == format_materiel,
        )
        .first()
    )


def _validate_owned_materiel_type(db: Session, ref_type_materiel_id: UUID | None, user_id: UUID) -> None:
    if ref_type_materiel_id is None:
        return

    option = db.get(models.RefTypeMateriel, ref_type_materiel_id)
    if option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type de materiel introuvable")
    if option.is_system or option.user_id == user_id:
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type de materiel introuvable")


def _compute_quantite_en_service_calculee(
    db: Session,
    user_id: UUID,
    ref_type_materiel_id: UUID | None,
    format_materiel: str | None = None,
    at_atelier: bool = False,
) -> int:
    """Materiel porte par les ruches, par type et format.

    `at_atelier=False` : ruches en rucher (en service) ; `True` : ruches
    montees et rangees a l'Atelier. Les ruches archivees (demontees ou
    absorbees par un transvasement) ne portent plus de materiel.
    """
    if ref_type_materiel_id is None:
        return 0

    option = db.get(models.RefTypeMateriel, ref_type_materiel_id)
    if option is None:
        return 0

    normalized_label = _normalize_materiel_label(option.libelle)
    if normalized_label not in AUTO_COUNTED_LABELS:
        return 0

    def scoped_hives():
        # Restreint au format quand il est renseigne: un corps de ruchette ne
        # doit jamais compter pour une ruche de production.
        query = db.query(models.Ruche).filter(
            models.Ruche.user_id == user_id,
            models.Ruche.archived_at.is_(None),
        )
        if at_atelier:
            query = query.filter(models.Ruche.is_at_atelier.is_(True))
        else:
            query = query.filter(models.Ruche.is_at_atelier.is_(False), models.Ruche.rucher_id.is_not(None))
        if format_materiel:
            # Cadres et partitions Dadant servent aussi les ruchettes Dadant.
            hive_formats = {format_materiel}
            if normalized_label in FRAME_FORMAT_LABELS and format_materiel == "dadant":
                hive_formats.add("ruchette")
            query = query.filter(models.Ruche.format_ruche.in_(hive_formats))
        return query

    if normalized_label == "cadre":
        rows = scoped_hives().with_entities(models.Ruche.nombre_cadres, models.Ruche.format_ruche).all()
        return sum(frames if frames is not None else default_frame_count(format_ruche) for frames, format_ruche in rows)

    if normalized_label == "hausse":
        hive_ids = scoped_hives().with_entities(models.Ruche.id).subquery()
        value = (
            db.query(func.coalesce(func.sum(models.MouvementHausse.quantite_delta), 0))
            .filter(models.MouvementHausse.ruche_id.in_(hive_ids.select()))
            .scalar()
            or 0
        )
        return max(int(value), 0)

    equipment_field_by_label = {
        "corps": "has_corps",
        "plancher": "has_plancher",
        "couvre-cadre": "has_corps",
        "toit": "has_toit",
        "partition": "has_partition",
        "grille a reine": "has_grille_a_reine",
        "nourrisseur": "has_nourrisseur",
    }

    equipment_field = equipment_field_by_label.get(normalized_label)
    if equipment_field is not None:
        return int(scoped_hives().filter(getattr(models.Ruche, equipment_field).is_(True)).count())

    return int(scoped_hives().count())


def _to_materiel_response(db: Session, materiel: models.MaterielAtelier) -> schemas.MaterielAtelierResponse:
    quantite_calculee = _compute_quantite_en_service_calculee(
        db, materiel.user_id, materiel.ref_type_materiel_id, materiel.format_materiel
    )
    return schemas.MaterielAtelierResponse(
        id=materiel.id,
        user_id=materiel.user_id,
        ref_type_materiel_id=materiel.ref_type_materiel_id,
        modele=materiel.modele,
        # Sans le format, le client ne retrouvait pas la ligne a modifier et en
        # creait une nouvelle : un retrait devenait un ajout (retour beta).
        format_materiel=materiel.format_materiel,
        quantite_atelier=materiel.quantite_atelier,
        quantite_en_service=materiel.quantite_en_service,
        quantite_en_service_manuelle=materiel.quantite_en_service,
        quantite_en_service_calculee=quantite_calculee,
        quantite_en_service_totale=materiel.quantite_en_service + quantite_calculee,
    )


@router.get("", response_model=list[schemas.MaterielAtelierResponse])
def list_materiel_atelier(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    materiels = (
        db.query(models.MaterielAtelier)
        .filter(models.MaterielAtelier.user_id == current_user.id)
        .order_by(models.MaterielAtelier.modele.asc().nullslast(), models.MaterielAtelier.id.asc())
        .all()
    )
    return [_to_materiel_response(db, materiel) for materiel in materiels]


@router.get("/stats/stock-synthetique-par-type", response_model=list[schemas.MaterielStockSyntheseByType])
def get_stock_synthetique_par_type(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    type_rows = (
        db.query(models.RefTypeMateriel)
        .filter(
            (models.RefTypeMateriel.is_system.is_(True))
            | (models.RefTypeMateriel.user_id == current_user.id)
        )
        .order_by(models.RefTypeMateriel.is_system.desc(), models.RefTypeMateriel.libelle.asc())
        .all()
    )

    manual_rows = (
        db.query(
            models.MaterielAtelier.ref_type_materiel_id.label("type_id"),
            models.MaterielAtelier.format_materiel.label("format_materiel"),
            func.coalesce(func.sum(models.MaterielAtelier.quantite_atelier), 0).label("quantite_atelier_totale"),
            func.coalesce(func.sum(models.MaterielAtelier.quantite_en_service), 0).label("quantite_en_service_manuelle_totale"),
        )
        .filter(
            models.MaterielAtelier.user_id == current_user.id,
            models.MaterielAtelier.ref_type_materiel_id.is_not(None),
        )
        .group_by(models.MaterielAtelier.ref_type_materiel_id, models.MaterielAtelier.format_materiel)
        .all()
    )

    # Une ligne par couple (type, format): les stocks de formats differents ne
    # sont pas interchangeables et ne doivent jamais etre additionnes.
    manual_by_key = {(row.type_id, row.format_materiel): row for row in manual_rows}
    formats_by_type: dict[UUID, set[str | None]] = {}
    for type_id, format_materiel in manual_by_key:
        formats_by_type.setdefault(type_id, set()).add(format_materiel)

    hive_formats = {
        row[0]
        for row in (
            db.query(models.Ruche.format_ruche)
            .filter(
                models.Ruche.user_id == current_user.id,
                models.Ruche.archived_at.is_(None),
                models.Ruche.format_ruche.is_not(None),
            )
            .distinct()
            .all()
        )
        if row[0]
    }

    results: list[schemas.MaterielStockSyntheseByType] = []
    for type_row in type_rows:
        if _normalize_materiel_label(type_row.libelle) in AUTO_COUNTED_LABELS and hive_formats:
            formats_by_type.setdefault(type_row.id, set()).update(
                stock_format(type_row.libelle, hive_format) for hive_format in hive_formats
            )

        for format_materiel in sorted(
            formats_by_type.get(type_row.id, {None}), key=lambda value: (value is None, value or "")
        ):
            manual = manual_by_key.get((type_row.id, format_materiel))
            quantite_atelier_totale = int(manual.quantite_atelier_totale) if manual is not None else 0
            quantite_en_service_manuelle_totale = int(manual.quantite_en_service_manuelle_totale) if manual is not None else 0
            quantite_en_service_calculee = _compute_quantite_en_service_calculee(
                db, current_user.id, type_row.id, format_materiel
            )
            quantite_en_service_totale = quantite_en_service_manuelle_totale + quantite_en_service_calculee
            quantite_ruches_atelier = _compute_quantite_en_service_calculee(
                db, current_user.id, type_row.id, format_materiel, at_atelier=True
            )

            results.append(
                schemas.MaterielStockSyntheseByType(
                    ref_type_materiel_id=type_row.id,
                    libelle_type_materiel=type_row.libelle,
                    format_materiel=format_materiel,
                    quantite_atelier_totale=quantite_atelier_totale,
                    quantite_en_service_manuelle_totale=quantite_en_service_manuelle_totale,
                    quantite_en_service_calculee=quantite_en_service_calculee,
                    quantite_en_service_totale=quantite_en_service_totale,
                    quantite_ruches_atelier_calculee=quantite_ruches_atelier,
                    quantite_stock_totale=quantite_atelier_totale + quantite_ruches_atelier + quantite_en_service_totale,
                )
            )
    return results


@router.post("", response_model=schemas.MaterielAtelierResponse, status_code=status.HTTP_201_CREATED)
def create_materiel_atelier(
    payload: schemas.MaterielAtelierCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_owned_materiel_type(db, payload.ref_type_materiel_id, current_user.id)

    data = payload.model_dump()
    data["format_materiel"] = stock_format(_type_label(db, payload.ref_type_materiel_id), payload.format_materiel)
    # Une seule ligne par type et format : un ajout sur un couple existant
    # s'additionne au stock range au lieu de creer un doublon que l'edition
    # ne verrait pas (retour beta : un retrait devenait un ajout).
    materiel = _find_stock_row(db, current_user.id, payload.ref_type_materiel_id, data["format_materiel"])
    if materiel is None:
        materiel = models.MaterielAtelier(**data, user_id=current_user.id)
        db.add(materiel)
    else:
        materiel.quantite_atelier += payload.quantite_atelier
        materiel.quantite_en_service += payload.quantite_en_service
        if payload.modele and not materiel.modele:
            materiel.modele = payload.modele
    db.commit()
    db.refresh(materiel)
    return _to_materiel_response(db, materiel)


@router.get("/{materiel_id}", response_model=schemas.MaterielAtelierResponse)
def get_materiel_atelier(
    materiel_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    materiel = db.get(models.MaterielAtelier, materiel_id)
    if materiel is None or materiel.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Materiel introuvable")
    return _to_materiel_response(db, materiel)


@router.put("/{materiel_id}", response_model=schemas.MaterielAtelierResponse)
def update_materiel_atelier(
    materiel_id: UUID,
    payload: schemas.MaterielAtelierUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    materiel = db.get(models.MaterielAtelier, materiel_id)
    if materiel is None or materiel.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Materiel introuvable")

    _validate_owned_materiel_type(db, payload.ref_type_materiel_id, current_user.id)

    data = payload.model_dump(exclude={"quantite_en_service"})
    data["format_materiel"] = stock_format(_type_label(db, payload.ref_type_materiel_id), payload.format_materiel)
    other = _find_stock_row(db, current_user.id, payload.ref_type_materiel_id, data["format_materiel"])
    if other is not None and other.id != materiel.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce type et ce format ont deja une ligne de stock : modifiez-la directement.")
    for field, value in data.items():
        setattr(materiel, field, value)

    db.commit()
    db.refresh(materiel)
    return _to_materiel_response(db, materiel)


@router.delete("/{materiel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_materiel_atelier(
    materiel_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    materiel = db.get(models.MaterielAtelier, materiel_id)
    if materiel is None or materiel.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Materiel introuvable")

    db.delete(materiel)
    db.commit()
    return None