-- Migration 178: topics-lite per-department custom instructions
-- (enterprise-audit item 4).
--
-- One jsonb map on tenants keyed by engine department id
-- (e.g. {"sales": "Always mention the referral program."}). Mirrors the
-- os_auto_send_rules pattern. Injected into the Agent OS engine as
-- high-priority KbEntry rows — style/behavior guidance only; approval and
-- guardrail invariants are pinned in code and cannot be overridden here.

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS os_custom_instructions jsonb NOT NULL DEFAULT '{}'::jsonb;
