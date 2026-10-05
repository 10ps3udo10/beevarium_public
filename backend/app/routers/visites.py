from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.creation_rapide import validate_hive_type
from app.database import get_db
from app.ownership import get_owned_ruche
from app.routers.ruches import add_manual_tag, apply_transvasement
from app.security import get_current_user


router = APIRouter(prefix="/visites", tags=["visites"])


VALID_SOURCES_SAISIE = {"manuelle", "ia_vocale"}
VALID_STATUTS_VALIDATION = {"brouillon", "valide"}
VALID_TYPES_HISTORIQUE = {"visite", "recolte"}
EVENT_TAGS = {"candi pose", "sirop donne", "traitement varroa", "division prevue", "essaim recent"}


def _visit_tag_rules(
    reine_vue: bool | None,
    etat_couvain: str | None,
    nombre_cadres_couvain: int | None,
    reserves_nourriture: str | None,
) -> tuple[list[str], set[str]]:
    suggestions: list[str] = []
    removals: set[str] = set()

    def suggest(label: str) -> None:
        if label not in suggestions:
            suggestions.append(label)

    if reine_vue is False:
        suggest("reine non vue")
        if nombre_cadres_couvain == 0:
            suggest("orpheline")
            suggest("a surveiller")
    elif reine_vue is True:
        removals.update({"reine non vue", "orpheline"})

    if reserves_nourriture == "critique":
        suggest("reserves faibles")
        suggest("a nourrir")
    elif reserves_nourriture in {"correct", "abondant"}:
        removals.update({"reserves faibles", "a nourrir"})

    if etat_couvain == "faible":
        suggest("couvain faible")
    elif etat_couvain in {"normal", "excellent"}:
        removals.update({"couvain faible", "absence couvain"})

    if nombre_cadres_couvain == 0:
        suggest("absence couvain")
    elif nombre_cadres_couvain is not None and nombre_cadres_couvain > 0:
        removals.add("absence couvain")

    return suggestions, removals


def _apply_reversible_tag_removals(db: Session, ruche_id: UUID, user_id: UUID, labels: set[str]) -> None:
    if not labels:
        return
    normalized = {label.lower() for label in labels}
    tags = (
        db.query(models.RucheTag)
        .filter(models.RucheTag.ruche_id == ruche_id, models.RucheTag.user_id == user_id)
        .all()
    )
    for tag in tags:
        if tag.libelle.lower() in normalized:
            db.delete(tag)


def _expire_event_tags_for_next_visit(db: Session, ruche_id: UUID, user_id: UUID) -> list[str]:
    tags = (
        db.query(models.RucheTag)
        .filter(models.RucheTag.ruche_id == ruche_id, models.RucheTag.user_id == user_id)
        .filter(func.lower(models.RucheTag.libelle).in_(EVENT_TAGS))
        .all()
    )
    removed_labels = [tag.libelle for tag in tags]
    for tag in tags:
        db.delete(tag)
    return removed_labels



def _validate_owned_visite_rucher(db: Session, visite_rucher_id: UUID | None, user_id: UUID) -> None:
    if visite_rucher_id is None:
        return

    visite_rucher = db.get(models.VisiteRucher, visite_rucher_id)
    if visite_rucher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visite rucher introuvable")

    rucher = db.get(models.Rucher, visite_rucher.rucher_id)
    if rucher is None or rucher.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visite rucher introuvable")


def _validate_visite_rucher_matches_ruche(db: Session, ruche_id: UUID, visite_rucher_id: UUID | None) -> None:
    if visite_rucher_id is None:
        return

    ruche = db.get(models.Ruche, ruche_id)
    visite_rucher = db.get(models.VisiteRucher, visite_rucher_id)
    if ruche is None or visite_rucher is None or ruche.rucher_id is None or ruche.rucher_id != visite_rucher.rucher_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La visite rucher doit correspondre au rucher de la ruche",
        )


def _validate_visite_has_content(payload: schemas.VisiteRucheCreate | schemas.VisiteRucheUpdate) -> None:
    has_observation = any(
        value is not None
        for value in (
            payload.reine_vue,
            payload.presence_ponte,
            payload.etat_couvain,
            payload.nombre_cadres_couvain,
            payload.reserves_nourriture,
            payload.agressivite,
            payload.note_ruche,
            payload.nombre_cadres_total,
        )
    )
    has_actions = bool(
        payload.action_ids
        or payload.interventions
        or payload.mouvements_cadres
        or payload.mouvements_hausses
        # Un transvasement ou des tags choisis suffisent a justifier la visite.
        or getattr(payload, "transvasement", None)
        or getattr(payload, "tags_ajoutes", None)
        or getattr(payload, "ref_type_ruche_id", None)
    )

    if not has_observation and not has_actions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La visite doit contenir au moins une observation, une action, une intervention ou un mouvement",
        )


