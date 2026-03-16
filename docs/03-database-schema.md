# Database Schema â€” ObserveML
**v1.2.0 | 2026-03-16 | Database Architect**

---

## 1. Entity Relationship Overview

```
organizations â”€â”€< api_keys
organizations â”€â”€< alert_rules
organizations â”€â”€< team_members
organizations â”€â”€< audit_log
organizations â”€â”€< usage_billing  (ON DELETE RESTRICT -- billing history preserved on GDPR deletion)
organizations â”€â”€< deletion_tokens
[ClickHouse] metric_events (time-series, partitioned by org + day)
[PostgreSQL] organizations, api_keys, alert_rules, team_members, audit_log, usage_billing, deletion_tokens
```

---

## 2. PostgreSQL Tables

### `organizations`
```sql
CREATE TABLE organizations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(255) NOT NULL,
    plan       VARCHAR(20) NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `api_keys`
```sql
CREATE TABLE api_keys (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    key_hash     VARCHAR(64) NOT NULL UNIQUE, -- SHA-256 of the key; plaintext never stored
    name         VARCHAR(255),
    last_used_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at   TIMESTAMPTZ
);
```

### `alert_rules`
```sql
CREATE TABLE alert_rules (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    call_site    VARCHAR(255),        -- NULL = applies to all call sites
    metric       VARCHAR(50) NOT NULL, -- 'latency_p95', 'error_rate', 'cost_usd'
    threshold    NUMERIC NOT NULL,
    webhook_url  TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `team_members`
```sql
CREATE TABLE team_members (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_email   VARCHAR(255) NOT NULL,
    role         VARCHAR(20) NOT NULL DEFAULT 'viewer'
                     CHECK (role IN ('owner', 'analyst', 'viewer')),
    invited_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at  TIMESTAMPTZ,
    UNIQUE (org_id, user_email)
);
```

### `audit_log`
```sql
CREATE TABLE audit_log (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    action     VARCHAR(64) NOT NULL,  -- 'key_rotated', 'deletion_requested', 'deletion_executed'
    actor      VARCHAR(255),          -- email or system
    details    TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `usage_billing`
```sql
CREATE TABLE usage_billing (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    billing_period VARCHAR(7) NOT NULL,  -- 'YYYY-MM'
    event_count    BIGINT NOT NULL DEFAULT 0,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (org_id, billing_period)
);
-- ON DELETE RESTRICT: billing history must survive GDPR data deletion
```

### `deletion_tokens`
```sql
CREATE TABLE deletion_tokens (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    token_hash   VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 of single-use raw token
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed_at  TIMESTAMPTZ  -- NULL until deletion is executed
);
```

---

## 3. ClickHouse Table (Metric Events)

```sql
CREATE TABLE metric_events (
    event_id      String,        -- idempotency key
    org_id        String,
    call_site     String,        -- hash fingerprint of source location
    model         String,        -- 'gpt-4o', 'claude-3-5', etc.
    latency_ms    UInt32,
    input_tokens  UInt32,
    output_tokens UInt32,
    cost_usd      Float32,
    error         Bool,
    error_code    String,
    prompt_hash   String,        -- SHA-256; never prompt content
    trace_id      String,        -- OTel trace propagation (added v1.1.0)
    session_id    String,        -- session grouping (added v1.2.0)
    ts            DateTime64(3)  -- millisecond precision
) ENGINE = MergeTree()
PARTITION BY (org_id, toYYYYMMDD(ts))
ORDER BY (org_id, call_site, ts)
TTL ts + INTERVAL 90 DAY;
```

---

## 4. Indexes

```sql
-- PostgreSQL
CREATE INDEX idx_api_keys_hash  ON api_keys(key_hash) WHERE revoked_at IS NULL;
CREATE INDEX idx_alert_rules_org ON alert_rules(org_id);

-- ClickHouse
-- Primary key index is ORDER BY clause: (org_id, call_site, ts)
-- Additional: skip index on model for model-specific queries
```

---

## 5. Migration Strategy

- PostgreSQL: Alembic, additive-only in v1
- ClickHouse: schema managed via `clickhouse-migrations` CLI
- Zero-downtime: ClickHouse is append-only; no UPDATE/DELETE on event data

---

## 6. Privacy Notes

- `prompt_hash`: SHA-256 of prompt+response content â€” enables dedup without storing content
- `call_site`: hashed source file + line number (not function names or code content)
- ClickHouse TTL: auto-deletes events older than 90 days (configurable)

