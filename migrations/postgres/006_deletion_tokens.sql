-- OB-48: GDPR deletion tokens — single-use, 25h TTL, 24h cooling-off
-- Sprint 05 — v1.2.0
-- Śhāstrārtha checkpoint: token must be >= 24h old before deletion executes.
-- Note: ON DELETE RESTRICT — billing history (usage_billing) prevents cascade.

CREATE TABLE IF NOT EXISTS deletion_tokens (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    token_hash   VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 of plaintext token
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed_at  TIMESTAMPTZ                   -- NULL until deletion runs
);

CREATE INDEX IF NOT EXISTS idx_deletion_tokens_org
    ON deletion_tokens(org_id, requested_at DESC);