def _build_visite_response(
    db: Session,
    visite: models.VisiteRuche,
    tag_suggestions: list[str] | None = None,
    tag_removal_suggestions: list[str] | None = None,
) -> schemas.VisiteRucheResponse:
    interventions = (
        db.query(models.InterventionSanitaire)
        .filter(models.InterventionSanitaire.visite_ruche_id == visite.id)
        .order_by(models.InterventionSanitaire.date_action.asc())
        .all()
    )
    mouvements = (
        db.query(models.GestionCadres)
        .filter(models.GestionCadres.visite_ruche_id == visite.id)
        .order_by(models.GestionCadres.id.asc())
        .all()
    )
    mouvements_hausses = (
        db.query(models.MouvementHausse)
        .filter(models.MouvementHausse.visite_ruche_id == visite.id)
        .order_by(models.MouvementHausse.id.asc())
        .all()
    )

    return schemas.VisiteRucheResponse(
        id=visite.id,
        ruche_id=visite.ruche_id,
        visite_rucher_id=visite.visite_rucher_id,
        reine_id=visite.reine_id,
        date_visite=visite.date_visite,
        updated_at=visite.updated_at,
        reine_vue=visite.reine_vue,
        presence_ponte=visite.presence_ponte,
        etat_couvain=visite.etat_couvain,
        nombre_cadres_couvain=visite.nombre_cadres_couvain,
        reserves_nourriture=visite.reserves_nourriture,
        agressivite=visite.agressivite,
        note_ruche=visite.note_ruche,
        nombre_cadres_total=visite.nombre_cadres_total,
        corps_present=visite.corps_present,
        hausse_presente=visite.hausse_presente,
        grille_a_reine_presente=visite.grille_a_reine_presente,
        nourrisseur_present=visite.nourrisseur_present,
        toit_present=visite.toit_present,
        plancher_present=visite.plancher_present,
        partition_presente=visite.partition_presente,
        source_saisie=visite.source_saisie,
        statut_validation=visite.statut_validation,
        actions=[schemas.ActionVisiteResponse.model_validate(action) for action in visite.actions],
        interventions=[schemas.InterventionSanitaireResponse.model_validate(item) for item in interventions],
        mouvements_cadres=[schemas.GestionCadresResponse.model_validate(item) for item in mouvements],
        mouvements_hausses=[schemas.MouvementHausseResponse.model_validate(item) for item in mouvements_hausses],
        tag_suggestions=tag_suggestions or [],
        tag_removal_suggestions=tag_removal_suggestions or [],
    )


def _validate_visite_effective_content(
    reine_vue: bool | None,
    presence_ponte: bool | None,
    etat_couvain: str | None,
    nombre_cadres_couvain: int | None,
    reserves_nourriture: str | None,
    agressivite: int | None,
    note_ruche: int | None,
    nombre_cadres_total: int | None,
    action_ids: list[UUID],
    interventions: list[schemas.InterventionSanitaireCreate],
    mouvements_cadres: list[schemas.GestionCadresCreate],
    mouvements_hausses: list[schemas.MouvementHausseCreate],
) -> None:
    has_observation = any(
        value is not None
        for value in (
            reine_vue,
            presence_ponte,
            etat_couvain,
            nombre_cadres_couvain,
            reserves_nourriture,
            agressivite,
            note_ruche,
            nombre_cadres_total,
        )
    )
    has_actions = bool(action_ids or interventions or mouvements_cadres or mouvements_hausses)
    if not has_observation and not has_actions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La visite doit contenir au moins une observation, une action, une intervention ou un mouvement",
        )


def _sync_hive_frame_count(db: Session, visite: models.VisiteRuche) -> None:
    """La fiche ruche reprend le nombre de cadres de sa visite la plus recente.

    Une visite plus ancienne (synchronisee en retard, ou corrigee) ne change
    pas la fiche. Le nombre sert ensuite a pre-remplir la visite suivante.
    """
    if visite.nombre_cadres_total is None:
        return
    db.flush()
    this_date = db.query(models.VisiteRuche.date_visite).filter(models.VisiteRuche.id == visite.id).scalar_subquery()
    newer = (
        db.query(models.VisiteRuche.id)
        .filter(models.VisiteRuche.ruche_id == visite.ruche_id, models.VisiteRuche.id != visite.id, models.VisiteRuche.date_visite > this_date)
        .first()
    )
    if newer is None:
        db.get(models.Ruche, visite.ruche_id).nombre_cadres = visite.nombre_cadres_total


