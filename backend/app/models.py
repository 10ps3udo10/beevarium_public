import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    JSON,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


actions_visite = Table(
    "actions_visite",
    Base.metadata,
    Column(
        "visite_ruche_id",
        UUID(as_uuid=True),
        ForeignKey("visites_ruche.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "ref_action_visite_id",
        UUID(as_uuid=True),
        ForeignKey("ref_action_visite.id"),
        primary_key=True,
    ),
)


class RefTypeRuche(Base):
    __tablename__ = "ref_type_ruche"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    libelle = Column(String(50), nullable=False)


class RefStatutRuche(Base):
    __tablename__ = "ref_statut_ruche"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    libelle = Column(String(50), nullable=False)


class RefActionVisite(Base):
    __tablename__ = "ref_action_visite"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    libelle = Column(String(50), nullable=False)


class RefTypeIntervention(Base):
    __tablename__ = "ref_type_intervention"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    libelle = Column(String(50), nullable=False)


class RefActionCadre(Base):
    __tablename__ = "ref_action_cadre"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    libelle = Column(String(50), nullable=False)


class RefTypeMateriel(Base):
    __tablename__ = "ref_type_materiel"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    libelle = Column(String(50), nullable=False)

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    auth_provider = Column(String(20), nullable=False, default="local")
    provider_subject = Column(String(255), unique=True)
    password_hash = Column(String(255), nullable=False)
    prenom = Column(String(100))
    is_premium = Column(Boolean, nullable=False, default=False)
    token_version = Column(Integer, nullable=False, default=0)
    tag_favorites = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("auth_provider IN ('local', 'apple', 'google')", name="ck_users_auth_provider"),
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # Seul le hash est stocke: une fuite de base ne permet pas de rejouer un lien de reinitialisation.
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Rucher(Base):
    __tablename__ = "ruchers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nom = Column(String(150), nullable=False)
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    type_terrain = Column(String(50))
    statut_activite = Column(String(20), nullable=False, default="actif")
    statut_peuplement = Column(String(20), nullable=False, default="peuple")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User")

    __table_args__ = (
        CheckConstraint("statut_activite IN ('actif', 'inactif')", name="ck_ruchers_statut_activite"),
        CheckConstraint("statut_peuplement IN ('peuple', 'vide')", name="ck_ruchers_statut_peuplement"),
    )


class Atelier(Base):
    __tablename__ = "ateliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    nom = Column(String(150), nullable=False, default="Atelier")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User")


class Ruche(Base):
    __tablename__ = "ruches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rucher_id = Column(UUID(as_uuid=True), ForeignKey("ruchers.id", ondelete="SET NULL"), nullable=True)
    atelier_id = Column(UUID(as_uuid=True), ForeignKey("ateliers.id", ondelete="SET NULL"), nullable=True)
    is_at_atelier = Column(Boolean, nullable=False, default=False)
    identifiant_personnalise = Column(String(100), nullable=False)
    ref_type_ruche_id = Column(UUID(as_uuid=True), ForeignKey("ref_type_ruche.id"))
    ref_statut_ruche_id = Column(UUID(as_uuid=True), ForeignKey("ref_statut_ruche.id"))
    reine_annee_marquage = Column(Integer)
    reine_race = Column(String(100))
    reine_provenance = Column(String(150))
    nombre_cadres = Column(Integer)
    format_ruche = Column(String(30))
    has_corps = Column(Boolean, nullable=False, default=True)
    has_hausse = Column(Boolean, nullable=False, default=False)
    has_partition = Column(Boolean, nullable=False, default=False)
    has_grille_a_reine = Column(Boolean, nullable=False, default=False)
    has_nourrisseur = Column(Boolean, nullable=False, default=False)
    has_toit = Column(Boolean, nullable=False, default=True)
    has_plancher = Column(Boolean, nullable=False, default=True)
    # Ruche demontee ou absorbee par un transvasement : sortie des listes et du
    # stock, mais son historique (visites, recoltes) reste dans les statistiques.
    archived_at = Column(DateTime(timezone=True), nullable=True)
    motif_archive = Column(String(30), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    rucher = relationship("Rucher")
    atelier = relationship("Atelier")
    user = relationship("User")
    tags = relationship("RucheTag", cascade="all, delete-orphan", back_populates="ruche")
    reines = relationship("Reine", viewonly=True)

    @property
    def reine_date_mise_en_place(self):
        """Jour de mise en place de la reine active : sert au calcul de son age."""
        active = next((reine for reine in self.reines if reine.statut == "active"), None)
        return active.date_mise_en_place.date() if active is not None else None


class RucheTag(Base):
    __tablename__ = "ruche_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ruche_id = Column(UUID(as_uuid=True), ForeignKey("ruches.id", ondelete="CASCADE"), nullable=False)
    libelle = Column(String(50), nullable=False)
    source = Column(String(20), nullable=False, default="manuel")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    ruche = relationship("Ruche", back_populates="tags")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("ruche_id", "libelle", name="uq_ruche_tags_ruche_libelle"),
        CheckConstraint("source IN ('manuel', 'derive')", name="ck_ruche_tags_source"),
    )


