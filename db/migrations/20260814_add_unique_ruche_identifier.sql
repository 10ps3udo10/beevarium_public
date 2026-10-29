DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM ruches
        GROUP BY user_id, lower(trim(identifiant_personnalise))
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Doublons identifiant_personnalise detectes: traiter les donnees avant la migration';
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_ruches_user_identifier_normalized
    ON ruches (user_id, lower(trim(identifiant_personnalise)));