def _replace_visit_children(db: Session, visite: models.VisiteRuche, payload: schemas.VisiteRucheCreate | schemas.VisiteRucheUpdate) -> None:
    if payload.action_ids:
        actions = db.query(models.RefActionVisite).filter(models.RefActionVisite.id.in_(payload.action_ids)).all()
        if len(actions) != len(payload.action_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Une ou plusieurs actions de visite sont introuvables")
        visite.actions = actions
    else:
        visite.actions = []

    db.query(models.InterventionSanitaire).filter(models.InterventionSanitaire.visite_ruche_id == visite.id).delete()
    db.query(models.GestionCadres).filter(models.GestionCadres.visite_ruche_id == visite.id).delete()
    db.query(models.MouvementHausse).filter(models.MouvementHausse.visite_ruche_id == visite.id).delete()

    for intervention in payload.interventions:
        ref = db.get(models.RefTypeIntervention, intervention.ref_type_intervention_id)
        if ref is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type d'intervention introuvable")
        db.add(
            models.InterventionSanitaire(
                ruche_id=visite.ruche_id,
                visite_ruche_id=visite.id,
                ref_type_intervention_id=intervention.ref_type_intervention_id,
                details=intervention.details,
            )
        )

    for mouvement in payload.mouvements_cadres:
        ref = db.get(models.RefActionCadre, mouvement.ref_action_cadre_id)
        if ref is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action cadre introuvable")
        db.add(
            models.GestionCadres(
                ruche_id=visite.ruche_id,
                visite_ruche_id=visite.id,
                ref_action_cadre_id=mouvement.ref_action_cadre_id,
                quantite=mouvement.quantite,
                annee_cire=mouvement.annee_cire,
            )
        )

    for mouvement in payload.mouvements_hausses:
        db.add(
            models.MouvementHausse(
                ruche_id=visite.ruche_id,
                visite_ruche_id=visite.id,
                quantite_delta=mouvement.quantite_delta,
                note=mouvement.note,
            )
        )


@router.get("", response_model=list[schemas.VisiteRucheResponse])
def list_visites(
    ruche_id: UUID,
    source_saisie: str | None = None,
    statut_validation: str | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_ruche(db, ruche_id, current_user.id)

    if source_saisie is not None and source_saisie not in VALID_SOURCES_SAISIE:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="source_saisie invalide")
    if statut_validation is not None and statut_validation not in VALID_STATUTS_VALIDATION:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="statut_validation invalide")

    query = db.query(models.VisiteRuche).options(selectinload(models.VisiteRuche.actions)).filter(models.VisiteRuche.ruche_id == ruche_id)
    if source_saisie is not None:
        query = query.filter(models.VisiteRuche.source_saisie == source_saisie)
    if statut_validation is not None:
        query = query.filter(models.VisiteRuche.statut_validation == statut_validation)

    visites = query.order_by(models.VisiteRuche.date_visite.desc()).all()
    return [_build_visite_response(db, visite) for visite in visites]


