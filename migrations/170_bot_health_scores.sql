-- Migration 170: bot_health_scores table
--
-- Per-tenant Bot-Health evals (opportunity #R4). Scores each tenant's
-- chat-widget bot quality on recent conversations using an LLM-as-judge
-- (Haiku, cheap + high-volume — see .claude/rules/model-routing.md #R7 cost
-- floor). One row per scoring run (POST /api/v1/bot-health/run, or an
-- automation-loop cron later), NOT upserted — the table is a time series so
-- the dashboard can show a trend line and detect degradation over time, not
-- just a single point-in-time snapshot.
--
-- bot_health_scores.tenant_id — a per-tenant AGGREGATE table, not the leads/
-- conversations table, so it uses tenant_id (NOT client_id). See
-- .claude/rules/schema-discipline.md. The source data it aggregates
-- (chat_messages) also uses tenant_id (migration 006), so this stays
-- consistent with its input.
--
-- No RLS — matches the two most recent per-tenant aggregate/approval tables
-- (167_appointment_reminders.sql, 168_review_responses.sql). The app uses a
-- Supabase service-role client exclusively for this table (see
-- backend/services/bot_health.py); RLS is not the guardrail here.

CREATE TABLE IF NOT EXISTS bot_health_scores (
    id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                 uuid NOT NULL,
    computed_at               timestamptz NOT NULL DEFAULT now(),
    window_days               int NOT NULL,
    sample_size               int NOT NULL,
    resolution_rate           numeric,
    hallucination_flag_count  int,
    unresolved_intent_count   int,
    avg_sentiment             numeric,
    health_score              numeric,
    details                   jsonb,
    created_at                timestamptz NOT NULL DEFAULT now()
);

-- Dashboard query: "give me tenant X's most recent health score(s), newest
-- first" — this is the only read pattern (GET /api/v1/bot-health/{tenant_id}).
CREATE INDEX IF NOT EXISTS idx_bot_health_scores_tenant_computed
    ON bot_health_scores (tenant_id, computed_at DESC);
