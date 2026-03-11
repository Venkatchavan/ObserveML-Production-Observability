-- OB-12: alert_fired table — records every anomaly threshold breach
CREATE TABLE IF NOT EXISTS alert_fired (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id       UUID REFERENCES alert_rules(id) ON DELETE SET NULL,
    org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    call_site     VARCHAR(255),
    metric        VARCHAR(50),
    current_value NUMERIC,
    threshold     NUMERIC,
    fired_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_fired_org_fired
    ON alert_fired(org_id, fired_at DESC);