class RucheTransvasement(Base):
    __tablename__ = "ruche_transvasements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ruche_id = Column(UUID(as_uuid=True), ForeignKey("ruches.id", ondelete="CASCADE"), nullable=False)
    visite_ruche_id = Column(UUID(as_uuid=True), ForeignKey("visites_ruche.id", ondelete="SET NULL"), nullable=True)
    date_transvasement = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    format_avant = Column(String(30))
    format_apres = Column(String(30))
    provenance = Column(String(20), nullable=False)
    ruche_atelier_id = Column(UUID(as_uuid=True), ForeignKey("ruches.id", ondelete="SET NULL"), nullable=True)
    cadres_transferes = Column(Integer, nullable=False, default=0)
    cadres_ajoutes = Column(Integer, nullable=False, default=0)
    identifiant_avant = Column(String(100))
    identifiant_apres = Column(String(100))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("provenance IN ('stock', 'achat', 'ruche_atelier')", name="ck_ruche_transvasements_provenance"),
    )


class ModeleRuche(Base):
    __tablename__ = "modeles_ruche"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nom = Column(String(80), nullable=False)
    ref_type_ruche_id = Column(UUID(as_uuid=True), ForeignKey("ref_type_ruche.id", ondelete="SET NULL"), nullable=True)
    format_ruche = Column(String(30))
    nombre_cadres = Column(Integer)
    has_corps = Column(Boolean, nullable=False, default=True)
    has_toit = Column(Boolean, nullable=False, default=True)
    has_plancher = Column(Boolean, nullable=False, default=True)
    has_grille_a_reine = Column(Boolean, nullable=False, default=False)
    has_nourrisseur = Column(Boolean, nullable=False, default=False)
    has_hausse = Column(Boolean, nullable=False, default=False)
    has_partition = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MaterielAtelier(Base):
    __tablename__ = "materiel_atelier"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ref_type_materiel_id = Column(UUID(as_uuid=True), ForeignKey("ref_type_materiel.id"))
    modele = Column(String(100))
    format_materiel = Column(String(30))
    quantite_atelier = Column(Integer, nullable=False, default=0)
    quantite_en_service = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("quantite_atelier >= 0", name="ck_materiel_atelier_quantite_atelier"),
        CheckConstraint("quantite_en_service >= 0", name="ck_materiel_atelier_quantite_en_service"),
    )


class VisiteRucher(Base):
    __tablename__ = "visites_rucher"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rucher_id = Column(UUID(as_uuid=True), ForeignKey("ruchers.id", ondelete="CASCADE"), nullable=False)
    date_visite = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    note_meteo = Column(String(100))
    impression_generale = Column(Text)
    note_globale = Column(Integer)

    __table_args__ = (
        CheckConstraint("note_globale BETWEEN 1 AND 5", name="ck_visites_rucher_note_globale"),
    )


class VisiteRuche(Base):
    __tablename__ = "visites_ruche"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ruche_id = Column(UUID(as_uuid=True), ForeignKey("ruches.id", ondelete="CASCADE"), nullable=False)
    reine_id = Column(UUID(as_uuid=True), ForeignKey("reines.id", ondelete="SET NULL"), nullable=True)
    visite_rucher_id = Column(UUID(as_uuid=True), ForeignKey("visites_rucher.id", ondelete="SET NULL"), nullable=True)
    date_visite = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    reine_vue = Column(Boolean)
    presence_ponte = Column(Boolean)
    etat_couvain = Column(String(20))
    nombre_cadres_couvain = Column(Integer)
    reserves_nourriture = Column(String(20))
    agressivite = Column(Integer)
    note_ruche = Column(Integer)
    nombre_cadres_total = Column(Integer)
    corps_present = Column(Boolean)
    hausse_presente = Column(Boolean)
    grille_a_reine_presente = Column(Boolean)
    nourrisseur_present = Column(Boolean)
    toit_present = Column(Boolean)
    plancher_present = Column(Boolean)
    partition_presente = Column(Boolean)
    source_saisie = Column(String(20), nullable=False, default="manuelle")
    statut_validation = Column(String(20), nullable=False, default="valide")

    __table_args__ = (
        CheckConstraint("etat_couvain IN ('faible', 'normal', 'excellent')", name="ck_visites_ruche_etat_couvain"),
        CheckConstraint(
            "reserves_nourriture IN ('critique', 'correct', 'abondant')",
            name="ck_visites_ruche_reserves_nourriture",
        ),
        CheckConstraint("agressivite BETWEEN 1 AND 5", name="ck_visites_ruche_agressivite"),
        CheckConstraint("note_ruche BETWEEN 1 AND 5", name="ck_visites_ruche_note_ruche"),
        CheckConstraint("nombre_cadres_couvain >= 0", name="ck_visites_ruche_nombre_cadres_couvain"),
        CheckConstraint("nombre_cadres_total >= 0", name="ck_visites_ruche_nombre_cadres_total"),
        CheckConstraint("source_saisie IN ('manuelle', 'ia_vocale')", name="ck_visites_ruche_source_saisie"),
        CheckConstraint("statut_validation IN ('brouillon', 'valide')", name="ck_visites_ruche_statut_validation"),
    )

    actions = relationship("RefActionVisite", secondary=actions_visite)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(255), nullable=False)
    endpoint = Column(String(100), nullable=False)
    response_status = Column(Integer, nullable=False)
    response_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "key", "endpoint", name="uq_idempotency_user_key_endpoint"),
    )


