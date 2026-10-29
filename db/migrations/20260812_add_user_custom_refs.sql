ALTER TABLE ref_type_ruche ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE ref_type_ruche ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE ref_type_ruche SET is_system = TRUE WHERE user_id IS NULL;
ALTER TABLE ref_type_ruche DROP CONSTRAINT IF EXISTS ref_type_ruche_libelle_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_type_ruche_system_libelle ON ref_type_ruche(libelle) WHERE is_system IS TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_type_ruche_user_libelle ON ref_type_ruche(user_id, libelle) WHERE user_id IS NOT NULL;

ALTER TABLE ref_statut_ruche ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE ref_statut_ruche ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE ref_statut_ruche SET is_system = TRUE WHERE user_id IS NULL;
ALTER TABLE ref_statut_ruche DROP CONSTRAINT IF EXISTS ref_statut_ruche_libelle_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_statut_ruche_system_libelle ON ref_statut_ruche(libelle) WHERE is_system IS TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_statut_ruche_user_libelle ON ref_statut_ruche(user_id, libelle) WHERE user_id IS NOT NULL;

ALTER TABLE ref_action_visite ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE ref_action_visite ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE ref_action_visite SET is_system = TRUE WHERE user_id IS NULL;
ALTER TABLE ref_action_visite DROP CONSTRAINT IF EXISTS ref_action_visite_libelle_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_action_visite_system_libelle ON ref_action_visite(libelle) WHERE is_system IS TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_action_visite_user_libelle ON ref_action_visite(user_id, libelle) WHERE user_id IS NOT NULL;

ALTER TABLE ref_type_intervention ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE ref_type_intervention ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE ref_type_intervention SET is_system = TRUE WHERE user_id IS NULL;
ALTER TABLE ref_type_intervention DROP CONSTRAINT IF EXISTS ref_type_intervention_libelle_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_type_intervention_system_libelle ON ref_type_intervention(libelle) WHERE is_system IS TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_type_intervention_user_libelle ON ref_type_intervention(user_id, libelle) WHERE user_id IS NOT NULL;

ALTER TABLE ref_action_cadre ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE ref_action_cadre ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE ref_action_cadre SET is_system = TRUE WHERE user_id IS NULL;
ALTER TABLE ref_action_cadre DROP CONSTRAINT IF EXISTS ref_action_cadre_libelle_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_action_cadre_system_libelle ON ref_action_cadre(libelle) WHERE is_system IS TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_action_cadre_user_libelle ON ref_action_cadre(user_id, libelle) WHERE user_id IS NOT NULL;

ALTER TABLE ref_type_materiel ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE ref_type_materiel ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE ref_type_materiel SET is_system = TRUE WHERE user_id IS NULL;
ALTER TABLE ref_type_materiel DROP CONSTRAINT IF EXISTS ref_type_materiel_libelle_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_type_materiel_system_libelle ON ref_type_materiel(libelle) WHERE is_system IS TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ref_type_materiel_user_libelle ON ref_type_materiel(user_id, libelle) WHERE user_id IS NOT NULL;