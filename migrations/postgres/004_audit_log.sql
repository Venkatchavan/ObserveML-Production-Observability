-- OB-47: Audit log for API key rotation and org events
-- Sprint 05 — v1.2.0

CREATE TABLE IF NOT EXISTS audit_log (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id     UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    action     VARCHAR(64) NOT NULL,   -- 'API_KEY_ROTATED', 'DATA_DELETION_REQUESTED', etc.
    actor      VARCHAR(255),           -- 'api' or user email
    details    TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_org
    ON audit_log(org_id, created_at DESC);
