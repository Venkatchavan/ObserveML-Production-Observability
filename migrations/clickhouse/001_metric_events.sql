-- OB-02: ClickHouse metric_events table with 90-day TTL
-- Applied by: clickhouse-migrations CLI or ensure_table() on startup

CREATE TABLE IF NOT EXISTS metric_events (
    event_id      String,         -- UUID idempotency key
    org_id        String,         -- UUID of owning organization
    call_site     String,         -- hashed source fingerprint
    model         String,         -- e.g. 'gpt-4o', 'claude-3-5'
    latency_ms    UInt32,
    input_tokens  UInt32,
    output_tokens UInt32,
    cost_usd      Float32,
    error         Bool,
    error_code    String,
    prompt_hash   String,         -- SHA-256 of prompt+response for dedup only
    ts            DateTime64(3)   -- millisecond precision UTC
) ENGINE = MergeTree()
PARTITION BY (org_id, toYYYYMMDD(ts))
ORDER BY (org_id, call_site, ts)
TTL toDateTime(ts) + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;
