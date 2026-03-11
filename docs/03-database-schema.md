# Database Schema â€” ObserveML
**v1.0.3 | 2026-03-12 | Database Architect**

---

## 1. Entity Relationship Overview

```
organizations â”€â”€< api_keys
organizations â”€â”€< alert_rules
[ClickHouse] metric_events (time-series, partitioned by org + day)
[PostgreSQL] organizations, api_keys, alert_rules
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

