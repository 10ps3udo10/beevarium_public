from datetime import date, datetime
from typing import Annotated, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    prenom: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=12, max_length=255)
    is_premium: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "toi@example.com",
                    "prenom": "Paul",
                    "password": "motdepasse123",
                    "is_premium": False,
                }
            ]
        }
    )


class UserResponse(UserBase):
    id: UUID
    auth_provider: str
    is_premium: bool
    created_at: datetime
    tag_favorites: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    prenom: Optional[str] = Field(default=None, max_length=100)
    tag_favorites: Optional[list[str]] = Field(default=None, max_length=40)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=255)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "toi@example.com",
                    "password": "motdepasse123",
                }
            ]
        }
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LogoutResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "toi@example.com"}]}
    )


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=255)
    password: str = Field(min_length=12, max_length=255)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "token": "jeton-recu-par-email",
                    "password": "nouveaumotdepasse123",
                }
            ]
        }
    )


class MessageResponse(BaseModel):
    message: str
    debug_reset_url: Optional[str] = None


class BetaFeedbackCreate(BaseModel):
    category: str = Field(pattern="^(bug|idee|question|autre)$")
    message: str = Field(min_length=10, max_length=4000)
    context: Optional[str] = Field(default=None, max_length=255)


class BetaFeedbackResponse(BaseModel):
    id: UUID
    category: str
    message: str
    context: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReferenceOptionBase(BaseModel):
    libelle: str = Field(min_length=1, max_length=50)


class ReferenceOptionCreate(ReferenceOptionBase):
    pass


class ReferenceOptionUpdate(ReferenceOptionBase):
    pass


class ReferenceOptionResponse(ReferenceOptionBase):
    id: UUID
    user_id: Optional[UUID] = None
    is_system: bool

    model_config = ConfigDict(from_attributes=True)


class RucherBase(BaseModel):
    nom: str = Field(min_length=1, max_length=150)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    type_terrain: Optional[str] = Field(default=None, max_length=50)
    statut_activite: str = Field(default="actif", max_length=20)
    statut_peuplement: str = Field(default="peuple", max_length=20)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nom": "Rucher Maison",
                    "latitude": 45.123456,
                    "longitude": 3.123456,
                    "type_terrain": "plaine",
                    "statut_activite": "actif",
                    "statut_peuplement": "peuple",
                }
            ]
        }
    )


class RucherCreate(RucherBase):
    pass


class RucherUpdate(RucherBase):
    pass


class RucherResponse(RucherBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VisiteRucherBase(BaseModel):
    rucher_id: UUID
    note_meteo: Optional[str] = Field(default=None, max_length=100)
    impression_generale: Optional[str] = None
    note_globale: Optional[int] = Field(default=None, ge=1, le=5)


class VisiteRucherCreate(VisiteRucherBase):
    pass


class VisiteRucherUpdate(VisiteRucherBase):
    pass


class VisiteRucherResponse(VisiteRucherBase):
    id: UUID
    date_visite: datetime

    model_config = ConfigDict(from_attributes=True)


class RucheBase(BaseModel):
    identifiant_personnalise: str = Field(min_length=1, max_length=100)
    rucher_id: Optional[UUID] = None
    is_at_atelier: bool = False
    ref_type_ruche_id: Optional[UUID] = None
    ref_statut_ruche_id: Optional[UUID] = None
    reine_annee_marquage: Optional[int] = Field(default=None, ge=1900, le=2100)
    # Jour J de mise en place de la reine active : l'age se compte depuis ce
    # jour. Sans date, la reine de l'annee en cours est datee du jour de saisie.
    reine_date_mise_en_place: Optional[date] = None
    reine_race: Optional[str] = Field(default=None, max_length=100)
    reine_provenance: Optional[str] = Field(default=None, max_length=150)
    nombre_cadres: Optional[int] = Field(default=None, ge=0, le=100)
    format_ruche: Optional[str] = Field(default=None, max_length=30)
    atelier_id: Optional[UUID] = None
    has_corps: bool = True
    has_hausse: bool = False
    has_partition: bool = False
    has_grille_a_reine: bool = False
    has_nourrisseur: bool = False
    has_toit: bool = True
    has_plancher: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "identifiant_personnalise": "R1",
                    "rucher_id": "7b4e5e4f-1f6b-4c9b-8f60-3af6d7bbf7f1",
                    "is_at_atelier": False,
                    "reine_annee_marquage": 2026,
                    "reine_race": "Buckfast",
                    "reine_provenance": "Elevage local",
                }
            ]
        }
    )


