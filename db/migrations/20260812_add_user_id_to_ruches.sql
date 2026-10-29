ALTER TABLE ruches
ADD COLUMN IF NOT EXISTS user_id UUID;

UPDATE ruches r
SET user_id = ru.user_id
FROM ruchers ru
WHERE r.rucher_id = ru.id
  AND r.user_id IS NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_ruches_user_id'
  ) THEN
    ALTER TABLE ruches
    ADD CONSTRAINT fk_ruches_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_ruches_user_id ON ruches(user_id);
