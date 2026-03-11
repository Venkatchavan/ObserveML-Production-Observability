-- OB-03: PostgreSQL schema migration 001 — initial tables
-- Applied by: Alembic in production, init_db() in development

CREATE TABLE IF NOT EXISTS organizations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(255) NOT NULL,
    plan       VARCHAR(20)  NOT NULL DEFAULT 'free'
                   CHECK (plan IN ('free', 'pro', 'enterprise')),
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_keys (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL
                     REFERENCES organizations(id) ON DELETE CASCADE,
    key_hash     VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256; plaintext never stored
    name         VARCHAR(255),
    last_used_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL
                    REFERENCES organizations(id) ON DELETE CASCADE,
    call_site   VARCHAR(255),           -- NULL = applies to all call sites
    metric      VARCHAR(50)  NOT NULL,  -- 'latency_p95', 'error_rate', 'cost_usd'
    threshold   NUMERIC      NOT NULL,
    webhook_url TEXT,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash
    ON api_keys(key_hash) WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_alert_rules_org
    ON alert_rules(org_id);