MaterielElement = Literal["plancher", "corps", "couvre_cadre", "toit", "partition", "grille", "nourrisseur", "cadres"]


class RucheCreate(RucheBase):
    # `achat` : materiel neuf (le stock range ne bouge pas). `stock` : les
    # elements choisis sont retires du stock range de l'Atelier, au format de
    # la ruche ; refus 409 si une quantite manque.
    origine_materiel: Literal["achat", "stock"] = "achat"
    elements_stock: Optional[list[MaterielElement]] = None


class RucheUpdate(RucheBase):
    pass


class RucheTagCreate(BaseModel):
    libelle: str = Field(min_length=1, max_length=50)


class RucheTagResponse(BaseModel):
    id: UUID
    ruche_id: UUID
    libelle: str
    source: str
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RucheResponse(RucheBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    archived_at: Optional[datetime] = None
    motif_archive: Optional[str] = None
    tags: list[RucheTagResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RucheDemontageRequest(BaseModel):
    ruche_ids: list[UUID] = Field(min_length=1)
    # Elements remis dans le stock range ; par defaut tous ceux de la ruche.
    elements_stock: Optional[list[Literal["plancher", "corps", "couvre_cadre", "toit", "partition", "grille", "nourrisseur", "cadres", "hausses"]]] = None


class RucheDemontageResponse(BaseModel):
    demontees: int


class TransvasementCreate(BaseModel):
    format_apres: str = Field(min_length=1, max_length=30)
    provenance: Literal["stock", "achat", "ruche_atelier"]
    ruche_atelier_id: Optional[UUID] = None
    # Elements du nouveau contenant (ignores pour une ruche preparee : ce sont les siens).
    elements: list[Literal["plancher", "corps", "couvre_cadre", "toit", "partition", "grille", "nourrisseur"]] = Field(
        default_factory=lambda: ["plancher", "corps", "toit"]
    )
    cadres_transferes: int = Field(ge=0, le=100)
    cadres_ajoutes: int = Field(default=0, ge=0, le=100)
    annee_cire: Optional[int] = Field(default=None, ge=1900, le=2100)
    nouvel_identifiant: Optional[str] = Field(default=None, min_length=1, max_length=100)


class TransvasementResponse(BaseModel):
    id: UUID
    ruche_id: UUID
    visite_ruche_id: Optional[UUID] = None
    date_transvasement: datetime
    format_avant: Optional[str] = None
    format_apres: Optional[str] = None
    provenance: str
    ruche_atelier_id: Optional[UUID] = None
    cadres_transferes: int
    cadres_ajoutes: int
    identifiant_avant: Optional[str] = None
    identifiant_apres: Optional[str] = None
    tag_suggestions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AtelierResponse(BaseModel):
    id: UUID
    nom: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReineCreate(BaseModel):
    date_mise_en_place: datetime
    origine: str = Field(default="inconnue", pattern="^(essaimage|remerage|apport_reine_fecondee|apport_reine_vierge|cellule_royale|inconnue)$")
    race: Optional[str] = Field(default=None, max_length=100)
    provenance: Optional[str] = Field(default=None, max_length=150)


class ReineResponse(ReineCreate):
    id: UUID
    ruche_id: UUID
    statut: str
    date_fin: Optional[datetime] = None
    motif_fin: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RucheMoveRequest(BaseModel):
    ruche_ids: list[UUID] = Field(min_length=1)
    target_rucher_id: Optional[UUID] = None
    move_to_atelier: bool = False


class RucheMoveResponse(BaseModel):
    moved_count: int
    target_rucher_id: Optional[UUID] = None
    move_to_atelier: bool


class InterventionSanitaireCreate(BaseModel):
    ref_type_intervention_id: UUID
    details: Optional[str] = None


class InterventionSanitaireResponse(InterventionSanitaireCreate):
    id: UUID
    ruche_id: UUID
    visite_ruche_id: Optional[UUID] = None
    date_action: datetime

    model_config = ConfigDict(from_attributes=True)


class GestionCadresCreate(BaseModel):
    ref_action_cadre_id: UUID
    quantite: int = Field(ge=1)
    annee_cire: Optional[int] = Field(default=None, ge=1900, le=2100)


class GestionCadresResponse(GestionCadresCreate):
    id: UUID
    ruche_id: UUID
    visite_ruche_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class MouvementHausseCreate(BaseModel):
    quantite_delta: int = Field(ne=0)
    note: Optional[str] = None


class MouvementHausseResponse(MouvementHausseCreate):
    id: UUID
    ruche_id: UUID
    visite_ruche_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class ActionVisiteResponse(BaseModel):
    id: UUID
    libelle: str

    model_config = ConfigDict(from_attributes=True)


class VisiteRucheBase(BaseModel):
    ruche_id: UUID
    visite_rucher_id: Optional[UUID] = None
    reine_id: Optional[UUID] = None
    reine_vue: Optional[bool] = None
    presence_ponte: Optional[bool] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "rucher_id": "7b4e5e4f-1f6b-4c9b-8f60-3af6d7bbf7f1",
                    "note_meteo": "ensoleille",
                    "impression_generale": "Belle activite",
                    "note_globale": 4,
                }
            ]
        }
    )
    etat_couvain: Optional[str] = Field(default=None, pattern="^(faible|normal|excellent)$")
    nombre_cadres_couvain: Optional[int] = Field(default=None, ge=0)
    reserves_nourriture: Optional[str] = Field(default=None, pattern="^(critique|correct|abondant)$")
    agressivite: Optional[int] = Field(default=None, ge=1, le=5)
    note_ruche: Optional[int] = Field(default=None, ge=1, le=5)
    nombre_cadres_total: Optional[int] = Field(default=None, ge=0)
    corps_present: Optional[bool] = None
    hausse_presente: Optional[bool] = None
    grille_a_reine_presente: Optional[bool] = None
    nourrisseur_present: Optional[bool] = None
    toit_present: Optional[bool] = None
    plancher_present: Optional[bool] = None
    partition_presente: Optional[bool] = None
    source_saisie: str = Field(default="manuelle", pattern="^(manuelle|ia_vocale)$")
    statut_validation: str = Field(default="valide", pattern="^(brouillon|valide)$")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ruche_id": "7b4e5e4f-1f6b-4c9b-8f60-3af6d7bbf7f1",
                    "visite_rucher_id": None,
                    "reine_vue": True,
                    "presence_ponte": True,
                    "etat_couvain": "normal",
                    "nombre_cadres_couvain": 4,
                    "reserves_nourriture": "correct",
                    "agressivite": 2,
                    "note_ruche": 4,
                    "nombre_cadres_total": 10,
                    "source_saisie": "manuelle",
                    "statut_validation": "valide",
                }
            ]
        }
    )