@router.get("/historique", response_model=schemas.VisiteHistoriqueResponse)
def list_visit_history(
    rucher_id: UUID | None = None,
    ruche_id: UUID | None = None,
    search: str | None = None,
    type_evenement: str | None = None,
    source_saisie: str | None = None,
    statut_validation: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Historique leger et pagine pour la liste client, sans N+1 par ruche."""
    if source_saisie is not None and source_saisie not in VALID_SOURCES_SAISIE:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="source_saisie invalide")
    if statut_validation is not None and statut_validation not in VALID_STATUTS_VALIDATION:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="statut_validation invalide")
    if type_evenement is not None and type_evenement not in VALID_TYPES_HISTORIQUE:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="type_evenement invalide")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date doit etre <= end_date")
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit doit etre compris entre 1 et 200")
    if rucher_id is not None:
        rucher = db.get(models.Rucher, rucher_id)
        if rucher is None or rucher.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rucher introuvable")
    if ruche_id is not None:
        ruche = get_owned_ruche(db, ruche_id, current_user.id)
        if rucher_id is not None and ruche.rucher_id != rucher_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La ruche ne correspond pas au rucher filtre")

    query = (
        db.query(models.VisiteRuche, models.Ruche.identifiant_personnalise, models.Rucher.nom)
        .join(models.Ruche, models.VisiteRuche.ruche_id == models.Ruche.id)
        .outerjoin(models.Rucher, models.Ruche.rucher_id == models.Rucher.id)
        .filter(models.Ruche.user_id == current_user.id)
    )
    if rucher_id is not None:
        query = query.filter(models.Ruche.rucher_id == rucher_id)
    if ruche_id is not None:
        query = query.filter(models.VisiteRuche.ruche_id == ruche_id)
    if source_saisie is not None:
        query = query.filter(models.VisiteRuche.source_saisie == source_saisie)
    if statut_validation is not None:
        query = query.filter(models.VisiteRuche.statut_validation == statut_validation)
    if start_date is not None:
        query = query.filter(func.date(models.VisiteRuche.date_visite) >= start_date)
    if end_date is not None:
        query = query.filter(func.date(models.VisiteRuche.date_visite) <= end_date)
    if search:
        query = query.filter(models.Ruche.identifiant_personnalise.ilike(f"%{search.strip()}%"))

    recolte_query = (
        db.query(models.Recolte, models.Ruche.identifiant_personnalise, models.Rucher.nom)
        .join(models.Ruche, models.Recolte.ruche_id == models.Ruche.id)
        .outerjoin(models.Rucher, models.Ruche.rucher_id == models.Rucher.id)
        .filter(models.Ruche.user_id == current_user.id)
    )
    if rucher_id is not None:
        recolte_query = recolte_query.filter(models.Ruche.rucher_id == rucher_id)
    if ruche_id is not None:
        recolte_query = recolte_query.filter(models.Recolte.ruche_id == ruche_id)
    if start_date is not None:
        recolte_query = recolte_query.filter(func.date(models.Recolte.date_recolte) >= start_date)
    if end_date is not None:
        recolte_query = recolte_query.filter(func.date(models.Recolte.date_recolte) <= end_date)
    if search:
        recolte_query = recolte_query.filter(models.Ruche.identifiant_personnalise.ilike(f"%{search.strip()}%"))

    include_visits = type_evenement != "recolte"
    include_harvests = type_evenement != "visite" and source_saisie is None and statut_validation in (None, "valide")
    visit_total = query.count() if include_visits else 0
    harvest_total = recolte_query.count() if include_harvests else 0
    visit_rows = query.order_by(models.VisiteRuche.date_visite.desc()).limit(limit).all() if include_visits else []
    harvest_rows = recolte_query.order_by(models.Recolte.date_recolte.desc()).limit(limit).all() if include_harvests else []
    items = [
        schemas.VisiteHistoriqueItem(
            id=visit.id,
            ruche_id=visit.ruche_id,
            rucher_label=rucher_label or "Atelier",
            ruche_label=label,
            date_visite=visit.date_visite,
            type_evenement="visite",
            note_ruche=visit.note_ruche,
            source_saisie=visit.source_saisie,
            statut_validation=visit.statut_validation,
        )
        for visit, label, rucher_label in visit_rows
    ]
    items.extend(
        schemas.VisiteHistoriqueItem(
            id=harvest.id,
            ruche_id=harvest.ruche_id,
            rucher_label=rucher_label or "Atelier",
            ruche_label=label,
            date_visite=harvest.date_recolte,
            type_evenement="recolte",
            poids_miel_kg=float(harvest.poids_miel_kg),
            source_saisie="recolte",
            statut_validation="valide",
        )
        for harvest, label, rucher_label in harvest_rows
    )
    items.sort(key=lambda item: item.date_visite, reverse=True)
    return schemas.VisiteHistoriqueResponse(
        total=visit_total + harvest_total,
        visits=items[:limit],
    )


@router.get("/synthese/periode", response_model=schemas.VisiteSynthesePeriodeResponse)
def visites_synthese_periode(
    start_date: date | None = None,
    end_date: date | None = None,
    rucher_id: UUID | None = None,
    ruche_id: UUID | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date doit etre <= end_date")

    if rucher_id is not None:
        rucher = db.get(models.Rucher, rucher_id)
        if rucher is None or rucher.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rucher introuvable")

    if ruche_id is not None:
        ruche = get_owned_ruche(db, ruche_id, current_user.id)
        if rucher_id is not None and ruche.rucher_id != rucher_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La ruche ne correspond pas au rucher filtre")

    visites_ruche_query = db.query(models.VisiteRuche).join(models.Ruche, models.VisiteRuche.ruche_id == models.Ruche.id).filter(models.Ruche.user_id == current_user.id)
    if ruche_id is not None:
        visites_ruche_query = visites_ruche_query.filter(models.VisiteRuche.ruche_id == ruche_id)
    if rucher_id is not None:
        visites_ruche_query = visites_ruche_query.filter(models.Ruche.rucher_id == rucher_id)
    if start_date is not None:
        visites_ruche_query = visites_ruche_query.filter(func.date(models.VisiteRuche.date_visite) >= start_date)
    if end_date is not None:
        visites_ruche_query = visites_ruche_query.filter(func.date(models.VisiteRuche.date_visite) <= end_date)
    visites_ruche = visites_ruche_query.all()

    visites_rucher_query = db.query(models.VisiteRucher).join(models.Rucher, models.VisiteRucher.rucher_id == models.Rucher.id).filter(models.Rucher.user_id == current_user.id)
    if rucher_id is not None:
        visites_rucher_query = visites_rucher_query.filter(models.VisiteRucher.rucher_id == rucher_id)
    if start_date is not None:
        visites_rucher_query = visites_rucher_query.filter(func.date(models.VisiteRucher.date_visite) >= start_date)
    if end_date is not None:
        visites_rucher_query = visites_rucher_query.filter(func.date(models.VisiteRucher.date_visite) <= end_date)
    visites_rucher = visites_rucher_query.all()

    notes_ruche = [item.note_ruche for item in visites_ruche if item.note_ruche is not None]
    notes_rucher = [item.note_globale for item in visites_rucher if item.note_globale is not None]
    reine_flags = [item.reine_vue for item in visites_ruche if item.reine_vue is not None]

    return schemas.VisiteSynthesePeriodeResponse(
        start_date=start_date,
        end_date=end_date,
        ruche_id=ruche_id,
        rucher_id=rucher_id,
        total_visites_ruche=len(visites_ruche),
        total_visites_rucher=len(visites_rucher),
        visites_manuelles=sum(1 for item in visites_ruche if item.source_saisie == "manuelle"),
        visites_ia_vocale=sum(1 for item in visites_ruche if item.source_saisie == "ia_vocale"),
        brouillons_ia=sum(1 for item in visites_ruche if item.source_saisie == "ia_vocale" and item.statut_validation == "brouillon"),
        note_ruche_moyenne=round(sum(notes_ruche) / len(notes_ruche), 2) if notes_ruche else None,
        note_rucher_moyenne=round(sum(notes_rucher) / len(notes_rucher), 2) if notes_rucher else None,
        taux_reine_vue=round(sum(1 for flag in reine_flags if flag) / len(reine_flags), 2) if reine_flags else None,
    )

@router.get("/synthese/avancee", response_model=schemas.VisiteSyntheseAvanceeResponse)
def visites_synthese_avancee(
    window_days: int = 30,
    rucher_id: UUID | None = None,
    ruche_id: UUID | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if window_days not in {30, 90, 180}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="window_days doit etre 30, 90 ou 180")
    if rucher_id is not None:
        rucher = db.get(models.Rucher, rucher_id)
        if rucher is None or rucher.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rucher introuvable")
    if ruche_id is not None:
        ruche = get_owned_ruche(db, ruche_id, current_user.id)
        if rucher_id is not None and ruche.rucher_id != rucher_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La ruche ne correspond pas au rucher filtre")

    today = datetime.now(timezone.utc).date()
    current_start = today - timedelta(days=window_days - 1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=window_days - 1)
    query = db.query(models.VisiteRuche).join(models.Ruche).filter(models.Ruche.user_id == current_user.id)
    if rucher_id is not None:
        query = query.filter(models.Ruche.rucher_id == rucher_id)
    if ruche_id is not None:
        query = query.filter(models.Ruche.id == ruche_id)
    visites = query.all()

    def period_metrics(start_date: date, end_date: date) -> schemas.VisiteSyntheseAvanceePeriode:
        period_visites = [item for item in visites if start_date <= item.date_visite.date() <= end_date]
        notes = [item.note_ruche for item in period_visites if item.note_ruche is not None]
        queen_flags = [item.reine_vue for item in period_visites if item.reine_vue is not None]
        brood_flags = [item.etat_couvain for item in period_visites if item.etat_couvain is not None]
        total_frames = [item.nombre_cadres_total for item in period_visites if item.nombre_cadres_total is not None]
        brood_frames = [item.nombre_cadres_couvain for item in period_visites if item.nombre_cadres_couvain is not None]
        brood_ratios = [item.nombre_cadres_couvain / item.nombre_cadres_total for item in period_visites if item.nombre_cadres_couvain is not None and item.nombre_cadres_total and item.nombre_cadres_total > 0]
        return schemas.VisiteSyntheseAvanceePeriode(
            start_date=start_date,
            end_date=end_date,
            total_visites=len(period_visites),
            note_moyenne=round(sum(notes) / len(notes), 2) if notes else None,
            taux_reine_vue=round(sum(1 for value in queen_flags if value) / len(queen_flags), 2) if queen_flags else None,
            taux_couvain=round(sum(1 for value in brood_flags if value in {"normal", "excellent"}) / len(brood_flags), 2) if brood_flags else None,
            cadres_total_moyens=round(sum(total_frames) / len(total_frames), 2) if total_frames else None,
            cadres_couvain_moyens=round(sum(brood_frames) / len(brood_frames), 2) if brood_frames else None,
            taux_cadres_couvain=round(sum(brood_ratios) / len(brood_ratios), 2) if brood_ratios else None,
        )

    ruches_query = db.query(models.Ruche, models.Rucher.nom).outerjoin(models.Rucher, models.Ruche.rucher_id == models.Rucher.id).filter(models.Ruche.user_id == current_user.id, models.Ruche.archived_at.is_(None))
    if rucher_id is not None:
        ruches_query = ruches_query.filter(models.Ruche.rucher_id == rucher_id)
    uncovered_hives = []
    for ruche, rucher_nom in ruches_query.all():
        ruche_visites = [item for item in visites if item.ruche_id == ruche.id and item.date_visite.date() <= today]
        last_visit = max((item.date_visite for item in ruche_visites), default=None)
        if last_visit is None or last_visit.date() < current_start:
            uncovered_hives.append(schemas.RucheSansVisiteResponse(
                ruche_id=ruche.id,
                identifiant_personnalise=ruche.identifiant_personnalise,
                rucher_nom=rucher_nom,
                derniere_visite=last_visit,
                jours_depuis_visite=(today - last_visit.date()).days if last_visit else None,
            ))

    current = period_metrics(current_start, today)
    previous = period_metrics(previous_start, previous_end)
    return schemas.VisiteSyntheseAvanceeResponse(
        window_days=window_days,
        current=current,
        previous=previous,
        note_delta=round(current.note_moyenne - previous.note_moyenne, 2) if current.note_moyenne is not None and previous.note_moyenne is not None else None,
        visites_delta=current.total_visites - previous.total_visites,
        reine_delta=round(current.taux_reine_vue - previous.taux_reine_vue, 2) if current.taux_reine_vue is not None and previous.taux_reine_vue is not None else None,
        couvain_delta=round(current.taux_couvain - previous.taux_couvain, 2) if current.taux_couvain is not None and previous.taux_couvain is not None else None,
        uncovered_hives=uncovered_hives,
    )


@router.post("", response_model=schemas.VisiteRucheResponse, status_code=status.HTTP_201_CREATED)
def create_visite(
    payload: schemas.VisiteRucheCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    endpoint = "POST:/visites"
    if idempotency_key:
        # Verrou transactionnel sur la cle : deux synchronisations paralleles
        # de la meme visite s'executent l'une apres l'autre, la seconde
        # renvoie alors la reponse memorisee au lieu de creer un doublon.
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"{current_user.id}:{endpoint}:{idempotency_key}"},
        )
        previous = db.query(models.IdempotencyKey).filter_by(user_id=current_user.id, key=idempotency_key, endpoint=endpoint).first()
        if previous is not None:
            return schemas.VisiteRucheResponse.model_validate(previous.response_payload)
    _validate_visite_has_content(payload)
    hive = get_owned_ruche(db, payload.ruche_id, current_user.id)
    if hive.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ruche archivee : elle a ete demontee ou transvasee")
    # Une visite saisie hors ligne garde son heure de saisie, pas celle de la
    # synchronisation ; une date future est ramenee a maintenant.
    visit_date = None
    if payload.date_visite is not None:
        visit_date = min(payload.date_visite, datetime.now(timezone.utc))
    effective_reine_id = payload.reine_id
    if effective_reine_id is None:
        active_reine = db.query(models.Reine).filter(models.Reine.ruche_id == payload.ruche_id, models.Reine.statut == "active").first()
        effective_reine_id = active_reine.id if active_reine is not None else None
    elif db.query(models.Reine).filter(models.Reine.id == effective_reine_id, models.Reine.ruche_id == payload.ruche_id).first() is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La reine ne correspond pas a la ruche")
    _validate_owned_visite_rucher(db, payload.visite_rucher_id, current_user.id)
    _validate_visite_rucher_matches_ruche(db, payload.ruche_id, payload.visite_rucher_id)

    visite = models.VisiteRuche(
        **({"date_visite": visit_date} if visit_date is not None else {}),
        ruche_id=payload.ruche_id,
        visite_rucher_id=payload.visite_rucher_id,
        reine_id=effective_reine_id,
        reine_vue=payload.reine_vue,
        presence_ponte=payload.presence_ponte,
        etat_couvain=payload.etat_couvain,
        nombre_cadres_couvain=payload.nombre_cadres_couvain,
        reserves_nourriture=payload.reserves_nourriture,
        agressivite=payload.agressivite,
        note_ruche=payload.note_ruche,
        nombre_cadres_total=payload.nombre_cadres_total,
        corps_present=payload.corps_present,
        hausse_presente=payload.hausse_presente,
        grille_a_reine_presente=payload.grille_a_reine_presente,
        nourrisseur_present=payload.nourrisseur_present,
        toit_present=payload.toit_present,
        plancher_present=payload.plancher_present,
        partition_presente=payload.partition_presente,
        source_saisie=payload.source_saisie,
        statut_validation=payload.statut_validation,
    )
    db.add(visite)
    db.flush()

    _replace_visit_children(db, visite, payload)
    tag_suggestions, tag_removals = _visit_tag_rules(
        payload.reine_vue,
        payload.etat_couvain,
        payload.nombre_cadres_couvain,
        payload.reserves_nourriture,
    )
    _apply_reversible_tag_removals(db, visite.ruche_id, current_user.id, tag_removals)
    tag_removal_suggestions = _expire_event_tags_for_next_visit(db, visite.ruche_id, current_user.id)
    # Tags choisis pendant une visite hors ligne : appliques avec la visite,
    # donc couverts par la meme cle d'idempotence. Un doublon ou un tag
    # verrouille est ignore pour ne pas bloquer la synchronisation.
    if payload.tags_ajoutes:
        ruche = db.get(models.Ruche, visite.ruche_id)
        for label in payload.tags_ajoutes:
            try:
                with db.begin_nested():
                    add_manual_tag(db, ruche, current_user.id, label)
            except HTTPException:
                continue

    # Transvasement saisi pendant la visite : applique dans la meme
    # transaction (donc rejoue sans doublon) ; s'il est impossible (stock
    # insuffisant...), la visite reste enregistree et un avertissement est rendu.
    _sync_hive_frame_count(db, visite)
    if payload.ref_type_ruche_id is not None and payload.ref_type_ruche_id != hive.ref_type_ruche_id:
        validate_hive_type(db, current_user.id, payload.ref_type_ruche_id)
        hive.ref_type_ruche_id = payload.ref_type_ruche_id
    avertissements: list[str] = []
    if payload.transvasement is not None:
        try:
            with db.begin_nested():
                _, transvasement_suggestions = apply_transvasement(db, hive, current_user.id, payload.transvasement, visite.id)
            tag_suggestions = [*tag_suggestions, *[label for label in transvasement_suggestions if label not in tag_suggestions]]
        except HTTPException as error:
            avertissements.append(f"Transvasement non applique : {error.detail}")

    db.flush()
    visite = (
        db.query(models.VisiteRuche)
        .options(selectinload(models.VisiteRuche.actions))
        .filter(models.VisiteRuche.id == visite.id)
        .one()
    )
    response = _build_visite_response(db, visite, tag_suggestions=tag_suggestions, tag_removal_suggestions=tag_removal_suggestions)
    response.avertissements = avertissements
    if idempotency_key:
        db.add(models.IdempotencyKey(
            user_id=current_user.id,
            key=idempotency_key,
            endpoint=endpoint,
            response_status=status.HTTP_201_CREATED,
            response_payload=response.model_dump(mode="json"),
        ))
    # Visite et cle d'idempotence sont validees ensemble.
    db.commit()
    return response


@router.get("/{visite_id}", response_model=schemas.VisiteRucheResponse)
def get_visite(visite_id: UUID, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    visite = (
        db.query(models.VisiteRuche)
        .options(selectinload(models.VisiteRuche.actions))
        .filter(models.VisiteRuche.id == visite_id)
        .first()
    )
    if visite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visite introuvable")
    get_owned_ruche(db, visite.ruche_id, current_user.id)
    return _build_visite_response(db, visite)


@router.put("/{visite_id}", response_model=schemas.VisiteRucheResponse)
def update_visite(
    visite_id: UUID,
    payload: schemas.VisiteRucheUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_visite_has_content(payload)
    visite = (
        db.query(models.VisiteRuche)
        .options(selectinload(models.VisiteRuche.actions))
        .filter(models.VisiteRuche.id == visite_id)
        .first()
    )
    if visite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visite introuvable")

    get_owned_ruche(db, visite.ruche_id, current_user.id)
    get_owned_ruche(db, payload.ruche_id, current_user.id)
    _validate_owned_visite_rucher(db, payload.visite_rucher_id, current_user.id)
    _validate_visite_rucher_matches_ruche(db, payload.ruche_id, payload.visite_rucher_id)

    for field, value in payload.model_dump(exclude={"action_ids", "interventions", "mouvements_cadres", "mouvements_hausses"}).items():
        setattr(visite, field, value)

    _replace_visit_children(db, visite, payload)
    tag_suggestions, tag_removals = _visit_tag_rules(
        payload.reine_vue,
        payload.etat_couvain,
        payload.nombre_cadres_couvain,
        payload.reserves_nourriture,
    )
    _apply_reversible_tag_removals(db, visite.ruche_id, current_user.id, tag_removals)
    tag_removal_suggestions = _expire_event_tags_for_next_visit(db, visite.ruche_id, current_user.id)
    _sync_hive_frame_count(db, visite)

    db.commit()
    db.refresh(visite)
    return _build_visite_response(db, visite, tag_suggestions=tag_suggestions, tag_removal_suggestions=tag_removal_suggestions)


@router.patch("/{visite_id}", response_model=schemas.VisiteRucheResponse)
def patch_visite(
    visite_id: UUID,
    payload: schemas.VisiteRuchePatch,
    client_base_updated_at: str | None = Header(default=None, alias="X-Client-Base-Updated-At"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patch_data = payload.model_dump(exclude_unset=True)
    if not patch_data:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Aucun champ a mettre a jour")

    visite = (
        db.query(models.VisiteRuche)
        .options(selectinload(models.VisiteRuche.actions))
        .filter(models.VisiteRuche.id == visite_id)
        .first()
    )
    if visite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visite introuvable")

    get_owned_ruche(db, visite.ruche_id, current_user.id)

    if client_base_updated_at:
        try:
            base_updated_at = datetime.fromisoformat(client_base_updated_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="X-Client-Base-Updated-At invalide") from exc
        if visite.updated_at is not None and visite.updated_at > base_updated_at:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La visite a ete modifiee depuis la derniere synchronisation")

    effective_ruche_id = payload.ruche_id if "ruche_id" in patch_data else visite.ruche_id
    effective_visite_rucher_id = payload.visite_rucher_id if "visite_rucher_id" in patch_data else visite.visite_rucher_id

    get_owned_ruche(db, effective_ruche_id, current_user.id)
    _validate_owned_visite_rucher(db, effective_visite_rucher_id, current_user.id)
    _validate_visite_rucher_matches_ruche(db, effective_ruche_id, effective_visite_rucher_id)

    existing_interventions = (
        db.query(models.InterventionSanitaire)
        .filter(models.InterventionSanitaire.visite_ruche_id == visite.id)
        .all()
    )
    existing_mouvements_cadres = (
        db.query(models.GestionCadres)
        .filter(models.GestionCadres.visite_ruche_id == visite.id)
        .all()
    )
    existing_mouvements_hausses = (
        db.query(models.MouvementHausse)
        .filter(models.MouvementHausse.visite_ruche_id == visite.id)
        .all()
    )

    action_ids = payload.action_ids if "action_ids" in patch_data else [item.id for item in visite.actions]
    interventions = (
        payload.interventions
        if "interventions" in patch_data
        else [schemas.InterventionSanitaireCreate(ref_type_intervention_id=item.ref_type_intervention_id, details=item.details) for item in existing_interventions]
    )
    mouvements_cadres = (
        payload.mouvements_cadres
        if "mouvements_cadres" in patch_data
        else [schemas.GestionCadresCreate(ref_action_cadre_id=item.ref_action_cadre_id, quantite=item.quantite, annee_cire=item.annee_cire) for item in existing_mouvements_cadres]
    )
    mouvements_hausses = (
        payload.mouvements_hausses
        if "mouvements_hausses" in patch_data
        else [schemas.MouvementHausseCreate(quantite_delta=item.quantite_delta, note=item.note) for item in existing_mouvements_hausses]
    )

    _validate_visite_effective_content(
        payload.reine_vue if "reine_vue" in patch_data else visite.reine_vue,
        payload.presence_ponte if "presence_ponte" in patch_data else visite.presence_ponte,
        payload.etat_couvain if "etat_couvain" in patch_data else visite.etat_couvain,
        payload.nombre_cadres_couvain if "nombre_cadres_couvain" in patch_data else visite.nombre_cadres_couvain,
        payload.reserves_nourriture if "reserves_nourriture" in patch_data else visite.reserves_nourriture,
        payload.agressivite if "agressivite" in patch_data else visite.agressivite,
        payload.note_ruche if "note_ruche" in patch_data else visite.note_ruche,
        payload.nombre_cadres_total if "nombre_cadres_total" in patch_data else visite.nombre_cadres_total,
        action_ids or [],
        interventions or [],
        mouvements_cadres or [],
        mouvements_hausses or [],
    )

    scalar_fields = {
        "ruche_id",
        "visite_rucher_id",
        "reine_vue",
        "presence_ponte",
        "etat_couvain",
        "nombre_cadres_couvain",
        "reserves_nourriture",
        "agressivite",
        "note_ruche",
        "nombre_cadres_total",
        "source_saisie",
        "statut_validation",
    }
    for field in scalar_fields:
        if field in patch_data:
            setattr(visite, field, patch_data[field])

    merged_payload = schemas.VisiteRucheUpdate(
        ruche_id=effective_ruche_id,
        visite_rucher_id=effective_visite_rucher_id,
        reine_vue=payload.reine_vue if "reine_vue" in patch_data else visite.reine_vue,
        presence_ponte=payload.presence_ponte if "presence_ponte" in patch_data else visite.presence_ponte,
        etat_couvain=payload.etat_couvain if "etat_couvain" in patch_data else visite.etat_couvain,
        nombre_cadres_couvain=payload.nombre_cadres_couvain if "nombre_cadres_couvain" in patch_data else visite.nombre_cadres_couvain,
        reserves_nourriture=payload.reserves_nourriture if "reserves_nourriture" in patch_data else visite.reserves_nourriture,
        agressivite=payload.agressivite if "agressivite" in patch_data else visite.agressivite,
        note_ruche=payload.note_ruche if "note_ruche" in patch_data else visite.note_ruche,
        nombre_cadres_total=payload.nombre_cadres_total if "nombre_cadres_total" in patch_data else visite.nombre_cadres_total,
        source_saisie=payload.source_saisie if "source_saisie" in patch_data else visite.source_saisie,
        statut_validation=payload.statut_validation if "statut_validation" in patch_data else visite.statut_validation,
        action_ids=action_ids or [],
        interventions=interventions or [],
        mouvements_cadres=mouvements_cadres or [],
        mouvements_hausses=mouvements_hausses or [],
    )
    _replace_visit_children(db, visite, merged_payload)
    tag_suggestions, tag_removals = _visit_tag_rules(
        merged_payload.reine_vue,
        merged_payload.etat_couvain,
        merged_payload.nombre_cadres_couvain,
        merged_payload.reserves_nourriture,
    )
    _apply_reversible_tag_removals(db, visite.ruche_id, current_user.id, tag_removals)
    tag_removal_suggestions = _expire_event_tags_for_next_visit(db, visite.ruche_id, current_user.id)
    _sync_hive_frame_count(db, visite)

    db.commit()
    db.refresh(visite)
    return _build_visite_response(db, visite, tag_suggestions=tag_suggestions, tag_removal_suggestions=tag_removal_suggestions)


@router.delete("/{visite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visite(visite_id: UUID, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    visite = db.get(models.VisiteRuche, visite_id)
    if visite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visite introuvable")

    get_owned_ruche(db, visite.ruche_id, current_user.id)

    db.delete(visite)
    db.commit()
    return None
