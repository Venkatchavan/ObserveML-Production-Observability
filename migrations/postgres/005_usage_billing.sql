-- OB-42: Usage billing — track monthly event counts per org
-- Sprint 05 — v1.2.0
-- Note: billing invoice history must survive GDPR data deletion (Vedantic Launch Gate).

CREATE TABLE IF NOT EXISTS usage_billing (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         UUID        NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    billing_period VARCHAR(7)  NOT NULL,  -- 'YYYY-MM'
    event_count    BIGINT      NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_billing_org_period
    ON usage_billing(org_id, billing_period);