class VisiteRucheCreate(VisiteRucheBase):
    # Heure de saisie (visite hors ligne) ; a defaut, heure d'enregistrement.
    date_visite: Optional[datetime] = None
    transvasement: Optional[TransvasementCreate] = None
    # Type de ruche constate a la visite (essaim devenu production...) :
    # applique a la ruche avec la visite, donc aussi hors ligne.
    ref_type_ruche_id: Optional[UUID] = None
    action_ids: list[UUID] = Field(default_factory=list)
    # Tags choisis hors ligne pendant la visite, poses a la synchronisation.
    tags_ajoutes: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(default_factory=list, max_length=20)
    interventions: list[InterventionSanitaireCreate] = Field(default_factory=list)
    mouvements_cadres: list[GestionCadresCreate] = Field(default_factory=list)
    mouvements_hausses: list[MouvementHausseCreate] = Field(default_factory=list)


class VisiteRucheUpdate(VisiteRucheBase):
    action_ids: list[UUID] = Field(default_factory=list)
    interventions: list[InterventionSanitaireCreate] = Field(default_factory=list)
    mouvements_cadres: list[GestionCadresCreate] = Field(default_factory=list)
    mouvements_hausses: list[MouvementHausseCreate] = Field(default_factory=list)


class VisiteRuchePatch(BaseModel):
    ruche_id: Optional[UUID] = None
    visite_rucher_id: Optional[UUID] = None
    reine_vue: Optional[bool] = None
    presence_ponte: Optional[bool] = None
    etat_couvain: Optional[str] = Field(default=None, pattern="^(faible|normal|excellent)$")
    nombre_cadres_couvain: Optional[int] = Field(default=None, ge=0)
    reserves_nourriture: Optional[str] = Field(default=None, pattern="^(critique|correct|abondant)$")
    agressivite: Optional[int] = Field(default=None, ge=1, le=5)
    note_ruche: Optional[int] = Field(default=None, ge=1, le=5)
    nombre_cadres_total: Optional[int] = Field(default=None, ge=0)
    corps_present: Optional[bool] = None
    hausse_presente: Optional[bool] = None
    grille_a_reine_presente: Optional[bool] = None
    nourrisseur_present: Optional[bool] = None
    toit_present: Optional[bool] = None
    plancher_present: Optional[bool] = None
    partition_presente: Optional[bool] = None
    source_saisie: Optional[str] = Field(default=None, pattern="^(manuelle|ia_vocale)$")
    statut_validation: Optional[str] = Field(default=None, pattern="^(brouillon|valide)$")
    action_ids: Optional[list[UUID]] = None
    interventions: Optional[list[InterventionSanitaireCreate]] = None
    mouvements_cadres: Optional[list[GestionCadresCreate]] = None
    mouvements_hausses: Optional[list[MouvementHausseCreate]] = None


