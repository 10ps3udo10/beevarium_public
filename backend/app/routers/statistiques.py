from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.ownership import get_owned_ruche, get_owned_rucher
from app.materiel_flux import default_frame_count, hive_elements
from app.surveillance import watch_reasons
from app.security import get_current_user

router = APIRouter(prefix="/statistiques", tags=["statistiques"])


def _apiculture_year(today: date | None = None) -> int:
    today = today or datetime.now(timezone.utc).date()
    return today.year


def _owned_scope(db: Session, user_id: UUID, rucher_id: UUID | None, ruche_id: UUID | None):
    if rucher_id is not None:
        get_owned_rucher(db, rucher_id, user_id)
    if ruche_id is not None:
        ruche = get_owned_ruche(db, ruche_id, user_id)
        if rucher_id is not None and ruche.rucher_id != rucher_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La ruche ne correspond pas au rucher")


def _scope_hives(db: Session, user_id: UUID, rucher_id: UUID | None, ruche_id: UUID | None, include_archived: bool = False):
    # Les ruches archivees (demontees, transvasees) sortent des effectifs mais
    # leur historique (visites, recoltes) reste compte quand on le demande.
    query = db.query(models.Ruche).filter(models.Ruche.user_id == user_id)
    if not include_archived:
        query = query.filter(models.Ruche.archived_at.is_(None))
    if rucher_id is not None:
        query = query.filter(models.Ruche.rucher_id == rucher_id)
    if ruche_id is not None:
        query = query.filter(models.Ruche.id == ruche_id)
    return query.all()


def _as_date(value) -> date | None:
    """`date_visite` peut etre une date ou un datetime selon les enregistrements."""
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


