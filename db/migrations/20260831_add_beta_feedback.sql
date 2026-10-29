CREATE TABLE IF NOT EXISTS beta_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(30) NOT NULL CHECK (category IN ('bug', 'idee', 'question', 'autre')),
    message TEXT NOT NULL CHECK (char_length(message) >= 10),
    context VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_beta_feedback_created_at ON beta_feedback(created_at DESC);