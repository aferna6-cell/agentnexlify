-- Migration 177: golden-question eval harness (enterprise-audit item 2).
--
-- Per-tenant regression checks for the widget bot's grounding: the owner (or
-- onboarding) records questions customers actually ask plus the phrases the
-- compiled knowledge must contain. Evals run deterministically (substring
-- checks against widget_configs.knowledge_base + faq_entries) after every KB
-- compile and on demand — no LLM judge, no token spend.
--
-- tenant_id (default scope column) — owner config, not customer-data family.

CREATE TABLE IF NOT EXISTS tenant_eval_questions (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         uuid NOT NULL,
    question          text NOT NULL,
    expected_phrases  text[] NOT NULL DEFAULT '{}',
    enabled           boolean NOT NULL DEFAULT true,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tenant_eval_questions_tenant_idx
    ON tenant_eval_questions (tenant_id, enabled);

CREATE TABLE IF NOT EXISTS tenant_eval_runs (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    uuid NOT NULL,
    trigger      text NOT NULL,            -- 'kb_compile' | 'manual' | 'nightly'
    total        integer NOT NULL DEFAULT 0,
    passed       integer NOT NULL DEFAULT 0,
    failed       integer NOT NULL DEFAULT 0,
    regressions  integer NOT NULL DEFAULT 0,
    results      jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tenant_eval_runs_tenant_idx
    ON tenant_eval_runs (tenant_id, created_at DESC);

-- Service-role access only (matches migration 175 pattern: RLS on, no
-- permissive policies — the backend's service client bypasses RLS).
ALTER TABLE tenant_eval_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_eval_runs ENABLE ROW LEVEL SECURITY;
