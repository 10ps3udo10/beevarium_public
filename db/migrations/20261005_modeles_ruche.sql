-- Modeles de ruche (Premium) : configuration reutilisable pour la creation
-- rapide (format, cadres, elements presents).

CREATE TABLE IF NOT EXISTS modeles_ruche (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nom VARCHAR(80) NOT NULL,
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
