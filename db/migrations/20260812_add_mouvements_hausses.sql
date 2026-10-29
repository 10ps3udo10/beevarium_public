CREATE TABLE IF NOT EXISTS mouvements_hausses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruche_id UUID NOT NULL REFERENCES ruches(id) ON DELETE CASCADE,
    visite_ruche_id UUID REFERENCES visites_ruche(id) ON DELETE SET NULL,
    quantite_delta INTEGER NOT NULL,
    note TEXT
);

CREATE INDEX IF NOT EXISTS idx_mouvements_hausses_ruche_id ON mouvements_hausses(ruche_id);