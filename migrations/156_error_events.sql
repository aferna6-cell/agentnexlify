-- Migration 156: platform-level error event log
-- Provides a zero-dependency local fallback for error capture when
-- SENTRY_DSN is not configured. Records unhandled 500s into this table
-- via backend/services/error_events.py.
-- Idempotent: safe to re-apply.

CREATE TABLE IF NOT EXISTS error_events (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at  timestamptz NOT NULL    DEFAULT now(),
    level       text,
    source      text,
    message     text,
    path        text,
    status_code int,
    stack       text,
    context     jsonb
);

-- Fast time-range queries (monitoring, dashboards, cleanup jobs)
CREATE INDEX IF NOT EXISTS error_events_created_at_idx
    ON error_events (created_at DESC);
