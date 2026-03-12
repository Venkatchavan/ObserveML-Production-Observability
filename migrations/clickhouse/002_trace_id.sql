-- OB-36: Add trace_id column for OpenTelemetry trace propagation
-- Safe to run multiple times (IF NOT EXISTS via ALTER ... ADD COLUMN IF NOT EXISTS)

ALTER TABLE metric_events
    ADD COLUMN IF NOT EXISTS trace_id String DEFAULT '';