class Reine(Base):
    __tablename__ = "reines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ruche_id = Column(UUID(as_uuid=True), ForeignKey("ruches.id", ondelete="CASCADE"), nullable=False)
    date_mise_en_place = Column(DateTime(timezone=True), nullable=False)
    origine = Column(String(40), nullable=False, default="inconnue")
    race = Column(String(100))
    provenance = Column(String(150))
    statut = Column(String(20), nullable=False, default="active")
    date_fin = Column(DateTime(timezone=True))
    motif_fin = Column(String(40))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    ruche = relationship("Ruche")

    __table_args__ = (
        CheckConstraint("origine IN ('essaimage', 'remerage', 'apport_reine_fecondee', 'apport_reine_vierge', 'cellule_royale', 'inconnue')", name="ck_reines_origine"),
        CheckConstraint("statut IN ('active', 'terminee')", name="ck_reines_statut"),
    )


class InterventionSanitaire(Base):
    __tablename__ = "interventions_sanitaires"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ruche_id = Column(UUID(as_uuid=True), ForeignKey("ruches.id", ondelete="CASCADE"), nullable=False)
    visite_ruche_id = Column(UUID(as_uuid=True), ForeignKey("visites_ruche.id", ondelete="SET NULL"), nullable=True)
    ref_type_intervention_id = Column(UUID(as_uuid=True), ForeignKey("ref_type_intervention.id"))
    date_action = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    details = Column(Text)


class GestionCadres(Base):
    __tablename__ = "gestion_cadres"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ruche_id = Column(UUID(as_uuid=True), ForeignKey("ruches.id", ondelete="CASCADE"), nullable=False)
    visite_ruche_id = Column(UUID(as_uuid=True), ForeignKey("visites_ruche.id", ondelete="SET NULL"), nullable=True)
    ref_action_cadre_id = Column(UUID(as_uuid=True), ForeignKey("ref_action_cadre.id"))
    quantite = Column(Integer, nullable=False)
    annee_cire = Column(Integer)

    __table_args__ = (
        CheckConstraint("quantite > 0", name="ck_gestion_cadres_quantite"),
        CheckConstraint("annee_cire >= 1900", name="ck_gestion_cadres_annee_cire"),
    )


class MouvementHausse(Base):
    __tablename__ = "mouvements_hausses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ruche_id = Column(UUID(as_uuid=True), ForeignKey("ruches.id", ondelete="CASCADE"), nullable=False)
    visite_ruche_id = Column(UUID(as_uuid=True), ForeignKey("visites_ruche.id", ondelete="SET NULL"), nullable=True)
    quantite_delta = Column(Integer, nullable=False)
    note = Column(Text)


class Recolte(Base):
    __tablename__ = "recoltes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ruche_id = Column(UUID(as_uuid=True), ForeignKey("ruches.id", ondelete="CASCADE"), nullable=False)
    visite_ruche_id = Column(UUID(as_uuid=True), ForeignKey("visites_ruche.id", ondelete="SET NULL"), nullable=True)
    date_recolte = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    poids_miel_kg = Column(Numeric(5, 2), nullable=False)


class ApiEvent(Base):
    __tablename__ = "api_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(64), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    method = Column(String(10), nullable=False)
    path = Column(String(255), nullable=False)
    status_code = Column(Integer, nullable=False)
    duration_ms = Column(Numeric(10, 2), nullable=False)
    error_code = Column(String(50))
    error_message = Column(String(255))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (CheckConstraint("poids_miel_kg >= 0", name="ck_recoltes_poids_miel_kg"),)


class BetaFeedback(Base):
    __tablename__ = "beta_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(30), nullable=False)
    message = Column(Text, nullable=False)
    context = Column(String(255))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    # Classement des retours traites (scripts/linux/list_beta_feedback.sh).
    traite_le = Column(DateTime(timezone=True))
    note_traitement = Column(String(255))

    user = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "category IN ('bug', 'idee', 'question', 'autre')",
            name="ck_beta_feedback_category",
        ),
    )