class VisiteRucheResponse(BaseModel):
    id: UUID
    ruche_id: UUID
    visite_rucher_id: Optional[UUID] = None
    reine_id: Optional[UUID] = None
    date_visite: datetime
    updated_at: Optional[datetime] = None
    reine_vue: Optional[bool] = None
    presence_ponte: Optional[bool] = None
    etat_couvain: Optional[str] = None
    nombre_cadres_couvain: Optional[int] = None
    reserves_nourriture: Optional[str] = None
    agressivite: Optional[int] = None
    note_ruche: Optional[int] = None
    nombre_cadres_total: Optional[int] = None
    corps_present: Optional[bool] = None
    hausse_presente: Optional[bool] = None
    partition_presente: Optional[bool] = None
    grille_a_reine_presente: Optional[bool] = None
    nourrisseur_present: Optional[bool] = None
    toit_present: Optional[bool] = None
    plancher_present: Optional[bool] = None
    source_saisie: str
    statut_validation: str
    actions: list[ActionVisiteResponse] = Field(default_factory=list)
    interventions: list[InterventionSanitaireResponse] = Field(default_factory=list)
    mouvements_cadres: list[GestionCadresResponse] = Field(default_factory=list)
    mouvements_hausses: list[MouvementHausseResponse] = Field(default_factory=list)
    tag_suggestions: list[str] = Field(default_factory=list)
    tag_removal_suggestions: list[str] = Field(default_factory=list)
    # Effets annexes non appliques (ex. transvasement refuse faute de stock).
    avertissements: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class VisiteHistoriqueItem(BaseModel):
    id: UUID
    ruche_id: UUID
    rucher_label: str
    ruche_label: str
    date_visite: datetime
    type_evenement: str = "visite"
    note_ruche: Optional[int] = None
    poids_miel_kg: Optional[float] = None
    source_saisie: str
    statut_validation: str


class VisiteHistoriqueResponse(BaseModel):
    total: int
    visits: list[VisiteHistoriqueItem]


class VisiteSynthesePeriodeResponse(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    ruche_id: Optional[UUID] = None
    rucher_id: Optional[UUID] = None
    total_visites_ruche: int
    total_visites_rucher: int
    visites_manuelles: int
    visites_ia_vocale: int
    brouillons_ia: int
    note_ruche_moyenne: Optional[float] = None
    note_rucher_moyenne: Optional[float] = None
    taux_reine_vue: Optional[float] = None


class VisiteSyntheseAvanceePeriode(BaseModel):
    start_date: date
    end_date: date
    total_visites: int
    note_moyenne: Optional[float] = None
    taux_reine_vue: Optional[float] = None
    taux_couvain: Optional[float] = None
    cadres_total_moyens: Optional[float] = None
    cadres_couvain_moyens: Optional[float] = None
    taux_cadres_couvain: Optional[float] = None


class RucheSansVisiteResponse(BaseModel):
    ruche_id: UUID
    identifiant_personnalise: str
    rucher_nom: Optional[str] = None
    derniere_visite: Optional[datetime] = None
    jours_depuis_visite: Optional[int] = None


class VisiteSyntheseAvanceeResponse(BaseModel):
    window_days: int
    current: VisiteSyntheseAvanceePeriode
    previous: VisiteSyntheseAvanceePeriode
    note_delta: Optional[float] = None
    visites_delta: Optional[int] = None
    reine_delta: Optional[float] = None
    couvain_delta: Optional[float] = None
    uncovered_hives: list[RucheSansVisiteResponse] = Field(default_factory=list)


class RecolteBase(BaseModel):
    ruche_id: UUID
    visite_ruche_id: Optional[UUID] = None
    poids_miel_kg: float = Field(ge=0)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ruche_id": "7b4e5e4f-1f6b-4c9b-8f60-3af6d7bbf7f1",
                    "visite_ruche_id": "8c5a7a54-3ca8-4b44-9a72-03f5139b11b3",
                    "poids_miel_kg": 18.5,
                }
            ]
        }
    )


