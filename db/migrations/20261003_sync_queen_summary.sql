-- Aligne le resume reine des ruches sur la table reines (source de verite).
-- 1. Ruches avec un resume reine mais aucune reine enregistree : creation de
--    la reine active (age calcule depuis l'annee saisie).
INSERT INTO reines (id, ruche_id, date_mise_en_place, origine, race, provenance, statut)
SELECT
    gen_random_uuid(),
    r.id,
    make_timestamptz(COALESCE(r.reine_annee_marquage, EXTRACT(YEAR FROM r.created_at)::int), 1, 1, 0, 0, 0, 'UTC'),
    'inconnue',
    r.reine_race,
    r.reine_provenance,
    'active'
FROM ruches r
WHERE (r.reine_annee_marquage IS NOT NULL OR r.reine_race IS NOT NULL OR r.reine_provenance IS NOT NULL)
  AND NOT EXISTS (SELECT 1 FROM reines q WHERE q.ruche_id = r.id);

-- 2. Ruches avec une reine active : le resume reprend ses valeurs (corrige les
--    remplacements de reine faits avant la v1.34).
UPDATE ruches r
SET reine_race = q.race,
    reine_provenance = q.provenance,
    reine_annee_marquage = EXTRACT(YEAR FROM q.date_mise_en_place)::int
FROM reines q
WHERE q.ruche_id = r.id
  AND q.statut = 'active'
  AND (
    r.reine_race IS DISTINCT FROM q.race
    OR r.reine_provenance IS DISTINCT FROM q.provenance
    OR r.reine_annee_marquage IS DISTINCT FROM EXTRACT(YEAR FROM q.date_mise_en_place)::int
  );
