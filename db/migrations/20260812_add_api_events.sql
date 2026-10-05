CREATE TABLE IF NOT EXISTS api_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(64) NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    method VARCHAR(10) NOT NULL,
    path VARCHAR(255) NOT NULL,
    status_code INTEGER NOT NULL,
    duration_ms NUMERIC(10,2) NOT NULL,
    error_code VARCHAR(50),
    error_message VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_events_user_created_at ON api_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_events_request_id ON api_events(request_id);
