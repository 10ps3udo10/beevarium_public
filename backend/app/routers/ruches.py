from datetime import date, datetime, timedelta, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.database import get_db
from app.materiel_flux import default_frame_count, hive_elements, return_to_stock, take_from_stock
from app.ownership import get_owned_ruche
from app.surveillance import WATCH_TAG, watch_reasons
from app.security import get_current_user


router = APIRouter(prefix="/ruches", tags=["ruches"])

EVENT_TAG_TTL_DAYS = 30
EVENT_TAGS = {"candi pose", "sirop donne", "traitement varroa", "division prevue", "essaim recent"}
DEAD_COLONY_TAG = "colonie morte"
TYPE_TAGS = {"production", "essaim", "essaim recent", "starter", "finisseur", "nuclei", "banque a males", "ruche pedagogique", "ruche piege"}
PRIMARY_STATUS_TAGS = {"active", "bourdonneuse", "orpheline", "suspicion maladie", DEAD_COLONY_TAG}


def _validate_rucher_owner(db: Session, user_id: UUID, rucher_id: UUID | None) -> None:
    if rucher_id is None:
        return

    rucher = db.get(models.Rucher, rucher_id)
    if rucher is None or rucher.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rucher introuvable pour cet utilisateur")


def _validate_atelier_owner(db: Session, user_id: UUID, atelier_id: UUID | None) -> None:
    if atelier_id is None:
        return
    atelier = db.get(models.Atelier, atelier_id)
    if atelier is None or atelier.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atelier introuvable pour cet utilisateur")


def _validate_ruche_references_owner(
    db: Session,
    user_id: UUID,
    ref_type_ruche_id: UUID | None,
    ref_statut_ruche_id: UUID | None,
) -> None:
    if ref_type_ruche_id is not None:
        type_option = (
            db.query(models.RefTypeRuche)
            .filter(
                models.RefTypeRuche.id == ref_type_ruche_id,
                or_(models.RefTypeRuche.is_system.is_(True), models.RefTypeRuche.user_id == user_id),
            )
            .first()
        )
        if type_option is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type de ruche introuvable")

    if ref_statut_ruche_id is not None:
        statut_option = (
            db.query(models.RefStatutRuche)
            .filter(
                models.RefStatutRuche.id == ref_statut_ruche_id,
                or_(models.RefStatutRuche.is_system.is_(True), models.RefStatutRuche.user_id == user_id),
            )
            .first()
        )
        if statut_option is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statut de ruche introuvable")


def _validate_unique_identifier(
    db: Session,
    user_id: UUID,
    identifier: str,
    current_ruche_id: UUID | None = None,
) -> str:
    normalized_identifier = identifier.strip()
    query = db.query(models.Ruche).filter(
        models.Ruche.user_id == user_id,
        models.Ruche.identifiant_personnalise.ilike(normalized_identifier),
        models.Ruche.archived_at.is_(None),
    )
    if current_ruche_id is not None:
        query = query.filter(models.Ruche.id != current_ruche_id)
    if query.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet identifiant de ruche est deja utilise.")
    return normalized_identifier



QUEEN_SUMMARY_FIELDS = ("reine_race", "reine_provenance", "reine_annee_marquage")