@router.get("/dernieres-visites", response_model=list[schemas.DerniereVisiteRuche])
def get_dernieres_visites(
    rucher_id: UUID | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Derniere visite de chaque ruche, en une requete.

    Le client faisait un appel par ruche, ce qui devenait prohibitif au-dela
    d une trentaine de ruches dans un rucher.
    """
    _owned_scope(db, current_user.id, rucher_id, None)
    hives = _scope_hives(db, current_user.id, rucher_id, None)
    hive_ids = [hive.id for hive in hives]
    if not hive_ids:
        return []

    visits = (
        db.query(models.VisiteRuche)
        .filter(models.VisiteRuche.ruche_id.in_(hive_ids))
        .order_by(models.VisiteRuche.date_visite.asc())
        .all()
    )
    derniere_par_ruche: dict[UUID, models.VisiteRuche] = {}
    for visit in visits:
        derniere_par_ruche[visit.ruche_id] = visit

    return [
        schemas.DerniereVisiteRuche(
            ruche_id=ruche_id_courant,
            date_visite=visit.date_visite,
            nombre_cadres_total=visit.nombre_cadres_total,
            nombre_cadres_couvain=visit.nombre_cadres_couvain,
            note_ruche=visit.note_ruche,
            statut_validation=visit.statut_validation,
        )
        for ruche_id_courant, visit in derniere_par_ruche.items()
    ]


@router.get("/cheptel", response_model=schemas.StatistiquesCheptelResponse)
def get_cheptel_overview(
    rucher_id: UUID | None = None,
    ruche_id: UUID | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Indicateurs du tableau de bord, calcules en une seule requete par table.

    Le client faisait auparavant deux appels par ruche, ce qui devenait
    inutilisable au-dela de quelques dizaines de ruches.
    """
    _owned_scope(db, current_user.id, rucher_id, ruche_id)
    hives = _scope_hives(db, current_user.id, rucher_id, ruche_id)
    hive_ids = [hive.id for hive in hives]

    today = datetime.now(timezone.utc)
    recent_limit = today.date() - timedelta(days=30)
    year_start = date(today.year, 1, 1)

    visits_by_hive: dict[UUID, models.VisiteRuche] = {}
    visited_this_year: set[UUID] = set()
    last_visit_date: date | None = None
    drafts_count = 0
    if hive_ids:
        visits = (
            db.query(models.VisiteRuche)
            .filter(models.VisiteRuche.ruche_id.in_(hive_ids))
            .order_by(models.VisiteRuche.date_visite.asc())
            .all()
        )
        for visit in visits:
            visits_by_hive[visit.ruche_id] = visit
            if visit.statut_validation == "brouillon":
                drafts_count += 1
            visit_date = _as_date(visit.date_visite)
            if visit_date is not None and visit_date >= year_start:
                visited_this_year.add(visit.ruche_id)
            if visit_date is not None and (last_visit_date is None or visit_date > last_visit_date):
                last_visit_date = visit_date

    active_queens = (
        db.query(models.Reine)
        .filter(models.Reine.ruche_id.in_(hive_ids), models.Reine.statut == "active")
        .all()
        if hive_ids else []
    )
    queen_ages = [(today - queen.date_mise_en_place).days / 365.25 for queen in active_queens]

    rucher_names = {
        rucher.id: rucher.nom
        for rucher in db.query(models.Rucher).filter(models.Rucher.user_id == current_user.id).all()
    }

    frame_counts: list[int] = []
    brood_ratios: list[float] = []
    a_surveiller: list[schemas.RucheASurveiller] = []
    watch = watch_reasons(db, hives, today)
    sans_visite_recente = 0
    visitees_annee = 0
    occupancy: list[float] = []

    for hive in hives:
        visit = visits_by_hive.get(hive.id)
        visit_date = _as_date(visit.date_visite) if visit is not None else None
        # Les ruches a l'Atelier ne sont pas visitables : les compter faussait
        # la couverture des visites (taux negatif sur le tableau de bord).
        if not hive.is_at_atelier:
            if visit_date is None or visit_date < recent_limit:
                sans_visite_recente += 1
            if hive.id in visited_this_year:
                visitees_annee += 1

        # La derniere visite fait foi; a defaut, le nombre saisi a la creation.
        frames_total = None
        if visit is not None and visit.nombre_cadres_total:
            frames_total = visit.nombre_cadres_total
        elif hive.nombre_cadres:
            frames_total = hive.nombre_cadres

        if frames_total:
            frame_counts.append(frames_total)
            # Occupation rapportee a la capacite du corps : une ruchette pleine
            # (6/6) vaut une Dadant pleine (10/10). Hors Atelier : pas de colonie.
            if not hive.is_at_atelier:
                occupancy.append(min(frames_total / default_frame_count(hive.format_ruche), 1.0))
            if visit is not None and visit.nombre_cadres_couvain is not None:
                brood_ratios.append(min(visit.nombre_cadres_couvain / frames_total, 1.0))

        motifs = watch.get(hive.id, [])
        if motifs:
            a_surveiller.append(
                schemas.RucheASurveiller(
                    ruche_id=hive.id,
                    identifiant_personnalise=hive.identifiant_personnalise,
                    rucher_nom=rucher_names.get(hive.rucher_id) if hive.rucher_id else "Atelier",
                    motifs=motifs,
                )
            )

    return schemas.StatistiquesCheptelResponse(
        ruchers_actifs=len({hive.rucher_id for hive in hives if hive.rucher_id is not None}),
        ruches_suivies=sum(1 for hive in hives if not hive.is_at_atelier),
        ruches_atelier=sum(1 for hive in hives if hive.is_at_atelier),
        derniere_visite=last_visit_date,
        ruches_sans_visite_recente=sans_visite_recente,
        ruches_visitees_annee=visitees_annee,
        visites_a_valider=drafts_count,
        reines_actives=len(active_queens),
        reines_plus_2_ans=sum(1 for age in queen_ages if age >= 2),
        age_moyen_reines=round(sum(queen_ages) / len(queen_ages), 2) if queen_ages else None,
        cadres_moyens_par_ruche=round(sum(frame_counts) / len(frame_counts), 1) if frame_counts else None,
        taux_occupation_cadres=round(sum(occupancy) / len(occupancy), 3) if occupancy else None,
        taux_couvain_moyen=round(sum(brood_ratios) / len(brood_ratios), 3) if brood_ratios else None,
        ruches_a_surveiller=sorted(a_surveiller, key=lambda item: item.identifiant_personnalise),
    )


@router.get("/visites-par-mois", response_model=schemas.VisitesParMoisResponse)
def get_monthly_visits(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Nombre de visites ruche par mois de l annee civile en cours."""
    today = datetime.now(timezone.utc).date()
    season_start_year = today.year
    season_start = date(season_start_year, 1, 1)
    hives = _scope_hives(db, current_user.id, None, None)
    hive_ids = [hive.id for hive in hives]

    counts: dict[str, int] = {}
    if hive_ids:
        rows = (
            db.query(models.VisiteRuche.date_visite, func.count(models.VisiteRuche.id))
            .filter(
                models.VisiteRuche.ruche_id.in_(hive_ids),
                models.VisiteRuche.date_visite >= season_start,
            )
            .group_by(models.VisiteRuche.date_visite)
            .all()
        )
        for visit_date, count in rows:
            month = _as_date(visit_date).strftime("%Y-%m")
            counts[month] = counts.get(month, 0) + count

    months: list[schemas.VisitesParMoisPoint] = []
    current_year, current_month = season_start_year, 1
    while current_month <= 12:
        month = f"{current_year}-{current_month:02d}"
        months.append(schemas.VisitesParMoisPoint(month=month, count=counts.get(month, 0)))
        current_month += 1

    return schemas.VisitesParMoisResponse(season_start_year=season_start_year, months=months)


@router.get("/tableau-de-bord", response_model=schemas.StatistiquesTableauBordResponse)
def get_statistics_dashboard(
    year: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    rucher_id: UUID | None = None,
    ruche_id: UUID | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # La fenetre choisie dans Statistiques (start_date/end_date) prime ; a
    # defaut, l'annee civile demandee ou en cours (saison = annee civile).
    selected_year = year or (end_date.year if end_date else _apiculture_year())
    period_start = start_date or date(selected_year, 1, 1)
    period_end = end_date or date(selected_year, 12, 31)
    if period_start > period_end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La date de debut doit preceder la date de fin")
    period_end_exclusive = datetime.combine(period_end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    period_start_dt = datetime.combine(period_start, datetime.min.time(), tzinfo=timezone.utc)
    _owned_scope(db, current_user.id, rucher_id, ruche_id)
    hives = _scope_hives(db, current_user.id, rucher_id, ruche_id)
    hive_ids = [hive.id for hive in hives]
    history_hive_ids = [hive.id for hive in _scope_hives(db, current_user.id, rucher_id, ruche_id, include_archived=True)]
    current_hive_ids = {hive.id for hive in hives if not hive.is_at_atelier and hive.rucher_id is not None}
    status_labels = {
        option.id: option.libelle
        for option in db.query(models.RefStatutRuche).filter(
            (models.RefStatutRuche.is_system.is_(True)) | (models.RefStatutRuche.user_id == current_user.id)
        ).all()
    }
    type_labels = {
        option.id: option.libelle
        for option in db.query(models.RefTypeRuche).filter(
            (models.RefTypeRuche.is_system.is_(True)) | (models.RefTypeRuche.user_id == current_user.id)
        ).all()
    }

    type_distribution: dict[str, int] = {}
    for hive in hives:
        label = type_labels.get(hive.ref_type_ruche_id, "Type non renseigne")
        type_distribution[label] = type_distribution.get(label, 0) + 1

    rucher_distribution: dict[str, int] = {}
    for hive in hives:
        label = "Atelier"
        if hive.rucher_id is not None:
            rucher = db.get(models.Rucher, hive.rucher_id)
            label = rucher.nom if rucher is not None else "Rucher inconnu"
        rucher_distribution[label] = rucher_distribution.get(label, 0) + 1

    visits = []
    if history_hive_ids:
        visits = (
            db.query(models.VisiteRuche)
            .filter(
                models.VisiteRuche.ruche_id.in_(history_hive_ids),
                models.VisiteRuche.date_visite >= period_start_dt,
                models.VisiteRuche.date_visite < period_end_exclusive,
            )
            .all()
        )
    honey = (
        db.query(func.coalesce(func.sum(models.Recolte.poids_miel_kg), 0), func.count(models.Recolte.id))
        .filter(
            models.Recolte.ruche_id.in_(history_hive_ids) if history_hive_ids else False,
            models.Recolte.date_recolte >= period_start_dt,
            models.Recolte.date_recolte < period_end_exclusive,
        )
        .one()
    )

    active_queens = (
        db.query(models.Reine)
        .filter(models.Reine.ruche_id.in_(hive_ids), models.Reine.statut == "active")
        .all()
        if hive_ids else []
    )
    today = datetime.now(timezone.utc)
    queen_ages = [(today - queen.date_mise_en_place).days / 365.25 for queen in active_queens]
    frame_years = (
        db.query(models.GestionCadres.annee_cire, func.sum(models.GestionCadres.quantite))
        .filter(models.GestionCadres.ruche_id.in_(hive_ids), models.GestionCadres.annee_cire.is_not(None))
        .group_by(models.GestionCadres.annee_cire)
        .all()
        if hive_ids else []
    )
    frame_age_weighted_total = sum(
        (selected_year - int(year)) * int(quantity)
        for year, quantity in frame_years
        if int(year) <= selected_year
    )
    frame_count_with_age = sum(
        int(quantity) for year, quantity in frame_years if int(year) <= selected_year
    )

    material_rows = db.query(models.MaterielAtelier, models.RefTypeMateriel.libelle).outerjoin(
        models.RefTypeMateriel, models.MaterielAtelier.ref_type_materiel_id == models.RefTypeMateriel.id
    ).filter(models.MaterielAtelier.user_id == current_user.id).all()
    # Une colonie ne se monte qu avec des pieces du meme format: agreger tous
    # formats confondus surestimerait fortement les capacites.
    atelier_by_format: dict[str | None, dict[str, int]] = {}
    for row, label in material_rows:
        key = (label or "").strip().lower()
        bucket = atelier_by_format.setdefault(row.format_materiel, {})
        bucket[key] = bucket.get(key, 0) + (row.quantite_atelier or 0)

    potential_by_format = {
        (format_materiel or "non renseigne"): min(
            bucket.get("corps", 0), bucket.get("plancher", 0), bucket.get("toit", 0)
        )
        for format_materiel, bucket in atelier_by_format.items()
    }
    potential_new_colonies = sum(potential_by_format.values())

    dead_count = 0
    for hive in hives:
        label = status_labels.get(hive.ref_statut_ruche_id, "")
        if "mort" in label.lower() or "morte" in label.lower():
            dead_count += 1

    return schemas.StatistiquesTableauBordResponse(
        year=selected_year,
        start_date=period_start,
        end_date=period_end,
        total_ruches=len(hives),
        ruches_actives=len(current_hive_ids),
        ruches_atelier=sum(1 for hive in hives if hive.is_at_atelier),
        ruchers_count=len({hive.rucher_id for hive in hives if hive.rucher_id is not None}),
        mortalite_percent=round(dead_count / len(hives) * 100, 1) if hives else 0,
        miel_total_kg=float(honey[0] or 0),
        recoltes_count=int(honey[1] or 0),
        visites_count=len(visits),
        reines_actives=len(active_queens),
        age_moyen_reines=round(sum(queen_ages) / len(queen_ages), 2) if queen_ages else None,
        reines_agees_count=sum(1 for age in queen_ages if age >= 2),
        age_moyen_cadres=round(frame_age_weighted_total / frame_count_with_age, 2) if frame_count_with_age else None,
        cadres_anciens_count=sum(int(quantity) for year, quantity in frame_years if selected_year - int(year) >= 3),
        potential_new_colonies=int(potential_new_colonies),
        potential_new_colonies_par_format={k: int(v) for k, v in potential_by_format.items()},
        type_distribution=type_distribution,
        rucher_distribution=rucher_distribution,
    )


def _period_bounds(start_date: date | None, end_date: date | None) -> tuple[datetime, datetime]:
    """Fenetre [debut, fin + 1 jour[ ; par defaut, la saison (annee civile) en cours."""
    year = (end_date or datetime.now(timezone.utc).date()).year
    start = start_date or date(year, 1, 1)
    end = end_date or date(year, 12, 31)
    if start > end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La date de debut doit preceder la date de fin")
    return (
        datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
        datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc),
    )


@router.get("/fiche-ruche", response_model=schemas.FicheRucheResponse)
def get_fiche_ruche(
    ruche_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tout ce qu'il faut pour la fiche ruche des Statistiques, en un appel."""
    ruche = get_owned_ruche(db, ruche_id, current_user.id)
    period_start, period_end = _period_bounds(start_date, end_date)
    now = datetime.now(timezone.utc)

    queens = (
        db.query(models.Reine)
        .filter(models.Reine.ruche_id == ruche.id)
        .order_by(models.Reine.date_mise_en_place.desc())
        .all()
    )
    active_queen = next((queen for queen in queens if queen.statut == "active"), None)
    visits = (
        db.query(models.VisiteRuche)
        .filter(models.VisiteRuche.ruche_id == ruche.id, models.VisiteRuche.date_visite >= period_start, models.VisiteRuche.date_visite < period_end)
        .order_by(models.VisiteRuche.date_visite.asc())
        .all()
    )
    last_visit = (
        db.query(func.max(models.VisiteRuche.date_visite)).filter(models.VisiteRuche.ruche_id == ruche.id).scalar()
    )
    frame_rows = (
        db.query(models.GestionCadres, models.RefActionCadre.libelle, models.VisiteRuche.date_visite)
        .outerjoin(models.RefActionCadre, models.GestionCadres.ref_action_cadre_id == models.RefActionCadre.id)
        .outerjoin(models.VisiteRuche, models.GestionCadres.visite_ruche_id == models.VisiteRuche.id)
        .filter(models.GestionCadres.ruche_id == ruche.id)
        .all()
    )
    movements = [
        schemas.FicheMouvementCadre(date=visit_date, action=label, quantite=row.quantite, annee_cire=row.annee_cire)
        for row, label, visit_date in frame_rows
        if visit_date is None or period_start <= visit_date < period_end
    ]
    movements.sort(key=lambda item: item.date or now)
    wax_years = [(row.annee_cire, row.quantite) for row, _, _ in frame_rows if row.annee_cire]
    frames_with_age = sum(quantity for _, quantity in wax_years)
    harvests = (
        db.query(models.Recolte)
        .filter(models.Recolte.ruche_id == ruche.id, models.Recolte.date_recolte >= period_start, models.Recolte.date_recolte < period_end)
        .order_by(models.Recolte.date_recolte.asc())
        .all()
    )
    transvasements = (
        db.query(models.RucheTransvasement)
        .filter(models.RucheTransvasement.ruche_id == ruche.id)
        .order_by(models.RucheTransvasement.date_transvasement.desc())
        .all()
    )
    rucher = db.get(models.Rucher, ruche.rucher_id) if ruche.rucher_id else None
    return schemas.FicheRucheResponse(
        ruche=schemas.RucheResponse.model_validate(ruche),
        rucher_nom=rucher.nom if rucher is not None else ("Atelier" if ruche.is_at_atelier else None),
        reine_active=active_queen,
        age_reine=round((now - active_queen.date_mise_en_place).days / 365.25, 1) if active_queen is not None else None,
        reines=queens,
        materiel=hive_elements(db, ruche),
        visites=[schemas.FicheVisite.model_validate(visit, from_attributes=True) for visit in visits],
        derniere_visite=last_visit,
        mouvements_cadres=movements,
        age_moyen_cadres=round(sum((now.year - year) * quantity for year, quantity in wax_years) / frames_with_age, 1) if frames_with_age else None,
        recoltes=[schemas.FicheRecolte(date_recolte=harvest.date_recolte, poids_miel_kg=float(harvest.poids_miel_kg)) for harvest in harvests],
        miel_total_kg=round(sum(float(harvest.poids_miel_kg) for harvest in harvests), 2),
        transvasements=transvasements,
        surveillance=watch_reasons(db, [ruche]).get(ruche.id, []),
    )


@router.get("/fiche-rucher", response_model=schemas.FicheRucherResponse)
def get_fiche_rucher(
    rucher_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Synthese d'un rucher : effectifs, reines, visites, couvain, miel de chaque ruche."""
    rucher = get_owned_rucher(db, rucher_id, current_user.id)
    period_start, period_end = _period_bounds(start_date, end_date)
    now = datetime.now(timezone.utc)
    hives = (
        db.query(models.Ruche)
        .filter(models.Ruche.rucher_id == rucher.id, models.Ruche.archived_at.is_(None), models.Ruche.is_at_atelier.is_(False))
        .order_by(models.Ruche.identifiant_personnalise.asc())
        .all()
    )
    hive_ids = [hive.id for hive in hives]
    type_labels = {option.id: option.libelle for option in db.query(models.RefTypeRuche).all()}
    par_format: dict[str, int] = {}
    par_type: dict[str, int] = {}
    for hive in hives:
        format_label = hive.format_ruche or "non renseigne"
        par_format[format_label] = par_format.get(format_label, 0) + 1
        type_label = type_labels.get(hive.ref_type_ruche_id, "Type non renseigne")
        par_type[type_label] = par_type.get(type_label, 0) + 1

    queens = (
        db.query(models.Reine).filter(models.Reine.ruche_id.in_(hive_ids), models.Reine.statut == "active").all()
        if hive_ids else []
    )
    queen_ages = [(now - queen.date_mise_en_place).days / 365.25 for queen in queens]
    visits = (
        db.query(models.VisiteRuche)
        .filter(models.VisiteRuche.ruche_id.in_(hive_ids), models.VisiteRuche.date_visite >= period_start, models.VisiteRuche.date_visite < period_end)
        .order_by(models.VisiteRuche.date_visite.asc())
        .all()
        if hive_ids else []
    )
    last_by_hive: dict[UUID, models.VisiteRuche] = {}
    for visit in visits:
        last_by_hive[visit.ruche_id] = visit
    frames_by_hive = {hive.id: hive.nombre_cadres for hive in hives}
    brood = [
        min(visit.nombre_cadres_couvain / (visit.nombre_cadres_total or frames_by_hive[visit.ruche_id]), 1.0)
        for visit in last_by_hive.values()
        if visit.nombre_cadres_couvain is not None and (visit.nombre_cadres_total or frames_by_hive[visit.ruche_id])
    ]
    notes = [visit.note_ruche for visit in visits if visit.note_ruche is not None]
    honey_rows = dict(
        db.query(models.Recolte.ruche_id, func.coalesce(func.sum(models.Recolte.poids_miel_kg), 0))
        .filter(models.Recolte.ruche_id.in_(hive_ids), models.Recolte.date_recolte >= period_start, models.Recolte.date_recolte < period_end)
        .group_by(models.Recolte.ruche_id)
        .all()
        if hive_ids else []
    )
    # Toutes les ruches, y compris celles sans recolte : une faible productrice
    # doit se voir pour que l'apiculteur agisse.
    honey_per_hive = sorted(
        (
            schemas.MielParRuche(ruche_id=hive.id, identifiant_personnalise=hive.identifiant_personnalise, poids_total_kg=round(float(honey_rows.get(hive.id, 0)), 2))
            for hive in hives
        ),
        key=lambda item: (-item.poids_total_kg, item.identifiant_personnalise),
    )
    watch = watch_reasons(db, hives)
    return schemas.FicheRucherResponse(
        rucher_id=rucher.id,
        nom=rucher.nom,
        type_terrain=rucher.type_terrain,
        ruches_actives=len(hives),
        par_format=par_format,
        par_type=par_type,
        reines_actives=len(queens),
        age_moyen_reines=round(sum(queen_ages) / len(queen_ages), 1) if queen_ages else None,
        reines_plus_2_ans=sum(1 for age in queen_ages if age >= 2),
        visites_periode=len(visits),
        ruches_visitees_periode=len(last_by_hive),
        note_moyenne=round(sum(notes) / len(notes), 1) if notes else None,
        couvain_moyen=round(sum(brood) / len(brood), 3) if brood else None,
        miel_total_kg=round(sum(item.poids_total_kg for item in honey_per_hive), 2),
        miel_par_ruche=honey_per_hive,
        surveillance=[
            schemas.RucheASurveiller(ruche_id=hive.id, identifiant_personnalise=hive.identifiant_personnalise, rucher_nom=rucher.nom, motifs=watch[hive.id])
            for hive in hives if hive.id in watch
        ],
    )
