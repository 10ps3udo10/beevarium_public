BEGIN;

-- 1. Cadres et partitions se rangent au format du cadre : une ruchette Dadant
--    porte des cadres et une partition Dadant. Le format "ruchette" disparait
--    pour ces deux types.
UPDATE materiel_atelier m
SET format_materiel = 'dadant'
FROM ref_type_materiel r
WHERE r.id = m.ref_type_materiel_id
  AND lower(r.libelle) IN ('cadre', 'partition')
  AND m.format_materiel = 'ruchette';

-- 2. Une seule ligne de stock par utilisateur, type et format : les doublons
--    faisaient qu'une modification ne touchait qu'une ligne (retour beta).
WITH groupes AS (
    SELECT user_id, ref_type_materiel_id, COALESCE(format_materiel, '') AS fmt,
           min(id::text) AS garde, sum(quantite_atelier) AS qa, sum(quantite_en_service) AS qs
    FROM materiel_atelier
    GROUP BY user_id, ref_type_materiel_id, COALESCE(format_materiel, '')
    HAVING count(*) > 1
)
UPDATE materiel_atelier m
SET quantite_atelier = g.qa, quantite_en_service = g.qs
FROM groupes g
WHERE m.id::text = g.garde;

DELETE FROM materiel_atelier m
USING materiel_atelier k
WHERE m.user_id = k.user_id
  AND m.ref_type_materiel_id IS NOT DISTINCT FROM k.ref_type_materiel_id
  AND COALESCE(m.format_materiel, '') = COALESCE(k.format_materiel, '')
  AND m.id::text > k.id::text;

CREATE UNIQUE INDEX IF NOT EXISTS uq_materiel_atelier_type_format
    ON materiel_atelier(user_id, ref_type_materiel_id, COALESCE(format_materiel, ''));

-- 3. Retours testeurs : les retours traites sont classes, pas supprimes.
ALTER TABLE beta_feedback ADD COLUMN IF NOT EXISTS traite_le TIMESTAMPTZ;
ALTER TABLE beta_feedback ADD COLUMN IF NOT EXISTS note_traitement VARCHAR(255);

COMMIT;
