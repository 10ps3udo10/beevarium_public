-- Purge quotidienne du journal technique au-dela de 6 mois (backup_daily.sh) :
-- index sur la date pour eviter un parcours complet de la table.
CREATE INDEX IF NOT EXISTS idx_api_events_created_at ON api_events(created_at);
