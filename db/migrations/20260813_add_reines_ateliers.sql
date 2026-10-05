CREATE TABLE IF NOT EXISTS ateliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    nom VARCHAR(150) NOT NULL DEFAULT 'Atelier',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE ruches ADD COLUMN IF NOT EXISTS atelier_id UUID REFERENCES ateliers(id) ON DELETE SET NULL;

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

ALTER TABLE visites_ruche ADD COLUMN IF NOT EXISTS reine_id UUID REFERENCES reines(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_reines_ruche_date ON reines(ruche_id, date_mise_en_place DESC);