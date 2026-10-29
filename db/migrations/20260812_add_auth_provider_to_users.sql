ALTER TABLE users
ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(20) NOT NULL DEFAULT 'local';

ALTER TABLE users
ADD COLUMN IF NOT EXISTS provider_subject VARCHAR(255);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_users_auth_provider'
    ) THEN
        ALTER TABLE users
        ADD CONSTRAINT ck_users_auth_provider
        CHECK (auth_provider IN ('local', 'apple', 'google'));
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider_subject_unique
ON users(provider_subject)
WHERE provider_subject IS NOT NULL;