class RecolteCreate(RecolteBase):
    pass


class RecolteUpdate(RecolteBase):
    pass


class RecolteResponse(RecolteBase):
    id: UUID
    date_recolte: datetime

    model_config = ConfigDict(from_attributes=True)


class RucheASurveiller(BaseModel):
    ruche_id: UUID
    identifiant_personnalise: str
    rucher_nom: Optional[str] = None
    motifs: list[str]


class FicheVisite(BaseModel):
    date_visite: datetime
    note_ruche: Optional[int] = None
    nombre_cadres_total: Optional[int] = None
    nombre_cadres_couvain: Optional[int] = None
    reine_vue: Optional[bool] = None
    presence_ponte: Optional[bool] = None


class FicheMouvementCadre(BaseModel):
    date: Optional[datetime] = None
    action: Optional[str] = None
    quantite: int
    annee_cire: Optional[int] = None


class FicheRecolte(BaseModel):
    date_recolte: datetime
    poids_miel_kg: float


class FicheRucheResponse(BaseModel):
    """Fiche ruche en lecture seule pour l'onglet Statistiques (une requete)."""
    ruche: RucheResponse
    rucher_nom: Optional[str] = None
    reine_active: Optional[ReineResponse] = None
    age_reine: Optional[float] = None
    reines: list[ReineResponse]
    materiel: dict[str, int]
    visites: list[FicheVisite]
    derniere_visite: Optional[datetime] = None
    mouvements_cadres: list[FicheMouvementCadre]
    age_moyen_cadres: Optional[float] = None
    recoltes: list[FicheRecolte]
    miel_total_kg: float
    transvasements: list[TransvasementResponse]
    surveillance: list[str]


class MielParRuche(BaseModel):
    ruche_id: UUID
    identifiant_personnalise: str
    poids_total_kg: float


class FicheRucherResponse(BaseModel):
    """Synthese d'un rucher sur la fenetre choisie (une requete)."""
    rucher_id: UUID
    nom: str
    type_terrain: Optional[str] = None
    ruches_actives: int
    par_format: dict[str, int]
    par_type: dict[str, int]
    reines_actives: int
    age_moyen_reines: Optional[float] = None
    reines_plus_2_ans: int
    visites_periode: int
    ruches_visitees_periode: int
    note_moyenne: Optional[float] = None
    couvain_moyen: Optional[float] = None
    miel_total_kg: float
    miel_par_ruche: list[MielParRuche]
    surveillance: list[RucheASurveiller]


class RecolteStatsByRuche(BaseModel):
    ruche_id: UUID
    identifiant_personnalise: str
    total_recoltes: int
    poids_total_kg: float
    poids_moyen_kg: float


class RecolteStatsByRucher(BaseModel):
    rucher_id: UUID
    nom_rucher: str
    total_recoltes: int
    poids_total_kg: float
    poids_moyen_kg: float


class RecolteStatsByYear(BaseModel):
    annee: int
    total_recoltes: int
    poids_total_kg: float
    poids_moyen_kg: float


class RecolteStatsRollingPeriod(BaseModel):
    days: int
    total_recoltes: int
    poids_total_kg: float
    poids_moyen_kg: float


class RecolteStatsSeason(BaseModel):
    saison_label: str
    season_start_year: int
    season_start_month: int
    total_recoltes: int
    poids_total_kg: float
    poids_moyen_kg: float


class StatistiquesTableauBordResponse(BaseModel):
    year: int
    # Fenetre effectivement appliquee aux visites et recoltes.
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_ruches: int
    ruches_actives: int
    ruches_atelier: int
    ruchers_count: int
    mortalite_percent: float
    miel_total_kg: float
    recoltes_count: int
    visites_count: int
    reines_actives: int
    age_moyen_reines: Optional[float] = None
    reines_agees_count: int
    age_moyen_cadres: Optional[float] = None
    cadres_anciens_count: int
    potential_new_colonies: int
    potential_new_colonies_par_format: dict[str, int] = {}
    type_distribution: dict[str, int]
    rucher_distribution: dict[str, int]


