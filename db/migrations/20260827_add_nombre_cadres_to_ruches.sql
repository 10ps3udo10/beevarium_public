-- Nombre de cadres connu de la ruche, saisissable des la creation.
-- Evite d'obliger l'apiculteur a creer une visite pour renseigner cette donnee.
ALTER TABLE ruches ADD COLUMN IF NOT EXISTS nombre_cadres INTEGER;

ALTER TABLE ruches ADD CONSTRAINT ck_ruches_nombre_cadres
    CHECK (nombre_cadres IS NULL OR (nombre_cadres >= 0 AND nombre_cadres <= 100));