def _queen_placed_at(ruche: models.Ruche, placed_on: date | None) -> datetime:
    """Jour J de mise en place : date saisie, sinon deduite de l'annee.

    Pour l'annee en cours, le jour de saisie ; pour une annee passee sans
    date, le 1er juillet, milieu de saison, plutot que le 1er janvier qui
    vieillissait la reine jusqu'a six mois de trop.
    """
    if placed_on is not None:
        return datetime(placed_on.year, placed_on.month, placed_on.day, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if not ruche.reine_annee_marquage or ruche.reine_annee_marquage >= now.year:
        return now
    return datetime(ruche.reine_annee_marquage, 7, 1, tzinfo=timezone.utc)


def _sync_active_queen_from_hive(db: Session, ruche: models.Ruche, placed_on: date | None = None) -> None:
    """Repercute le resume reine de la fiche ruche sur la reine active.

    La table `reines` est la source de verite (historique, age, statistiques) ;
    la fiche ruche en garde un resume. Le remplacement de reine met a jour le
    resume ; ici, la saisie du resume met a jour ou cree la reine active.
    """
    if placed_on is not None:
        ruche.reine_annee_marquage = placed_on.year
    if all(getattr(ruche, field) is None for field in QUEEN_SUMMARY_FIELDS):
        return
    active = (
        db.query(models.Reine)
        .filter(models.Reine.ruche_id == ruche.id, models.Reine.statut == "active")
        .first()
    )
    if active is None:
        db.add(models.Reine(
            ruche_id=ruche.id,
            date_mise_en_place=_queen_placed_at(ruche, placed_on),
            origine="inconnue",
            race=ruche.reine_race,
            provenance=ruche.reine_provenance,
            statut="active",
        ))
        return
    active.race = ruche.reine_race
    active.provenance = ruche.reine_provenance
    if placed_on is not None:
        active.date_mise_en_place = _queen_placed_at(ruche, placed_on)
    elif ruche.reine_annee_marquage and active.date_mise_en_place.year != ruche.reine_annee_marquage:
        active.date_mise_en_place = _queen_placed_at(ruche, None)


def _default_active_status_id(db: Session, user_id: UUID) -> UUID | None:
    status_option = (
        db.query(models.RefStatutRuche)
        .filter(
            models.RefStatutRuche.libelle.ilike("active"),
            or_(models.RefStatutRuche.is_system.is_(True), models.RefStatutRuche.user_id == user_id),
        )
        .order_by(models.RefStatutRuche.is_system.desc())
        .first()
    )
    return status_option.id if status_option is not None else None


def _reference_id_by_label(db: Session, model, user_id: UUID, label: str) -> UUID | None:
    option = (
        db.query(model)
        .filter(
            model.libelle.ilike(label),
            or_(model.is_system.is_(True), model.user_id == user_id),
        )
        .order_by(model.is_system.desc())
        .first()
    )
    return option.id if option is not None else None


def _hausse_count_for_tag(label: str) -> int | None:
    normalized = label.lower()
    if normalized == "hausse posee":
        return 1
    parts = normalized.split()
    if len(parts) >= 3 and parts[1].startswith("hausse") and parts[2] == "posees":
        try:
            count = int(parts[0])
        except ValueError:
            return None
        if 1 <= count <= 5:
            return count
    return None


def _active_manual_tags_query(db: Session, ruche: models.Ruche):
    return (
        db.query(models.RucheTag)
        .filter(models.RucheTag.ruche_id == ruche.id, models.RucheTag.user_id == ruche.user_id)
        .filter(_active_tag_filter())
    )


def _delete_tag_with_effects(db: Session, ruche: models.Ruche, tag: models.RucheTag) -> None:
    _reverse_tag_effect(db, ruche, tag.libelle)
    db.delete(tag)


def _end_active_queen_for_dead_colony(db: Session, ruche: models.Ruche) -> None:
    active_reine = db.query(models.Reine).filter(models.Reine.ruche_id == ruche.id, models.Reine.statut == "active").first()
    if active_reine is None:
        return
    active_reine.statut = "terminee"
    active_reine.date_fin = datetime.now(timezone.utc)
    active_reine.motif_fin = "colonie_morte"


def _remove_dead_colony_tag(db: Session, ruche: models.Ruche) -> None:
    tags = _active_manual_tags_query(db, ruche).filter(func.lower(models.RucheTag.libelle) == DEAD_COLONY_TAG).all()
    for tag in tags:
        db.delete(tag)


def _remove_contradictory_tags_for_new_tag(db: Session, ruche: models.Ruche, label: str) -> None:
    normalized = label.lower()
    active_tags = _active_manual_tags_query(db, ruche).all()
    has_dead_colony = any(tag.libelle.lower() == DEAD_COLONY_TAG for tag in active_tags)
    if has_dead_colony and normalized != DEAD_COLONY_TAG:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Deplacer la ruche a l'Atelier avant d'ajouter d'autres tags")

    for tag in active_tags:
        tag_label = tag.libelle.lower()
        should_remove = normalized == DEAD_COLONY_TAG
        should_remove = should_remove or (normalized in TYPE_TAGS and tag_label in TYPE_TAGS and tag_label != normalized)
        should_remove = should_remove or (normalized in PRIMARY_STATUS_TAGS and tag_label in PRIMARY_STATUS_TAGS and tag_label != normalized)
        if should_remove:
            _delete_tag_with_effects(db, ruche, tag)


def _apply_tag_effect(db: Session, ruche: models.Ruche, label: str) -> None:
    normalized = label.lower()
    if normalized == DEAD_COLONY_TAG:
        _end_active_queen_for_dead_colony(db, ruche)
    type_by_tag = {
        "production": "Production",
        "essaim recent": "Essaim",
        "essaim": "Essaim",
        "starter": "Starter",
        "finisseur": "Finisseur",
        "nuclei": "Nuclei",
        "banque a males": "Banque a males",
        "ruche pedagogique": "Ruche pedagogique",
        "ruche piege": "Piege a essaim",
    }
    if normalized in type_by_tag:
        type_id = _reference_id_by_label(db, models.RefTypeRuche, ruche.user_id, type_by_tag[normalized])
        if type_id is not None:
            ruche.ref_type_ruche_id = type_id
    status_by_tag = {
        "active": "Active",
        "bourdonneuse": "Bourdonneuse",
        "orpheline": "Orpheline",
        "quarantaine": "En quarantaine",
        "suspicion maladie": "Suspecte maladie",
        "colonie morte": "Morte",
    }
    if normalized in status_by_tag:
        status_id = _reference_id_by_label(db, models.RefStatutRuche, ruche.user_id, status_by_tag[normalized])
        if status_id is not None:
            ruche.ref_statut_ruche_id = status_id
    equipment_by_tag = {
        "nourrisseur present": "has_nourrisseur",
        "grille a reine": "has_grille_a_reine",
    }
    if normalized in equipment_by_tag:
        setattr(ruche, equipment_by_tag[normalized], True)
    hausse_count = _hausse_count_for_tag(label)
    if hausse_count is not None:
        previous_tags = (
            db.query(models.RucheTag)
            .filter(models.RucheTag.ruche_id == ruche.id, models.RucheTag.user_id == ruche.user_id)
            .all()
        )
        previous_count = sum(_hausse_count_for_tag(tag.libelle) or 0 for tag in previous_tags)
        for tag in previous_tags:
            if _hausse_count_for_tag(tag.libelle) is not None and tag.libelle.lower() != normalized:
                db.delete(tag)
        ruche.has_hausse = True
        delta = hausse_count - previous_count
        if delta:
            db.add(models.MouvementHausse(ruche_id=ruche.id, quantite_delta=delta, note=f"Tag {label}"))


def _reverse_tag_effect(db: Session, ruche: models.Ruche, label: str) -> None:
    hausse_count = _hausse_count_for_tag(label)
    if hausse_count is not None:
        db.add(models.MouvementHausse(ruche_id=ruche.id, quantite_delta=-hausse_count, note=f"Retrait tag {label}"))


def _active_tag_filter():
    now = datetime.now(timezone.utc)
    return or_(models.RucheTag.expires_at.is_(None), models.RucheTag.expires_at > now)


def _expires_at_for_tag(label: str) -> datetime | None:
    if label.lower() in EVENT_TAGS:
        return datetime.now(timezone.utc) + timedelta(days=EVENT_TAG_TTL_DAYS)
    return None


def _derived_tag(ruche: models.Ruche, label: str) -> schemas.RucheTagResponse:
    return schemas.RucheTagResponse(
        id=uuid5(NAMESPACE_URL, f"beevarium:ruche:{ruche.id}:tag:{label}"),
        ruche_id=ruche.id,
        libelle=label,
        source="derive",
        created_at=ruche.created_at,
    )


def _watch_tag_needed(ruche: models.Ruche, reasons: dict[UUID, list[str]], manual_labels: set[str]) -> bool:
    return ruche.id in reasons and WATCH_TAG not in manual_labels


def _derived_tags_for_ruche(db: Session, ruche: models.Ruche, manual_labels: set[str]) -> list[schemas.RucheTagResponse]:
    if ruche.is_at_atelier:
        return [_derived_tag(ruche, "atelier")]
    if _watch_tag_needed(ruche, watch_reasons(db, [ruche]), manual_labels):
        return [_derived_tag(ruche, WATCH_TAG)]
    return []


@router.get("", response_model=list[schemas.RucheResponse])
def list_ruches(
    rucher_id: UUID | None = None,
    atelier_only: bool = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if rucher_id is not None:
        _validate_rucher_owner(db, current_user.id, rucher_id)

    query = (
        db.query(models.Ruche)
        .options(selectinload(models.Ruche.tags), selectinload(models.Ruche.reines))
        .filter(models.Ruche.user_id == current_user.id, models.Ruche.archived_at.is_(None))
    )
    if rucher_id is not None:
        query = query.filter(models.Ruche.rucher_id == rucher_id)
    if atelier_only:
        query = query.filter(models.Ruche.is_at_atelier.is_(True))
    hives = query.order_by(models.Ruche.created_at.desc()).all()
    # Tag derive `a surveiller` calcule pour toute la liste en trois requetes.
    reasons = watch_reasons(db, hives)
    responses = []
    for hive in hives:
        response = schemas.RucheResponse.model_validate(hive)
        if _watch_tag_needed(hive, reasons, {tag.libelle.lower() for tag in hive.tags}):
            response.tags.append(_derived_tag(hive, WATCH_TAG))
        responses.append(response)
    return responses


@router.post("", response_model=schemas.RucheResponse, status_code=status.HTTP_201_CREATED)
def create_ruche(
    payload: schemas.RucheCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_rucher_owner(db, current_user.id, payload.rucher_id)
    _validate_atelier_owner(db, current_user.id, payload.atelier_id)
    _validate_ruche_references_owner(db, current_user.id, payload.ref_type_ruche_id, payload.ref_statut_ruche_id)
    identifier = _validate_unique_identifier(db, current_user.id, payload.identifiant_personnalise)

    ruche_data = payload.model_dump(exclude={"origine_materiel", "elements_stock", "reine_date_mise_en_place"})
    ruche_data["identifiant_personnalise"] = identifier
    if payload.is_at_atelier:
        ruche_data["rucher_id"] = None
        if payload.atelier_id is None:
            atelier = db.query(models.Atelier).filter(models.Atelier.user_id == current_user.id).first()
            if atelier is None:
                atelier = models.Atelier(user_id=current_user.id, nom="Atelier")
                db.add(atelier)
                db.flush()
            ruche_data["atelier_id"] = atelier.id
    elif payload.rucher_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Renseigner un rucher ou cocher atelier")
    elif payload.ref_statut_ruche_id is None:
        ruche_data["ref_statut_ruche_id"] = _default_active_status_id(db, current_user.id)

    ruche_data["user_id"] = current_user.id

    ruche = models.Ruche(**ruche_data)
    db.add(ruche)
    db.flush()
    if payload.origine_materiel == "stock":
        # Ruche montee avec du materiel deja range a l'Atelier.
        elements = hive_elements(db, ruche, include_hausses=False)
        if payload.elements_stock is not None:
            elements = {key: quantity for key, quantity in elements.items() if key in payload.elements_stock}
        take_from_stock(db, current_user.id, ruche.format_ruche, elements)
    _sync_active_queen_from_hive(db, ruche, payload.reine_date_mise_en_place)
    db.commit()
    db.refresh(ruche)
    return ruche


@router.get("/{ruche_id}", response_model=schemas.RucheResponse)
def get_ruche(ruche_id: UUID, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ruche = db.query(models.Ruche).options(selectinload(models.Ruche.tags)).filter(models.Ruche.id == ruche_id).first()
    if ruche is None or ruche.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ruche introuvable")
    return ruche


@router.get("/{ruche_id}/tags", response_model=list[schemas.RucheTagResponse])
def list_ruche_tags(ruche_id: UUID, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ruche = get_owned_ruche(db, ruche_id, current_user.id)
    manual_tags = (
        db.query(models.RucheTag)
        .filter(models.RucheTag.ruche_id == ruche_id, models.RucheTag.user_id == current_user.id)
        .filter(_active_tag_filter())
        .order_by(models.RucheTag.libelle.asc())
        .all()
    )
    manual_labels = {tag.libelle.lower() for tag in manual_tags}
    return [schemas.RucheTagResponse.model_validate(tag) for tag in manual_tags] + _derived_tags_for_ruche(db, ruche, manual_labels)


def add_manual_tag(db: Session, ruche: models.Ruche, user_id: UUID, raw_label: str) -> models.RucheTag:
    """Pose un tag manuel avec ses effets metier, sans commit.

    Partage par l'ajout direct depuis la fiche ruche et par les tags choisis
    pendant une visite hors ligne, envoyes avec la visite.
    """
    label = " ".join(raw_label.strip().split())
    expired_duplicate = (
        db.query(models.RucheTag)
        .filter(
            models.RucheTag.ruche_id == ruche.id,
            models.RucheTag.user_id == user_id,
            func.lower(models.RucheTag.libelle) == label.lower(),
            models.RucheTag.expires_at.is_not(None),
            models.RucheTag.expires_at <= datetime.now(timezone.utc),
        )
        .first()
    )
    if expired_duplicate is not None:
        db.delete(expired_duplicate)
        db.flush()
    duplicate = (
        db.query(models.RucheTag)
        .filter(
            models.RucheTag.ruche_id == ruche.id,
            models.RucheTag.user_id == user_id,
            func.lower(models.RucheTag.libelle) == label.lower(),
            _active_tag_filter(),
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce tag existe deja pour cette ruche")
    _remove_contradictory_tags_for_new_tag(db, ruche, label)
    _apply_tag_effect(db, ruche, label)
    tag = models.RucheTag(user_id=user_id, ruche_id=ruche.id, libelle=label, source="manuel", expires_at=_expires_at_for_tag(label))
    db.add(tag)
    db.flush()
    return tag


@router.post("/{ruche_id}/tags", response_model=schemas.RucheTagResponse, status_code=status.HTTP_201_CREATED)
def create_ruche_tag(
    ruche_id: UUID,
    payload: schemas.RucheTagCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ruche = get_owned_ruche(db, ruche_id, current_user.id)
    tag = add_manual_tag(db, ruche, current_user.id, payload.libelle)
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{ruche_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ruche_tag(
    ruche_id: UUID,
    tag_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ruche = get_owned_ruche(db, ruche_id, current_user.id)
    tag = db.get(models.RucheTag, tag_id)
    if tag is None or tag.ruche_id != ruche_id or tag.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag introuvable")
    _reverse_tag_effect(db, ruche, tag.libelle)
    db.delete(tag)
    db.commit()
    return None


@router.put("/{ruche_id}", response_model=schemas.RucheResponse)
def update_ruche(
    ruche_id: UUID,
    payload: schemas.RucheUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ruche = get_owned_ruche(db, ruche_id, current_user.id)

    _validate_rucher_owner(db, current_user.id, payload.rucher_id)
    _validate_atelier_owner(db, current_user.id, payload.atelier_id)
    _validate_ruche_references_owner(db, current_user.id, payload.ref_type_ruche_id, payload.ref_statut_ruche_id)
    identifier = _validate_unique_identifier(db, current_user.id, payload.identifiant_personnalise, ruche.id)

    previous_has_hausse = ruche.has_hausse
    previous_queen_summary = tuple(getattr(ruche, field) for field in QUEEN_SUMMARY_FIELDS)
    data = payload.model_dump(exclude={"reine_date_mise_en_place"})
    data["identifiant_personnalise"] = identifier
    if payload.is_at_atelier:
        data["rucher_id"] = None
        if payload.atelier_id is None:
            atelier = db.query(models.Atelier).filter(models.Atelier.user_id == current_user.id).first()
            if atelier is None:
                atelier = models.Atelier(user_id=current_user.id, nom="Atelier")
                db.add(atelier)
                db.flush()
            data["atelier_id"] = atelier.id
    elif payload.rucher_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Renseigner un rucher ou cocher atelier")

    data["user_id"] = current_user.id

    for field, value in data.items():
        setattr(ruche, field, value)
    if previous_has_hausse != ruche.has_hausse:
        db.add(models.MouvementHausse(
            ruche_id=ruche.id,
            quantite_delta=1 if ruche.has_hausse else -1,
            note="Hausse ajoutee depuis la fiche ruche" if ruche.has_hausse else "Hausse retiree depuis la fiche ruche",
        ))
    # Seule une modification du resume reine touche la table `reines` : sinon
    # reenregistrer la fiche d'une colonie morte recreerait une reine active.
    placed_on = payload.reine_date_mise_en_place
    if placed_on is not None and placed_on == ruche.reine_date_mise_en_place:
        placed_on = None
    if placed_on is not None or tuple(getattr(ruche, field) for field in QUEEN_SUMMARY_FIELDS) != previous_queen_summary:
        _sync_active_queen_from_hive(db, ruche, placed_on)
    if ruche.is_at_atelier:
        _remove_dead_colony_tag(db, ruche)

    db.commit()
    db.refresh(ruche)
    return ruche


@router.post("/move", response_model=schemas.RucheMoveResponse)
def move_ruches(
    payload: schemas.RucheMoveRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.move_to_atelier and payload.target_rucher_id is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Choisir atelier ou rucher, pas les deux")
    if not payload.move_to_atelier and payload.target_rucher_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Rucher cible obligatoire hors atelier")

    target_rucher = None
    if payload.target_rucher_id is not None:
        target_rucher = db.get(models.Rucher, payload.target_rucher_id)
        if target_rucher is None or target_rucher.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rucher cible introuvable")

    atelier = None
    if payload.move_to_atelier:
        atelier = db.query(models.Atelier).filter(models.Atelier.user_id == current_user.id).first()
        if atelier is None:
            atelier = models.Atelier(user_id=current_user.id, nom="Atelier")
            db.add(atelier)
            db.flush()

    ruches = (
        db.query(models.Ruche)
        .filter(models.Ruche.user_id == current_user.id, models.Ruche.id.in_(payload.ruche_ids), models.Ruche.archived_at.is_(None))
        .all()
    )
    if len(ruches) != len(payload.ruche_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Une ou plusieurs ruches sont introuvables")

    for ruche in ruches:
        ruche.rucher_id = payload.target_rucher_id
        ruche.is_at_atelier = payload.move_to_atelier
        ruche.atelier_id = atelier.id if atelier is not None else None
        if payload.move_to_atelier:
            _remove_dead_colony_tag(db, ruche)

    db.commit()
    return schemas.RucheMoveResponse(
        moved_count=len(ruches),
        target_rucher_id=payload.target_rucher_id,
        move_to_atelier=payload.move_to_atelier,
    )


def _archive_hive(db: Session, ruche: models.Ruche, motif: str) -> None:
    """Sort une ruche du cheptel en gardant son historique."""
    now = datetime.now(timezone.utc)
    active_queen = (
        db.query(models.Reine)
        .filter(models.Reine.ruche_id == ruche.id, models.Reine.statut == "active")
        .first()
    )
    if active_queen is not None:
        active_queen.statut = "terminee"
        active_queen.date_fin = now
        active_queen.motif_fin = motif
    ruche.archived_at = now
    ruche.motif_archive = motif
    ruche.rucher_id = None
    ruche.is_at_atelier = True


@router.post("/demontage", response_model=schemas.RucheDemontageResponse)
def demonter_ruches(
    payload: schemas.RucheDemontageRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Demonte des ruches : leurs elements reviennent dans le stock range.

    La ruche est archivee (pas supprimee) : visites, recoltes et reines restent
    dans l'historique et les statistiques. La reine active est terminee.
    """
    ruches = (
        db.query(models.Ruche)
        .filter(models.Ruche.user_id == current_user.id, models.Ruche.id.in_(payload.ruche_ids), models.Ruche.archived_at.is_(None))
        .all()
    )
    if len(ruches) != len(set(payload.ruche_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Une ou plusieurs ruches sont introuvables")
    for ruche in ruches:
        elements = hive_elements(db, ruche)
        if payload.elements_stock is not None:
            elements = {key: quantity for key, quantity in elements.items() if key in payload.elements_stock}
        return_to_stock(db, current_user.id, ruche.format_ruche, elements)
        hausses = hive_elements(db, ruche).get("hausses", 0)
        if hausses:
            db.add(models.MouvementHausse(ruche_id=ruche.id, quantite_delta=-hausses, note="Hausses retirees au demontage"))
        _archive_hive(db, ruche, "demontee")
    db.commit()
    return schemas.RucheDemontageResponse(demontees=len(ruches))


SMALL_FORMATS = {"ruchette", "nucleus"}


def apply_transvasement(
    db: Session,
    ruche: models.Ruche,
    user_id: UUID,
    payload: schemas.TransvasementCreate,
    visite_id: UUID | None = None,
) -> tuple[models.RucheTransvasement, list[str]]:
    """Change le contenant d'une colonie sans changer la colonie.

    La ruche (colonie) garde son id, sa reine, ses visites et recoltes. L'ancien
    contenant revient dans le stock range ; le nouveau vient du stock, d'un
    achat ou d'une ruche preparee a l'Atelier (alors archivee). Sans commit.
    """
    if ruche.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ruche archivee")
    format_avant = ruche.format_ruche
    identifiant_avant = ruche.identifiant_personnalise
    old_frames = ruche.nombre_cadres if ruche.nombre_cadres is not None else default_frame_count(format_avant)

    # Ancien contenant : elements et cadres non transferes reviennent en stock.
    old_elements = hive_elements(db, ruche, include_frames=False, include_hausses=False)
    old_elements["cadres"] = max(old_frames - payload.cadres_transferes, 0)
    return_to_stock(db, user_id, format_avant, old_elements)

    format_apres = payload.format_apres
    source = None
    if payload.provenance == "ruche_atelier":
        if payload.ruche_atelier_id is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Choisir la ruche preparee a l'Atelier")
        source = get_owned_ruche(db, payload.ruche_atelier_id, user_id)
        if source.id == ruche.id or not source.is_at_atelier or source.archived_at is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La ruche preparee doit etre a l'Atelier")
        format_apres = source.format_ruche or format_apres
        for field in ("has_plancher", "has_corps", "has_toit", "has_partition", "has_grille_a_reine", "has_nourrisseur"):
            setattr(ruche, field, getattr(source, field))
        source_frames = source.nombre_cadres if source.nombre_cadres is not None else default_frame_count(source.format_ruche)
        if source_frames > payload.cadres_ajoutes:
            return_to_stock(db, user_id, format_apres, {"cadres": source_frames - payload.cadres_ajoutes})
        elif payload.cadres_ajoutes > source_frames:
            take_from_stock(db, user_id, format_apres, {"cadres": payload.cadres_ajoutes - source_frames})
        _archive_hive(db, source, "transvasement")
    else:
        chosen = set(payload.elements)
        field_by_element = {"plancher": "has_plancher", "corps": "has_corps", "toit": "has_toit", "partition": "has_partition", "grille": "has_grille_a_reine", "nourrisseur": "has_nourrisseur"}
        for element, field in field_by_element.items():
            setattr(ruche, field, element in chosen)
        if payload.provenance == "stock":
            needed = {element: 1 for element in chosen}
            needed["cadres"] = payload.cadres_ajoutes
            take_from_stock(db, user_id, format_apres, needed)

    if payload.nouvel_identifiant:
        ruche.identifiant_personnalise = _validate_unique_identifier(db, user_id, payload.nouvel_identifiant, ruche.id)
    ruche.format_ruche = format_apres
    ruche.nombre_cadres = payload.cadres_transferes + payload.cadres_ajoutes
    if payload.cadres_ajoutes and payload.annee_cire:
        # Cadres neufs : traces comme un ajout de cire gaufree pour l'age des cadres.
        action = (
            db.query(models.RefActionCadre)
            .filter(models.RefActionCadre.is_system.is_(True), func.lower(models.RefActionCadre.libelle) == "ajout cadre cire gaufree")
            .first()
        )
        if action is not None:
            db.add(models.GestionCadres(
                ruche_id=ruche.id,
                visite_ruche_id=visite_id,
                ref_action_cadre_id=action.id,
                quantite=payload.cadres_ajoutes,
                annee_cire=payload.annee_cire,
            ))

    transvasement = models.RucheTransvasement(
        user_id=user_id,
        ruche_id=ruche.id,
        visite_ruche_id=visite_id,
        format_avant=format_avant,
        format_apres=format_apres,
        provenance=payload.provenance,
        ruche_atelier_id=source.id if source is not None else None,
        cadres_transferes=payload.cadres_transferes,
        cadres_ajoutes=payload.cadres_ajoutes,
        identifiant_avant=identifiant_avant,
        identifiant_apres=ruche.identifiant_personnalise,
    )
    db.add(transvasement)
    db.flush()

    # Passage ruchette -> ruche : proposer le type production, jamais l'imposer.
    suggestions: list[str] = []
    if (format_avant or "").lower() in SMALL_FORMATS and (format_apres or "").lower() not in SMALL_FORMATS:
        active_labels = {tag.libelle.lower() for tag in ruche.tags}
        if "production" not in active_labels:
            suggestions.append("production")
    return transvasement, suggestions


@router.post("/{ruche_id}/transvasements", response_model=schemas.TransvasementResponse, status_code=status.HTTP_201_CREATED)
def create_transvasement(
    ruche_id: UUID,
    payload: schemas.TransvasementCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ruche = get_owned_ruche(db, ruche_id, current_user.id)
    transvasement, suggestions = apply_transvasement(db, ruche, current_user.id, payload)
    db.commit()
    db.refresh(transvasement)
    response = schemas.TransvasementResponse.model_validate(transvasement)
    response.tag_suggestions = suggestions
    return response


@router.get("/{ruche_id}/transvasements", response_model=list[schemas.TransvasementResponse])
def list_transvasements(ruche_id: UUID, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_owned_ruche(db, ruche_id, current_user.id)
    return (
        db.query(models.RucheTransvasement)
        .filter(models.RucheTransvasement.ruche_id == ruche_id)
        .order_by(models.RucheTransvasement.date_transvasement.desc())
        .all()
    )


@router.delete("/{ruche_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ruche(ruche_id: UUID, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ruche = get_owned_ruche(db, ruche_id, current_user.id)

    db.delete(ruche)
    db.commit()
    return None
