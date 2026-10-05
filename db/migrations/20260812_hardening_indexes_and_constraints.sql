DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_mouvements_hausses_quantite_delta_non_zero'
    ) THEN
        ALTER TABLE mouvements_hausses
        ADD CONSTRAINT ck_mouvements_hausses_quantite_delta_non_zero
        CHECK (quantite_delta <> 0);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_materiel_atelier_user_id ON materiel_atelier(user_id);
CREATE INDEX IF NOT EXISTS idx_materiel_atelier_ref_type_materiel_id ON materiel_atelier(ref_type_materiel_id);
CREATE INDEX IF NOT EXISTS idx_visites_rucher_rucher_id ON visites_rucher(rucher_id);
CREATE INDEX IF NOT EXISTS idx_visites_ruche_visite_rucher_id ON visites_ruche(visite_rucher_id);
CREATE INDEX IF NOT EXISTS idx_interventions_sanitaires_ruche_id ON interventions_sanitaires(ruche_id);
CREATE INDEX IF NOT EXISTS idx_interventions_sanitaires_visite_ruche_id ON interventions_sanitaires(visite_ruche_id);
CREATE INDEX IF NOT EXISTS idx_gestion_cadres_ruche_id ON gestion_cadres(ruche_id);
CREATE INDEX IF NOT EXISTS idx_gestion_cadres_visite_ruche_id ON gestion_cadres(visite_ruche_id);
CREATE INDEX IF NOT EXISTS idx_mouvements_hausses_visite_ruche_id ON mouvements_hausses(visite_ruche_id);
CREATE INDEX IF NOT EXISTS idx_recoltes_visite_ruche_id ON recoltes(visite_ruche_id);
CREATE INDEX IF NOT EXISTS idx_recoltes_date_recolte ON recoltes(date_recolte);
