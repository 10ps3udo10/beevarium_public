-- Type de ruche (production, essaim...) dans les modeles de creation rapide.

ALTER TABLE modeles_ruche ADD COLUMN IF NOT EXISTS ref_type_ruche_id UUID REFERENCES ref_type_ruche(id) ON DELETE SET NULL;
