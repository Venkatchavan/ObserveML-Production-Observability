-- OB-45: Add session_id column to metric_events (idempotent)
-- Sprint 05 — v1.2.0
-- Applied automatically by ensure_table() on startup.

ALTER TABLE metric_events
    ADD COLUMN IF NOT EXISTS session_id String DEFAULT '';
