-- Cycle de vie du materiel (lot L4) : archivage des ruches demontees ou
-- utilisees pour un transvasement, et journal des transvasements.

ALTER TABLE ruches ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
ALTER TABLE ruches ADD COLUMN IF NOT EXISTS motif_archive VARCHAR(30);

-- Une ruche archivee libere son identifiant pour une nouvelle ruche.
DROP INDEX IF EXISTS uq_ruches_user_identifier_normalized;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ruches_user_identifier_active
    ON ruches (user_id, lower(trim(identifiant_personnalise)))
    WHERE archived_at IS NULL;

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