class VisitesParMoisPoint(BaseModel):
    month: str
    count: int


class VisitesParMoisResponse(BaseModel):
    season_start_year: int
    months: list[VisitesParMoisPoint]


class DerniereVisiteRuche(BaseModel):
    ruche_id: UUID
    date_visite: Optional[datetime] = None
    nombre_cadres_total: Optional[int] = None
    nombre_cadres_couvain: Optional[int] = None
    note_ruche: Optional[int] = None
    statut_validation: Optional[str] = None


class StatistiquesCheptelResponse(BaseModel):
    ruchers_actifs: int
    ruches_suivies: int
    ruches_atelier: int
    derniere_visite: Optional[date] = None
    # Ruches en rucher (hors Atelier) sans visite depuis 30 jours.
    ruches_sans_visite_recente: int
    # Ruches en rucher visitees au moins une fois depuis le 1er janvier.
    ruches_visitees_annee: int = 0
    visites_a_valider: int = 0
    reines_actives: int
    reines_plus_2_ans: int = 0
    age_moyen_reines: Optional[float] = None
    # Moyennes calculees sur la derniere visite de chaque ruche, pas sur toutes
    # les visites: sinon une ruche visitee souvent pese plus lourd que les autres.
    cadres_moyens_par_ruche: Optional[float] = None
    # Cadres occupes / capacite du corps (10 Dadant, 8 Warre, 6 ruchette), 0 a 1.
    taux_occupation_cadres: Optional[float] = None
    taux_couvain_moyen: Optional[float] = None
    ruches_a_surveiller: list[RucheASurveiller]


class RecolteStatsQuery(BaseModel):
    year: Optional[int] = Field(default=None, ge=1900, le=2100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class MaterielAtelierBase(BaseModel):
    ref_type_materiel_id: Optional[UUID] = None
    modele: Optional[str] = Field(default=None, max_length=100)
    format_materiel: Optional[str] = Field(default=None, max_length=30)
    quantite_atelier: int = Field(ge=0)
    quantite_en_service: int = Field(ge=0)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ref_type_materiel_id": "b4f5d6c7-8a9b-4cde-9f01-1234567890ab",
                    "modele": "Dadant 10",
                    "quantite_atelier": 12,
                    "quantite_en_service": 4,
                }
            ]
        }
    )


class MaterielAtelierCreate(MaterielAtelierBase):
    pass


class MaterielAtelierUpdate(MaterielAtelierBase):
    pass


class MaterielAtelierResponse(MaterielAtelierBase):
    id: UUID
    user_id: UUID
    quantite_en_service_manuelle: int
    quantite_en_service_calculee: int
    quantite_en_service_totale: int

    model_config = ConfigDict(from_attributes=True)


class MaterielStockSyntheseByType(BaseModel):
    ref_type_materiel_id: UUID
    libelle_type_materiel: str
    format_materiel: Optional[str] = None
    quantite_atelier_totale: int
    quantite_en_service_manuelle_totale: int
    quantite_en_service_calculee: int
    quantite_en_service_totale: int
    # Materiel des ruches montees et rangees a l'Atelier (ni range en vrac, ni en service).
    quantite_ruches_atelier_calculee: int = 0
    quantite_stock_totale: int


class IaVocaleAnalyseRequest(BaseModel):
    ruche_id: UUID
    transcription: str = Field(min_length=1, max_length=4000)
    visite_rucher_id: Optional[UUID] = None
    audio_reference: Optional[str] = Field(default=None, max_length=255)
    save_as_draft: bool = False


class IaVocaleAnalyseResponse(BaseModel):
    audio_reference: Optional[str] = None
    transcription: str
    statut_validation: str
    confidence: float
    missing_fields: list[str] = Field(default_factory=list)
    extracted_visit: dict[str, object]
    saved_visite: Optional[VisiteRucheResponse] = None

    model_config = ConfigDict(from_attributes=True)


class IaVocaleTranscriptionResponse(BaseModel):
    audio_reference: str
    transcription: str
    detected_language: str
    duration_seconds_estimate: float

    model_config = ConfigDict(from_attributes=True)


