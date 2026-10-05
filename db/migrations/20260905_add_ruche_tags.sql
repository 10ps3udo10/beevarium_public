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

ALTER TABLE ruche_tags ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_ruche_tags_user_ruche ON ruche_tags(user_id, ruche_id);