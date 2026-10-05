CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    auth_provider VARCHAR(20) NOT NULL DEFAULT 'local' CHECK (auth_provider IN ('local', 'apple', 'google')),
    provider_subject VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    prenom VARCHAR(100),
    is_premium BOOLEAN NOT NULL DEFAULT FALSE,
    token_version INTEGER NOT NULL DEFAULT 0,
    tag_favorites JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ref_type_ruche (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    libelle VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_statut_ruche (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    libelle VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_action_visite (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    libelle VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_type_intervention (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    libelle VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_action_cadre (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    libelle VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_type_materiel (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    libelle VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS ruchers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nom VARCHAR(150) NOT NULL,
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    type_terrain VARCHAR(50),
    statut_activite VARCHAR(20) NOT NULL DEFAULT 'actif' CHECK (statut_activite IN ('actif', 'inactif')),
    statut_peuplement VARCHAR(20) NOT NULL DEFAULT 'peuple' CHECK (statut_peuplement IN ('peuple', 'vide')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ruches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rucher_id UUID REFERENCES ruchers(id) ON DELETE SET NULL,
    is_at_atelier BOOLEAN NOT NULL DEFAULT FALSE,
    identifiant_personnalise VARCHAR(100) NOT NULL,
    ref_type_ruche_id UUID REFERENCES ref_type_ruche(id),
    ref_statut_ruche_id UUID REFERENCES ref_statut_ruche(id),
    reine_annee_marquage INTEGER,
    reine_race VARCHAR(100),
    reine_provenance VARCHAR(150),
    nombre_cadres INTEGER CHECK (nombre_cadres IS NULL OR (nombre_cadres >= 0 AND nombre_cadres <= 100)),
    format_ruche VARCHAR(30),
    has_corps BOOLEAN NOT NULL DEFAULT TRUE,
    has_hausse BOOLEAN NOT NULL DEFAULT FALSE,
    has_partition BOOLEAN NOT NULL DEFAULT FALSE,
    has_grille_a_reine BOOLEAN NOT NULL DEFAULT FALSE,
    has_nourrisseur BOOLEAN NOT NULL DEFAULT FALSE,
    has_toit BOOLEAN NOT NULL DEFAULT TRUE,
    has_plancher BOOLEAN NOT NULL DEFAULT TRUE,
    archived_at TIMESTAMPTZ,
    motif_archive VARCHAR(30),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ruches_user_identifier_active
    ON ruches (user_id, lower(trim(identifiant_personnalise)))
    WHERE archived_at IS NULL;

CREATE TABLE IF NOT EXISTS ruche_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ruche_id UUID NOT NULL REFERENCES ruches(id) ON DELETE CASCADE,
    libelle VARCHAR(50) NOT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'manuel' CHECK (source IN ('manuel', 'derive')),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ruche_tags_ruche_libelle UNIQUE (ruche_id, libelle)
);

CREATE TABLE IF NOT EXISTS materiel_atelier (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ref_type_materiel_id UUID REFERENCES ref_type_materiel(id),
    modele VARCHAR(100),
    format_materiel VARCHAR(30),
    quantite_atelier INTEGER NOT NULL DEFAULT 0 CHECK (quantite_atelier >= 0),
    quantite_en_service INTEGER NOT NULL DEFAULT 0 CHECK (quantite_en_service >= 0)
);

CREATE TABLE IF NOT EXISTS ateliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    nom VARCHAR(150) NOT NULL DEFAULT 'Atelier',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS visites_rucher (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rucher_id UUID NOT NULL REFERENCES ruchers(id) ON DELETE CASCADE,
    date_visite TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    note_meteo VARCHAR(100),
    impression_generale TEXT,
    note_globale INTEGER CHECK (note_globale BETWEEN 1 AND 5)
);

CREATE TABLE IF NOT EXISTS visites_ruche (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruche_id UUID NOT NULL REFERENCES ruches(id) ON DELETE CASCADE,
    visite_rucher_id UUID REFERENCES visites_rucher(id) ON DELETE SET NULL,
    date_visite TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reine_vue BOOLEAN,
    presence_ponte BOOLEAN,
    etat_couvain VARCHAR(20) CHECK (etat_couvain IN ('faible', 'normal', 'excellent')),
    nombre_cadres_couvain INTEGER CHECK (nombre_cadres_couvain >= 0),
    reserves_nourriture VARCHAR(20) CHECK (reserves_nourriture IN ('critique', 'correct', 'abondant')),
    agressivite INTEGER CHECK (agressivite BETWEEN 1 AND 5),
    note_ruche INTEGER CHECK (note_ruche BETWEEN 1 AND 5),
    nombre_cadres_total INTEGER CHECK (nombre_cadres_total >= 0),
    source_saisie VARCHAR(20) NOT NULL DEFAULT 'manuelle' CHECK (source_saisie IN ('manuelle', 'ia_vocale')),
    statut_validation VARCHAR(20) NOT NULL DEFAULT 'valide' CHECK (statut_validation IN ('brouillon', 'valide')),
    corps_present BOOLEAN,
    hausse_presente BOOLEAN,
    grille_a_reine_presente BOOLEAN,
    nourrisseur_present BOOLEAN,
    toit_present BOOLEAN,
    plancher_present BOOLEAN
    ,partition_presente BOOLEAN
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    endpoint VARCHAR(100) NOT NULL,
    response_status INTEGER NOT NULL,
    response_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_idempotency_user_key_endpoint UNIQUE (user_id, key, endpoint)
);

CREATE TABLE IF NOT EXISTS reines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruche_id UUID NOT NULL REFERENCES ruches(id) ON DELETE CASCADE,
    date_mise_en_place TIMESTAMPTZ NOT NULL,
    origine VARCHAR(40) NOT NULL DEFAULT 'inconnue',
    race VARCHAR(100),
    provenance VARCHAR(150),
    statut VARCHAR(20) NOT NULL DEFAULT 'active',
    date_fin TIMESTAMPTZ,
    motif_fin VARCHAR(40),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_reines_origine CHECK (origine IN ('essaimage', 'remerage', 'apport_reine_fecondee', 'apport_reine_vierge', 'cellule_royale', 'inconnue')),
    CONSTRAINT ck_reines_statut CHECK (statut IN ('active', 'terminee'))
);

ALTER TABLE ruches ADD COLUMN IF NOT EXISTS atelier_id UUID REFERENCES ateliers(id) ON DELETE SET NULL;
ALTER TABLE visites_ruche ADD COLUMN IF NOT EXISTS reine_id UUID REFERENCES reines(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS actions_visite (
    visite_ruche_id UUID NOT NULL REFERENCES visites_ruche(id) ON DELETE CASCADE,
    ref_action_visite_id UUID NOT NULL REFERENCES ref_action_visite(id),
    PRIMARY KEY (visite_ruche_id, ref_action_visite_id)
);

CREATE TABLE IF NOT EXISTS interventions_sanitaires (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruche_id UUID NOT NULL REFERENCES ruches(id) ON DELETE CASCADE,
    visite_ruche_id UUID REFERENCES visites_ruche(id) ON DELETE SET NULL,
    ref_type_intervention_id UUID REFERENCES ref_type_intervention(id),
    date_action TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    details TEXT
);

CREATE TABLE IF NOT EXISTS gestion_cadres (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruche_id UUID NOT NULL REFERENCES ruches(id) ON DELETE CASCADE,
    visite_ruche_id UUID REFERENCES visites_ruche(id) ON DELETE SET NULL,
    ref_action_cadre_id UUID REFERENCES ref_action_cadre(id),
    quantite INTEGER NOT NULL CHECK (quantite > 0),
    annee_cire INTEGER CHECK (annee_cire >= 1900)
);

CREATE TABLE IF NOT EXISTS mouvements_hausses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruche_id UUID NOT NULL REFERENCES ruches(id) ON DELETE CASCADE,
    visite_ruche_id UUID REFERENCES visites_ruche(id) ON DELETE SET NULL,
    quantite_delta INTEGER NOT NULL CHECK (quantite_delta <> 0),
    note TEXT
);

CREATE TABLE IF NOT EXISTS recoltes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruche_id UUID NOT NULL REFERENCES ruches(id) ON DELETE CASCADE,
    visite_ruche_id UUID REFERENCES visites_ruche(id) ON DELETE SET NULL,
    date_recolte TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    poids_miel_kg DECIMAL(5,2) NOT NULL CHECK (poids_miel_kg >= 0)
);

CREATE TABLE IF NOT EXISTS ruche_transvasements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ruche_id UUID NOT NULL REFERENCES ruches(id) ON DELETE CASCADE,
    visite_ruche_id UUID REFERENCES visites_ruche(id) ON DELETE SET NULL,
    date_transvasement TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    format_avant VARCHAR(30),
    format_apres VARCHAR(30),
    provenance VARCHAR(20) NOT NULL CHECK (provenance IN ('stock', 'achat', 'ruche_atelier')),
    ruche_atelier_id UUID REFERENCES ruches(id) ON DELETE SET NULL,
    cadres_transferes INTEGER NOT NULL DEFAULT 0 CHECK (cadres_transferes >= 0),
    cadres_ajoutes INTEGER NOT NULL DEFAULT 0 CHECK (cadres_ajoutes >= 0),
    identifiant_avant VARCHAR(100),
    identifiant_apres VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ruche_transvasements_ruche ON ruche_transvasements (ruche_id, date_transvasement);

CREATE TABLE IF NOT EXISTS modeles_ruche (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nom VARCHAR(80) NOT NULL,
    ref_type_ruche_id UUID REFERENCES ref_type_ruche(id) ON DELETE SET NULL,
    format_ruche VARCHAR(30),
    nombre_cadres INTEGER CHECK (nombre_cadres IS NULL OR (nombre_cadres >= 0 AND nombre_cadres <= 100)),
    has_corps BOOLEAN NOT NULL DEFAULT TRUE,
    has_toit BOOLEAN NOT NULL DEFAULT TRUE,
    has_plancher BOOLEAN NOT NULL DEFAULT TRUE,
    has_grille_a_reine BOOLEAN NOT NULL DEFAULT FALSE,
    has_nourrisseur BOOLEAN NOT NULL DEFAULT FALSE,
    has_hausse BOOLEAN NOT NULL DEFAULT FALSE,
    has_partition BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_modeles_ruche_user_nom ON modeles_ruche (user_id, lower(trim(nom)));

CREATE TABLE IF NOT EXISTS api_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(64) NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    method VARCHAR(10) NOT NULL,
    path VARCHAR(255) NOT NULL,
    status_code INTEGER NOT NULL,
    duration_ms NUMERIC(10,2) NOT NULL,
    error_code VARCHAR(50),
    error_message VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS beta_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(30) NOT NULL CHECK (category IN ('bug', 'idee', 'question', 'autre')),
    message TEXT NOT NULL CHECK (char_length(message) >= 10),
    context VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    traite_le TIMESTAMPTZ,
    note_traitement VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_ruchers_user_id ON ruchers(user_id);
CREATE INDEX IF NOT EXISTS idx_ruches_user_id ON ruches(user_id);
CREATE INDEX IF NOT EXISTS idx_ruches_rucher_id ON ruches(rucher_id);
CREATE INDEX IF NOT EXISTS idx_ruches_format ON ruches(user_id, format_ruche);
CREATE INDEX IF NOT EXISTS idx_materiel_atelier_user_id ON materiel_atelier(user_id);
CREATE INDEX IF NOT EXISTS idx_materiel_atelier_ref_type_materiel_id ON materiel_atelier(ref_type_materiel_id);
CREATE INDEX IF NOT EXISTS idx_materiel_format ON materiel_atelier(user_id, format_materiel);
CREATE UNIQUE INDEX IF NOT EXISTS uq_materiel_atelier_type_format ON materiel_atelier(user_id, ref_type_materiel_id, COALESCE(format_materiel, ''));
CREATE INDEX IF NOT EXISTS idx_visites_rucher_rucher_id ON visites_rucher(rucher_id);
CREATE INDEX IF NOT EXISTS idx_visites_ruche_ruche_id ON visites_ruche(ruche_id);
CREATE INDEX IF NOT EXISTS idx_visites_ruche_visite_rucher_id ON visites_ruche(visite_rucher_id);
CREATE INDEX IF NOT EXISTS idx_interventions_sanitaires_ruche_id ON interventions_sanitaires(ruche_id);
CREATE INDEX IF NOT EXISTS idx_interventions_sanitaires_visite_ruche_id ON interventions_sanitaires(visite_ruche_id);
CREATE INDEX IF NOT EXISTS idx_gestion_cadres_ruche_id ON gestion_cadres(ruche_id);
CREATE INDEX IF NOT EXISTS idx_gestion_cadres_visite_ruche_id ON gestion_cadres(visite_ruche_id);
CREATE INDEX IF NOT EXISTS idx_mouvements_hausses_ruche_id ON mouvements_hausses(ruche_id);
CREATE INDEX IF NOT EXISTS idx_mouvements_hausses_visite_ruche_id ON mouvements_hausses(visite_ruche_id);
CREATE INDEX IF NOT EXISTS idx_recoltes_ruche_id ON recoltes(ruche_id);
CREATE INDEX IF NOT EXISTS idx_recoltes_visite_ruche_id ON recoltes(visite_ruche_id);
CREATE INDEX IF NOT EXISTS idx_recoltes_date_recolte ON recoltes(date_recolte);
CREATE INDEX IF NOT EXISTS idx_api_events_user_created_at ON api_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_password_reset_user_created ON password_reset_tokens(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_password_reset_expires ON password_reset_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_created_at ON beta_feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_events_request_id ON api_events(request_id);
CREATE INDEX IF NOT EXISTS idx_api_events_created_at ON api_events(created_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_type_ruche_system_libelle ON ref_type_ruche(libelle) WHERE is_system IS TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_type_ruche_user_libelle ON ref_type_ruche(user_id, libelle) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_statut_ruche_system_libelle ON ref_statut_ruche(libelle) WHERE is_system IS TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_statut_ruche_user_libelle ON ref_statut_ruche(user_id, libelle) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_action_visite_system_libelle ON ref_action_visite(libelle) WHERE is_system IS TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_action_visite_user_libelle ON ref_action_visite(user_id, libelle) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_type_intervention_system_libelle ON ref_type_intervention(libelle) WHERE is_system IS TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_type_intervention_user_libelle ON ref_type_intervention(user_id, libelle) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_action_cadre_system_libelle ON ref_action_cadre(libelle) WHERE is_system IS TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_action_cadre_user_libelle ON ref_action_cadre(user_id, libelle) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_type_materiel_system_libelle ON ref_type_materiel(libelle) WHERE is_system IS TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_type_materiel_user_libelle ON ref_type_materiel(user_id, libelle) WHERE user_id IS NOT NULL;