class ApiEventResponse(BaseModel):
    id: UUID
    request_id: str
    user_id: Optional[UUID] = None
    method: str
    path: str
    status_code: int
    duration_ms: float
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiObservabilityPath(BaseModel):
    path: str
    requests: int
    errors: int
    average_duration_ms: float


class ApiObservabilitySummary(BaseModel):
    window_events: int
    requests: int
    errors: int
    error_rate_percent: float
    average_duration_ms: float
    p95_duration_ms: float
    critical_paths: list[ApiObservabilityPath] = Field(default_factory=list)


class CadreAgeParRuche(BaseModel):
    ruche_id: UUID
    identifiant_personnalise: str
    total_cadres_declares: int
    total_cadres_avec_annee_cire: int
    age_moyen_cire: Optional[float] = None
    age_max_cire: Optional[int] = None
    cadres_plus_de_3_ans: int
    alerte_renouvellement: bool


class CadreAgeBucket(BaseModel):
    age_cire: int
    quantite: int


class CadreAgeDetailResponse(BaseModel):
    ruche_id: UUID
    identifiant_personnalise: str
    total_cadres_declares: int
    total_cadres_avec_annee_cire: int
    age_moyen_cire: Optional[float] = None
    age_max_cire: Optional[int] = None
    cadres_plus_de_3_ans: int
    alerte_renouvellement: bool
    buckets: list[CadreAgeBucket] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# --- Creation rapide, modeles de ruche et import -------------------------------

class ElementsRuche(BaseModel):
    """Elements presents dans une ruche ; le couvre-cadre suit le corps."""
    has_corps: bool = True
    has_toit: bool = True
    has_plancher: bool = True
    has_grille_a_reine: bool = False
    has_nourrisseur: bool = False
    has_hausse: bool = False
    has_partition: bool = False


class RucheRapide(ElementsRuche):
    identifiant_personnalise: str = Field(min_length=1, max_length=100)
    ref_type_ruche_id: Optional[UUID] = None
    format_ruche: Optional[str] = Field(default=None, max_length=30)
    nombre_cadres: Optional[int] = Field(default=None, ge=0, le=100)


class CreationRapideRequest(BaseModel):
    # Nouveau rucher (`rucher`) ou rucher existant (`rucher_id`), pas les deux.
    rucher: Optional[RucherCreate] = None
    rucher_id: Optional[UUID] = None
    ruches: list[RucheRapide] = Field(min_length=1, max_length=200)


class CreationRapideResponse(BaseModel):
    rucher: RucherResponse
    ruches_creees: int


class ModeleRucheCreate(ElementsRuche):
    nom: str = Field(min_length=1, max_length=80)
    ref_type_ruche_id: Optional[UUID] = None
    format_ruche: Optional[str] = Field(default=None, max_length=30)
    nombre_cadres: Optional[int] = Field(default=None, ge=0, le=100)


class ModeleRucheResponse(ModeleRucheCreate):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


ChampImport = Literal["rucher", "identifiant", "type_ruche", "format", "nombre_cadres"]


class ImportAnalyseRequest(BaseModel):
    nom_fichier: str = Field(min_length=1, max_length=255)
    contenu_base64: str = Field(min_length=1, max_length=1_200_000)
    # Colonne du fichier (en-tete) choisie pour chaque champ ; devinee si absente.
    correspondance: Optional[dict[ChampImport, Optional[str]]] = None


class LigneImport(BaseModel):
    rucher: str = Field(default="", max_length=150)
    identifiant: str = Field(default="", max_length=100)
    type_ruche: Optional[str] = Field(default=None, max_length=100)
    format_ruche: Optional[str] = Field(default=None, max_length=30)
    nombre_cadres: Optional[str] = Field(default=None, max_length=10)


class LigneImportVerifiee(LigneImport):
    numero: int
    erreurs: list[str] = Field(default_factory=list)
    rucher_existant: bool = False


class ImportVerificationRequest(BaseModel):
    lignes: list[LigneImport] = Field(min_length=1, max_length=1000)


class ImportVerificationResponse(BaseModel):
    colonnes: list[str] = Field(default_factory=list)
    correspondance: dict[str, Optional[str]] = Field(default_factory=dict)
    lignes: list[LigneImportVerifiee]
    nb_erreurs: int
    ruchers_a_creer: list[str] = Field(default_factory=list)


class ImportResultat(BaseModel):
    ruches_creees: int
    ruchers_crees: int
